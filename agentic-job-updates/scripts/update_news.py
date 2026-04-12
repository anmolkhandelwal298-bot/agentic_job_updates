#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import textwrap
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import build_site
from logo_utils import enrich_collection


ROOT = Path(__file__).resolve().parents[1]
CONTENT_PATH = ROOT / "data" / "content.json"

DEFAULT_MODEL = "gpt-5.2"
GOOGLE_NEWS = "https://news.google.com/rss/search"

LAYOFF_QUERIES = [
    "AI layoffs tech jobs workforce automation",
    "generative AI layoffs software company jobs",
    "AI replacing workers layoffs enterprise software",
]

INDIA_QUERIES = [
    "India AI jobs hiring engineers demand",
    "India generative AI hiring software engineers",
    "India AI opportunity jobs GCC hiring",
]


def fetch_rss(query: str, limit: int = 8):
    params = urllib.parse.urlencode({"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
    url = f"{GOOGLE_NEWS}?{params}"
    with urllib.request.urlopen(url, timeout=20) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    items = []
    for item in root.findall(".//item")[:limit]:
        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        description = item.findtext("description", default="").strip()
        source = item.findtext("source", default="Google News").strip()
        pub_date = item.findtext("pubDate", default="").strip()
        items.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "source": source,
                "published_at": pub_date,
            }
        )
    return items


def gather_candidates():
    groups = {"layoffs": [], "india": []}
    for query in LAYOFF_QUERIES:
        groups["layoffs"].extend(fetch_rss(query))
    for query in INDIA_QUERIES:
        groups["india"].extend(fetch_rss(query))

    for key, items in groups.items():
        deduped = []
        seen = set()
        for item in items:
            fingerprint = (item["title"].lower(), item["link"])
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            deduped.append(item)
        groups[key] = deduped[:15]
    return groups


def call_openai(api_key: str, model: str, content: dict, candidates: dict) -> dict:
    schema = {
        "name": "daily_ai_jobs_update",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "ticker_text": {"type": "string"},
                "hero_badge": {"type": "string"},
                "footer_text": {"type": "string"},
                "layoffs": {
                    "type": "array",
                    "maxItems": 8,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "c": {"type": "string"},
                            "ind": {"type": "string"},
                            "imp": {"type": "string"},
                            "d": {"type": "string"},
                            "y": {"type": "string"},
                            "big": {"type": "integer"},
                            "col": {"type": "string"},
                            "txt": {"type": "string"},
                            "q": {"type": "string"},
                            "lk": {"type": "string"},
                            "s": {"type": "string"},
                            "logo": {"type": "string"},
                        },
                        "required": ["c", "ind", "imp", "d", "y", "big", "col", "txt", "q", "lk", "s", "logo"],
                    },
                },
                "india": {
                    "type": "array",
                    "maxItems": 8,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "c": {"type": "string"},
                            "role": {"type": "string"},
                            "txt": {"type": "string"},
                            "lk": {"type": "string"},
                            "s": {"type": "string"},
                            "col": {"type": "string"},
                            "logo": {"type": "string"},
                        },
                        "required": ["c", "role", "txt", "lk", "s", "col", "logo"],
                    },
                },
            },
            "required": ["ticker_text", "hero_badge", "footer_text", "layoffs", "india"],
        },
    }

    instructions = textwrap.dedent(
        """
        You update a static news page for Indian software engineers about AI-driven layoffs and India hiring.
        Use ONLY the provided candidate articles. Never hallucinate data.

        FIELD RULES — follow exactly:

        layoffs array items:
        - c: SHORT company name only (e.g. "Oracle", "Amazon", "Meta"). NEVER a trend, topic, or industry name. If the article is not about a specific named company, skip it.
        - ind: short industry label, 1-3 words (e.g. "Technology", "Fintech", "E-commerce")
        - imp: ONLY the layoff count or range (e.g. "10,000–30,000", "~4,000", "Major cuts"). Max 20 characters. Never a sentence.
        - d: date as "Mon YYYY" (e.g. "Apr 2026")
        - y: year string "2026" or "2025"
        - big: integer 1 if impact is 10,000+ workers, else 0
        - col: a valid CSS hex color string (e.g. "#ff3b30", "#007DB8"). Never a color name like "RED".
        - txt: 1-2 sentence summary. May use <em>…</em> for emphasis only. No other HTML.
        - q: a SHORT direct quote or key fact (max 120 chars). Plain text only, no HTML.
        - lk: full https:// article URL
        - s: short source name (e.g. "CNBC", "Bloomberg")
        - logo: leave as empty string "" — it will be filled automatically

        india array items:
        - c: short label (e.g. "Infosys Hiring", "GCC Expansion")
        - role: short sub-label (e.g. "TechGig Report")
        - txt: 1-2 sentence summary. May use <em>…</em> only.
        - lk: full https:// article URL
        - s: short source name
        - col: a valid CSS hex color string (e.g. "#2dd4a0", "#5b9cf6")
        - logo: leave as empty string "" — it will be filled automatically

        Other rules:
        - Return only items with a specific named company (layoffs) or clear data point (india)
        - Skip vague trend articles with no named company or no specific numbers
        - Prefer reputable outlets (CNBC, Bloomberg, Reuters, TechCrunch, NYT, Al Jazeera)
        - Return only fresh items not already in existing_layoff_links / existing_india_links
        - ticker_text: all-caps ticker style, facts separated by ·
        - hero_badge: e.g. "EVIDENCE TRACKER — APRIL 2026"
        - footer_text: mention sources and current month/year
        """
    ).strip()

    user_input = {
        "current_page": {
            "hero_badge": content["hero"]["badge"],
            "footer_text": content["footer_text"],
            "existing_layoff_links": [item["lk"] for item in content["layoffs"][:12]],
            "existing_india_links": [item["lk"] for item in content["india"][:12]],
        },
        "candidates": candidates,
        "today": datetime.now().strftime("%Y-%m-%d"),
    }

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model=model,
        reasoning={"effort": "medium"},
        instructions=instructions,
        input=[{
            "role": "user",
            "content": json.dumps(user_input, ensure_ascii=False),
        }],
        text={
            "format": {
                "type": "json_schema",
                "name": schema["name"],
                "schema": schema["schema"],
                "strict": True,
            }
        },
    )

    return json.loads(response.output_text)


