const { get } = require('@vercel/blob');
const { buildHtml, loadLocalContent } = require('../lib/site');
const { CONTENT_BLOB_PATH } = require('../lib/updater');

module.exports = async function handler(_request, response) {
  try {
    let content;

    // Always use local content.json (current deploy) as primary source.
    // Blob is only used if local load fails.
    try {
      content = await loadLocalContent();
    } catch {
      const result = await get(CONTENT_BLOB_PATH, { access: 'private' });
      const raw = await new Response(result.stream).text();
      content = JSON.parse(raw);
    }

    const html = await buildHtml(content, { assetBase: '/assets' });
    response.setHeader('Content-Type', 'text/html; charset=utf-8');
    response.setHeader('Cache-Control', 'public, s-maxage=900, stale-while-revalidate=3600');
    response.status(200).send(html);
  } catch (error) {
    response.status(500).json({ ok: false, error: error.message });
  }
};
