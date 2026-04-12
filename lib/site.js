const fs = require('node:fs/promises');
const path = require('node:path');

const ROOT = process.cwd();
const TEMPLATE_PATH = path.join(ROOT, 'templates', 'page.html');
const CONTENT_PATH = path.join(ROOT, 'data', 'content.json');

const COMPANY_DOMAINS = {
  'Oracle': 'oracle.com',
  'Block (Square)': 'block.xyz',
  'Atlassian': 'atlassian.com',
  'Ocado': 'ocado.com',
  'Dell': 'dell.com',
  'Meta (Reality Labs)': 'meta.com',
  'Baker McKenzie': 'bakermckenzie.com',
  'Amazon': 'amazon.com',
  'Autodesk': 'autodesk.com',
  'UPS': 'ups.com',
  'Dow': 'dow.com',
  'ASML': 'asml.com',
  'Accenture': 'accenture.com',
  'Omnicom': 'omnicomgroup.com',
  'McKinsey': 'mckinsey.com',
  'C.H. Robinson': 'chrobinson.com',
  'Fiverr': 'fiverr.com',
  'Salesforce': 'salesforce.com',
  'IBM': 'ibm.com',
  'BlackRock': 'blackrock.com',
  'Klarna': 'klarna.com',
  'Duolingo': 'duolingo.com',
  'AI Hiring Surge': 'foundit.in',
  'Tech Hiring +12-15%': 'adecco.co.in',
  'ML Engineer Demand': 'adecco.co.in',
  'Hiring Intent +11%': 'taggd.in',
  'Bengaluru Leads': 'foundit.in',
  'Semiconductor Boom': 'taggd.in',
  'GCC Expansion': 'zyoin.com',
  'BFSI AI Surge': 'foundit.in',
  'Global Offshoring to India': 'ibtimes.co.in',
  '170M Global Tech Jobs': 'weforum.org',
  'Pay Premium': 'adecco.co.in',
  'IndiaAI Mission': 'indiaai.gov.in'
};

const FAVICON_URL = 'https://www.google.com/s2/favicons';

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function logoUrlForDomain(domain) {
  return `${FAVICON_URL}?domain=${encodeURIComponent(domain)}&sz=128`;
}

function sourceDomainFromLink(link) {
  try {
    return new URL(link).hostname.replace(/^www\./, '');
  } catch {
    return null;
  }
}

function attachLogo(item) {
  const enriched = { ...item };
  const domain = COMPANY_DOMAINS[enriched.c] || sourceDomainFromLink(enriched.lk || '');
  if (domain && !enriched.logo) {
    enriched.logo = logoUrlForDomain(domain);
  }
  return enriched;
}

function enrichContent(content) {
  return {
    ...content,
    layoffs: content.layoffs.map(attachLogo),
    india: content.india.map(attachLogo)
  };
}

async function loadLocalContent() {
  const raw = await fs.readFile(CONTENT_PATH, 'utf8');
  return enrichContent(JSON.parse(raw));
}

async function loadTemplate() {
  return fs.readFile(TEMPLATE_PATH, 'utf8');
}

function renderStats(stats) {
  return stats.map((item) =>
    `<div class="st"><div class="st-v">${escapeHtml(item.value)}</div><div class="st-l">${escapeHtml(item.label)}</div><div class="st-d ${escapeHtml(item.detail_class)}">${escapeHtml(item.detail)}</div></div>`
  ).join('');
}

function renderAnthropicItems(items) {
  return items.map((item) =>
    `<div class="anth-item"><div class="av">${escapeHtml(item.value)}</div><div class="al">${item.label}</div></div>`
  ).join('');
}

function renderAnthropicLinks(links) {
  return links.map((item) =>
    `<a href="${escapeHtml(item.href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.label)}</a>`
  ).join('');
}

async function buildHtml(content, options = {}) {
  const assetBase = options.assetBase || './assets';
  let template = await loadTemplate();
  const replacements = {
    '__PAGE_TITLE__': content.page_title,
    '__META_DESCRIPTION__': content.meta_description,
    '__TICKER_TEXT__': content.ticker_text,
    '__HERO_BADGE__': content.hero.badge,
    '__HERO_TITLE__': content.hero.title,
    '__HERO_DESCRIPTION__': content.hero.description,
    '__STATS_HTML__': renderStats(content.stats),
    '__ANTHROPIC_TITLE__': content.anthropic.title,
    '__ANTHROPIC_INTRO__': content.anthropic.intro,
    '__ANTHROPIC_ITEMS_HTML__': renderAnthropicItems(content.anthropic.items),
    '__ANTHROPIC_NOTE__': content.anthropic.note,
    '__ANTHROPIC_LINKS_HTML__': renderAnthropicLinks(content.anthropic.links),
    '__LAYOFF_COUNT__': String(content.layoffs.length),
    '__INDIA_COUNT__': String(content.india.length),
    '__DIVIDER_TITLE__': content.divider.title,
    '__DIVIDER_DESCRIPTION__': content.divider.description,
    '__ADVANTAGE_LABEL__': content.divider.advantage_label,
    '__ADVANTAGE_COPY__': content.divider.advantage_copy,
    '__WARNING_LABEL__': content.divider.warning_label,
    '__WARNING_COPY__': content.divider.warning_copy,
    '__CTA_LABEL__': content.cta.label,
    '__CTA_TITLE__': content.cta.title,
    '__CTA_DESCRIPTION__': content.cta.description,
    '__CTA_LINK__': content.cta.link,
    '__CTA_BUTTON__': content.cta.button,
    '__FOOTER_TEXT__': content.footer_text,
    '__LAYOFFS_JSON__': JSON.stringify(content.layoffs),
    '__INDIA_JSON__': JSON.stringify(content.india),
    '__LAYOFF_FILTERS_JSON__': JSON.stringify(content.layoff_filters)
  };

  template = template
    .replaceAll('../assets/newtonschool-logo.png', `${assetBase}/newtonschool-logo.png`);

  for (const [token, value] of Object.entries(replacements)) {
    template = template.replaceAll(token, value);
  }
  return template;
}

module.exports = {
  buildHtml,
  enrichContent,
  loadLocalContent
};