import re as _re

_HEX_RE = _re.compile(r'^#[0-9a-fA-F]{3,6}$')
_DEFAULT_LAYOFF_COLORS = ["#ff3b30", "#ff6b35", "#e84393", "#8b5cf6", "#333333"]
_DEFAULT_INDIA_COLORS = ["#2dd4a0", "#34d399", "#5b9cf6", "#fbbf24"]

def _sanitize_layoff(item: dict, idx: int) -> dict | None:
    """Return a cleaned item or None to discard it."""
    c = str(item.get("c", "")).strip()
    lk = str(item.get("lk", "")).strip()
    imp = str(item.get("imp", "")).strip()

    # Must be a named company (not a trend/industry topic)
    if not c or len(c) > 40 or not lk.startswith("http"):
        return None
    # imp should be short — if it's a full sentence, discard
    if len(imp) > 30:
        item["imp"] = imp[:30]

    # Fix col if not a valid hex color
    col = str(item.get("col", "")).strip()
    if not _HEX_RE.match(col):
        item["col"] = _DEFAULT_LAYOFF_COLORS[idx % len(_DEFAULT_LAYOFF_COLORS)]

    # Clear logo — logo_utils will fill it properly from the article link
    item["logo"] = ""

    # Truncate q if too long
    q = str(item.get("q", "")).strip()
    if len(q) > 150:
        item["q"] = q[:147] + "…"

    return item


def _sanitize_india(item: dict, idx: int) -> dict | None:
    c = str(item.get("c", "")).strip()
    lk = str(item.get("lk", "")).strip()
    if not c or not lk.startswith("http"):
        return None
    col = str(item.get("col", "")).strip()
    if not _HEX_RE.match(col):
        item["col"] = _DEFAULT_INDIA_COLORS[idx % len(_DEFAULT_INDIA_COLORS)]
    item["logo"] = ""
    return item


def sanitize_update(update: dict) -> dict:
    update["layoffs"] = [
        s for i, item in enumerate(update.get("layoffs", []))
        if (s := _sanitize_layoff(item, i)) is not None
    ]
    update["india"] = [
        s for i, item in enumerate(update.get("india", []))
        if (s := _sanitize_india(item, i)) is not None
    ]
    return update


def merge_items(existing: list[dict], incoming: list[dict], key: str, limit: int):
    merged = incoming + existing
    deduped = []
    seen = set()
    for item in merged:
        identifier = item.get(key, "").strip().lower()
        if not identifier or identifier in seen:
            continue
        seen.add(identifier)
        deduped.append(item)
    return deduped[:limit]


def sort_by_date(items: list[dict], field: str):
    def parse(item):
        try:
            return parsedate_to_datetime(item[field])
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    return sorted(items, key=parse, reverse=True)


def apply_update(content: dict, update: dict) -> dict:
    content["ticker_text"] = update["ticker_text"]
    content["hero"]["badge"] = update["hero_badge"]
    content["footer_text"] = update["footer_text"]
    content["layoffs"] = enrich_collection(merge_items(content["layoffs"], update["layoffs"], "lk", 30))
    content["india"] = enrich_collection(merge_items(content["india"], update["india"], "lk", 20))
    return content


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch fresh AI job-impact news and update the content JSON.")
    parser.add_argument("--content", default=str(CONTENT_PATH), help="Structured content JSON to update.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model to use.")
    parser.add_argument("--dry-run", action="store_true", help="Print the model update payload without writing changes.")
    parser.add_argument("--skip-build", action="store_true", help="Only update the JSON file and skip regenerating the HTML.")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required to run the daily updater.")

    content_path = Path(args.content).expanduser().resolve()
    content = json.loads(content_path.read_text(encoding="utf-8"))
    content["layoffs"] = enrich_collection(content["layoffs"])
    content["india"] = enrich_collection(content["india"])
    candidates = gather_candidates()

    # Favor the most recent candidates before sending them to the model.
    candidates["layoffs"] = sort_by_date(candidates["layoffs"], "published_at")
    candidates["india"] = sort_by_date(candidates["india"], "published_at")

    update = sanitize_update(call_openai(api_key=api_key, model=args.model, content=content, candidates=candidates))
    if args.dry_run:
        print(json.dumps(update, indent=2, ensure_ascii=False))
        return

    updated_content = apply_update(content, update)
    content_path.write_text(json.dumps(updated_content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not args.skip_build:
        html_output = build_site.build_html(updated_content)
        dist = ROOT / "dist"
        dist.mkdir(parents=True, exist_ok=True)
        (dist / "ai-layoffs-and-jobs.html").write_text(html_output, encoding="utf-8")
        (dist / "index.html").write_text(html_output, encoding="utf-8")


if __name__ == "__main__":
    main()
