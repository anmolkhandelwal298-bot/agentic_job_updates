# AI Layoffs And Jobs Updater

This project turns the original one-file HTML page into a small static-content pipeline so the page can be refreshed daily without hand-editing the markup.

## What changed

- `data/content.json` is the source of truth for the page content.
- `templates/page.html` preserves the existing visual design and card format.
- `scripts/build_site.py` rebuilds the final HTML into `dist/ai-layoffs-and-jobs.html`.
- `scripts/update_news.py` acts as the daily update agent:
  - fetches fresh news candidates from Google News RSS
  - asks OpenAI to classify and format the best items
  - merges new items into the existing data file

## One-time import

Import the current legacy HTML into structured JSON:

```bash
python3 scripts/import_legacy_html.py \
  --input /Users/anmolkhandelwal/Downloads/ai-layoffs-and-jobs.html \
  --output data/content.json
```

## Build the site

```bash
python3 scripts/build_site.py
```

The output file will be:

- `/Users/anmolkhandelwal/Documents/New project/dist/ai-layoffs-and-jobs.html`
- `/Users/anmolkhandelwal/Documents/New project/dist/index.html`

## Run the daily updater

The updater needs internet access and an OpenAI API key:

```bash
export OPENAI_API_KEY=your_key_here
python3 scripts/update_news.py --dry-run
python3 scripts/update_news.py
python3 scripts/build_site.py
```

## Suggested daily workflow

1. Run `scripts/update_news.py` in the morning.
2. Rebuild with `scripts/build_site.py`.
3. Review the generated HTML in `dist/`.

## Notes

- The updater keeps the same front-end format by updating structured content instead of editing HTML directly.
- It currently focuses on the two news grids and light metadata refreshes like the ticker, hero badge, and footer month.
- If you want, the next step can be adding a fully scheduled daily automation so this runs without manual intervention.

## Deploy on Vercel

This repo now supports a Vercel-native daily updater:

- `/api/site` serves the latest generated page
- `/api/cron-update` runs the daily refresh
- `vercel.json` rewrites `/` to `/api/site`
- `vercel.json` schedules the cron for `30 3 * * *` which is `9:00 AM IST`

### Required setup in Vercel

1. Push this project to GitHub.
2. Import the repo into Vercel.
3. Add a Blob store to the project.
4. Add these environment variables:
   - `OPENAI_API_KEY`
   - `CRON_SECRET`
   - `OPENAI_MODEL` optional, defaults to `gpt-5-mini`
5. Deploy.

Vercel Blob will provide `BLOB_READ_WRITE_TOKEN` to the project when linked.

### What happens after deploy

- Visitors hit `/` and Vercel rewrites that to `/api/site`
- `/api/site` reads the latest stored content from Vercel Blob and renders the page
- Every day at `9:00 AM IST`, Vercel Cron calls `/api/cron-update`
- `/api/cron-update` fetches fresh stories, asks OpenAI to format them, and stores the updated JSON in Blob

### CLI deploy

```bash
vercel
```

For production:

```bash
vercel --prod
```
