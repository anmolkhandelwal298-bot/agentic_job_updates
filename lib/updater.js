const { enrichContent } = require('./site');

const GOOGLE_NEWS = 'https://news.google.com/rss/search';
const CONTENT_BLOB_PATH = 'content/latest.json';

const LAYOFF_QUERIES = [
  'AI layoffs tech jobs workforce automation',
  'generative AI layoffs software company jobs',
  'AI replacing workers layoffs enterprise software'
];

const INDIA_QUERIES = [
  'India AI jobs hiring engineers demand',
  'India generative AI hiring software engineers',
  'India AI opportunity jobs GCC hiring'
];

function rssUrl(query) {
  const params = new URLSearchParams({
    q: query,
    hl: 'en-IN',
    gl: 'IN',
    ceid: 'IN:en'
  });
  return `${GOOGLE_NEWS}?${params.toString()}`;
}

function parseXmlItems(xml) {
  const itemMatches = [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)];
  return itemMatches.map((match) => {
    const block = match[1];
    return {
      title: decodeXml(block.match(/<title>([\s\S]*?)<\/title>/)?.[1] || ''),
      link: decodeXml(block.match(/<link>([\s\S]*?)<\/link>/)?.[1] || ''),
      description: decodeXml(block.match(/<description>([\s\S]*?)<\/description>/)?.[1] || ''),
      source: decodeXml(block.match(/<source[^>]*>([\s\S]*?)<\/source>/)?.[1] || 'Google News'),
      published_at: decodeXml(block.match(/<pubDate>([\s\S]*?)<\/pubDate>/)?.[1] || '')
    };
  });
}

function decodeXml(value) {
  return value
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

async function fetchRss(query, limit = 8) {
  const response = await fetch(rssUrl(query), { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Failed to fetch RSS for "${query}": ${response.status}`);
  }
  const xml = await response.text();
  return parseXmlItems(xml).slice(0, limit);
}

async function gatherCandidates() {
  const groups = { layoffs: [], india: [] };

  for (const query of LAYOFF_QUERIES) {
    groups.layoffs.push(...await fetchRss(query));
  }
  for (const query of INDIA_QUERIES) {
    groups.india.push(...await fetchRss(query));
  }

  for (const key of Object.keys(groups)) {
    const seen = new Set();
    groups[key] = groups[key]
      .filter((item) => {
        const fingerprint = `${item.title.toLowerCase()}::${item.link}`;
        if (seen.has(fingerprint)) {
          return false;
        }
        seen.add(fingerprint);
        return true;
      })
      .sort((a, b) => Date.parse(b.published_at || 0) - Date.parse(a.published_at || 0))
      .slice(0, 15);
  }

  return groups;
}

function extractResponseText(payload) {
  if (payload.output_text) {
    return payload.output_text;
  }

  const texts = [];
  for (const item of payload.output || []) {
    for (const content of item.content || []) {
      if ((content.type === 'output_text' || content.type === 'text') && content.text) {
        texts.push(content.text);
      }
    }
  }
  return texts.join('\n').trim();
}

async function callOpenAI(content, candidates) {
  if (!process.env.OPENAI_API_KEY) {
    throw new Error('OPENAI_API_KEY is required');
  }

  const schema = {
    type: 'object',
    additionalProperties: false,
    properties: {
      ticker_text: { type: 'string' },
      hero_badge: { type: 'string' },
      footer_text: { type: 'string' },
      layoffs: {
        type: 'array',
        maxItems: 8,
        items: {
          type: 'object',
          additionalProperties: false,
          properties: {
            c: { type: 'string' },
            ind: { type: 'string' },
            imp: { type: 'string' },
            d: { type: 'string' },
            y: { type: 'string' },
            big: { type: 'integer' },
            col: { type: 'string' },
            txt: { type: 'string' },
            q: { type: 'string' },
            lk: { type: 'string' },
            s: { type: 'string' }
          },
          required: ['c', 'ind', 'imp', 'd', 'y', 'big', 'col', 'txt', 'q', 'lk', 's']
        }
      },
      india: {
        type: 'array',
        maxItems: 8,
        items: {
          type: 'object',
          additionalProperties: false,
          properties: {
            c: { type: 'string' },
            role: { type: 'string' },
            txt: { type: 'string' },
            lk: { type: 'string' },
            s: { type: 'string' },
            col: { type: 'string' }
          },
          required: ['c', 'role', 'txt', 'lk', 's', 'col']
        }
      }
    },
    required: ['ticker_text', 'hero_badge', 'footer_text', 'layoffs', 'india']
  };

  const instructions = [
    'You update a static news page for Indian software engineers.',
    'Keep the tone sharp, evidence-backed, and concise.',
    'Use only the provided candidate articles.',
    'Preserve the existing schema and formatting conventions.',
    'layoffs items should be company-focused with short impact summaries and short quotes.',
    'india items should be opportunity or data-point focused, optimistic but factual.',
    'Use dates like "Apr 2026".',
    'Set big to 1 only when impact is 10,000+ or a very large workforce cut, otherwise 0.',
    'Only use <em> tags in txt when useful.',
    'Prefer reputable outlets and avoid duplicates.',
    'Return only fresh items not already present by link unless a better replacement is clearly warranted.',
    'Keep ticker_text in uppercase ticker style.',
    'hero_badge should look like "EVIDENCE TRACKER — APRIL 2026".',
    'footer_text should mention sources and current month/year.'
  ].join(' ');

  const response = await fetch('https://api.openai.com/v1/responses', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: process.env.OPENAI_MODEL || 'gpt-5-mini',
      instructions,
      input: JSON.stringify({
        current_page: {
          hero_badge: content.hero.badge,
          footer_text: content.footer_text,
          existing_layoff_links: content.layoffs.slice(0, 12).map((item) => item.lk),
          existing_india_links: content.india.slice(0, 12).map((item) => item.lk)
        },
        candidates,
        today: new Date().toISOString().slice(0, 10)
      }),
      text: {
        format: {
          type: 'json_schema',
          name: 'daily_ai_jobs_update',
          schema,
          strict: true
        }
      }
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`OpenAI request failed: ${response.status} ${errorText}`);
  }

  const payload = await response.json();
  return JSON.parse(extractResponseText(payload));
}

function mergeItems(existing, incoming, key, limit) {
  const merged = [...incoming, ...existing];
  const seen = new Set();
  return merged.filter((item) => {
    const identifier = String(item[key] || '').trim().toLowerCase();
    if (!identifier || seen.has(identifier)) {
      return false;
    }
    seen.add(identifier);
    return true;
  }).slice(0, limit);
}

function applyUpdate(content, update) {
  const next = {
    ...content,
    ticker_text: update.ticker_text,
    hero: { ...content.hero, badge: update.hero_badge },
    footer_text: update.footer_text,
    layoffs: mergeItems(content.layoffs, update.layoffs, 'lk', 30),
    india: mergeItems(content.india, update.india, 'lk', 20)
  };
  return enrichContent(next);
}

async function refreshContent(content) {
  const candidates = await gatherCandidates();
  const update = await callOpenAI(content, candidates);
  return applyUpdate(content, update);
}

module.exports = {
  CONTENT_BLOB_PATH,
  refreshContent
};
