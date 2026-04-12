const { put } = require('@vercel/blob');
const { loadLocalContent } = require('../lib/site');
const { CONTENT_BLOB_PATH, refreshContent } = require('../lib/updater');

module.exports = async function handler(request, response) {
  const authHeader = request.headers.authorization;
  if (!process.env.CRON_SECRET || authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return response.status(401).json({ ok: false, error: 'Unauthorized' });
  }

  try {
    const baseContent = await loadLocalContent();
    const refreshedContent = await refreshContent(baseContent);

    await put(CONTENT_BLOB_PATH, JSON.stringify(refreshedContent), {
      access: 'private',
      allowOverwrite: true,
      contentType: 'application/json'
    });

    return response.status(200).json({
      ok: true,
      updatedAt: new Date().toISOString(),
      layoffCount: refreshedContent.layoffs.length,
      indiaCount: refreshedContent.india.length
    });
  } catch (error) {
    return response.status(500).json({ ok: false, error: error.message });
  }
};
