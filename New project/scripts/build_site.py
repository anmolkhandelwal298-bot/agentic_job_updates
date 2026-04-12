#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import html
import json
from pathlib import Path

from logo_utils import enrich_collection


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "templates" / "page.html"
CONTENT_PATH = ROOT / "data" / "content.json"
OUTPUT_PATH = ROOT / "dist" / "ai-layoffs-and-jobs.html"
INDEX_PATH = ROOT / "dist" / "index.html"
ASSETS_SOURCE = ROOT / "assets"
ASSETS_OUTPUT = ROOT / "dist" / "assets"


def render_stats(stats):
    return "".join(
        f'<div class="st"><div class="st-v">{html.escape(item["value"])}</div>'
        f'<div class="st-l">{html.escape(item["label"])}</div>'
        f'<div class="st-d {html.escape(item["detail_class"])}">{html.escape(item["detail"])}</div></div>'
        for item in stats
    )


def render_anthropic_items(items):
    return "".join(
        f'<div class="anth-item"><div class="av">{html.escape(item["value"])}</div>'
        f'<div class="al">{item["label"]}</div></div>'
        for item in items
    )


def render_anthropic_links(links):
    return "".join(
        f'<a href="{html.escape(item["href"], quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(item["label"])}</a>'
        for item in links
    )


def load_content(path: Path):
    content = json.loads(path.read_text(encoding="utf-8"))
    content["layoffs"] = enrich_collection(content["layoffs"])
    content["india"] = enrich_collection(content["india"])
    return content


def build_html(content: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "__PAGE_TITLE__": content["page_title"],
        "__META_DESCRIPTION__": content["meta_description"],
        "__TICKER_TEXT__": content["ticker_text"],
        "__HERO_BADGE__": content["hero"]["badge"],
        "__HERO_TITLE__": content["hero"]["title"],
        "__HERO_DESCRIPTION__": content["hero"]["description"],
        "__STATS_HTML__": render_stats(content["stats"]),
        "__ANTHROPIC_TITLE__": content["anthropic"]["title"],
        "__ANTHROPIC_INTRO__": content["anthropic"]["intro"],
        "__ANTHROPIC_ITEMS_HTML__": render_anthropic_items(content["anthropic"]["items"]),
        "__ANTHROPIC_NOTE__": content["anthropic"]["note"],
        "__ANTHROPIC_LINKS_HTML__": render_anthropic_links(content["anthropic"]["links"]),
        "__LAYOFF_COUNT__": str(len(content["layoffs"])),
        "__INDIA_COUNT__": str(len(content["india"])),
        "__DIVIDER_TITLE__": content["divider"]["title"],
        "__DIVIDER_DESCRIPTION__": content["divider"]["description"],
        "__ADVANTAGE_LABEL__": content["divider"]["advantage_label"],
        "__ADVANTAGE_COPY__": content["divider"]["advantage_copy"],
        "__WARNING_LABEL__": content["divider"]["warning_label"],
        "__WARNING_COPY__": content["divider"]["warning_copy"],
        "__CTA_LABEL__": content["cta"]["label"],
        "__CTA_TITLE__": content["cta"]["title"],
        "__CTA_DESCRIPTION__": content["cta"]["description"],
        "__CTA_LINK__": content["cta"]["link"],
        "__CTA_BUTTON__": content["cta"]["button"],
        "__FOOTER_TEXT__": content["footer_text"],
        "__LAYOFFS_JSON__": json.dumps(content["layoffs"], ensure_ascii=False),
        "__INDIA_JSON__": json.dumps(content["india"], ensure_ascii=False),
        "__LAYOFF_FILTERS_JSON__": json.dumps(content["layoff_filters"], ensure_ascii=False),
    }

    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static AI layoffs and jobs page from structured content.")
    parser.add_argument("--content", default=str(CONTENT_PATH), help="JSON content file.")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="HTML output file.")
    args = parser.parse_args()

    content_path = Path(args.content).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    content = load_content(content_path)
    html_output = build_html(content)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_output, encoding="utf-8")
    INDEX_PATH.write_text(html_output, encoding="utf-8")

    if ASSETS_OUTPUT.exists():
        shutil.rmtree(ASSETS_OUTPUT)
    if ASSETS_SOURCE.exists():
        shutil.copytree(ASSETS_SOURCE, ASSETS_OUTPUT)


if __name__ == "__main__":
    main()
