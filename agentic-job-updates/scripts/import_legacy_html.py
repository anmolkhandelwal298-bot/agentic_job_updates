#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


def extract(pattern: str, text: str, label: str, flags: int = 0) -> str:
    match = re.search(pattern, text, flags)
    if not match:
        raise ValueError(f"Could not find {label}")
    return match.group(1).strip()


def parse_js_array(name: str, html: str):
    raw = extract(rf"const {name}=(\[[\s\S]*?\]);", html, name)
    raw = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', raw)
    raw = raw.replace("true", "True").replace("false", "False")
    return ast.literal_eval(raw)


def parse_stats(html: str):
    stats_block = extract(r'<div class="stats">([\s\S]*?)</div>\s*<div class="wrap">', html, "stats", re.S)
    cards = re.findall(
        r'<div class="st"><div class="st-v">(.*?)</div><div class="st-l">(.*?)</div><div class="st-d ([^"]+)">(.*?)</div></div>',
        stats_block,
        re.S,
    )
    return [{"value": value, "label": label, "detail_class": detail_class, "detail": detail} for value, label, detail_class, detail in cards]


def parse_anthropic(html: str):
    title = extract(r'<div class="anth">\s*<h3>(.*?)</h3>', html, "anthropic title", re.S)
    intro = extract(r'<div class="anth">\s*<h3>.*?</h3>\s*<p style="[^"]*">(.*?)</p>', html, "anthropic intro", re.S)
    items = re.findall(r'<div class="anth-item"><div class="av">(.*?)</div><div class="al">(.*?)</div></div>', html, re.S)
    note = extract(r'<p style="font:italic 11px/1.5 var\(--body\);color:var\(--td\);margin-top:8px">(.*?)</p>', html, "anthropic note", re.S)
    links = re.findall(r'<a href="(.*?)" target="_blank">(.*?)</a>', extract(r'<div class="anth-links">([\s\S]*?)</div>', html, "anthropic links", re.S), re.S)
    return {
        "title": title,
        "intro": intro,
        "items": [{"value": value, "label": label} for value, label in items],
        "note": note,
        "links": [{"href": href, "label": label} for href, label in links],
    }


def parse_divider(html: str):
    divider = extract(r'<div class="dv">([\s\S]*?)</div>\s*</div>\s*<section class="cta">', html, "divider", re.S)
    title = extract(r'<h3>(.*?)</h3>', divider, "divider title", re.S)
    description = extract(r'<p>(.*?)</p>', divider, "divider description", re.S)
    boxes = re.findall(r'<div class="bx bx-([gr])"><div class="bl">(.*?)</div><div class="bc">(.*?)</div></div>', divider, re.S)
    return {
        "title": title,
        "description": description,
        "advantage_label": boxes[0][1],
        "advantage_copy": boxes[0][2],
        "warning_label": boxes[1][1],
        "warning_copy": boxes[1][2],
    }


def parse_cta(html: str):
    cta = extract(r'<section class="cta">([\s\S]*?)</section>', html, "cta", re.S)
    return {
        "label": extract(r'<div class="cta-lb">(.*?)</div>', cta, "cta label", re.S),
        "title": extract(r'<h2>(.*?)</h2>', cta, "cta title", re.S),
        "description": extract(r'<p>(.*?)</p>', cta, "cta description", re.S),
        "link": extract(r'<a href="(.*?)" class="cta-btn">', cta, "cta link", re.S),
        "button": extract(r'<a href=".*?" class="cta-btn">(.*?)</a>', cta, "cta button", re.S),
    }


def build_content(html: str):
    ticker_text = extract(r'<div class="tk"><div class="tk-in">\s*([\s\S]*?)\s*</div></div>', html, "ticker", re.S)
    return {
        "page_title": extract(r"<title>(.*?)</title>", html, "page title"),
        "meta_description": extract(r'<meta name="description" content="(.*?)">', html, "meta description"),
        "ticker_text": re.sub(r"\s+", " ", ticker_text).strip(),
        "hero": {
            "badge": extract(r'<div class="hero-badge"><span class="dot"></span>(.*?)</div>', html, "hero badge", re.S),
            "title": extract(r"<section class=\"hero\">[\s\S]*?<h1>(.*?)</h1>", html, "hero title", re.S),
            "description": extract(r"<section class=\"hero\">[\s\S]*?<p>(.*?)</p>", html, "hero description", re.S),
        },
        "stats": parse_stats(html),
        "anthropic": parse_anthropic(html),
        "layoff_filters": [
            {"value": "all", "label": "All"},
            {"value": "2026", "label": "2026"},
            {"value": "2025", "label": "2025"},
            {"value": "10k+", "label": "10,000+"},
        ],
        "divider": parse_divider(html),
        "cta": parse_cta(html),
        "footer_text": extract(r"<footer>(.*?)</footer>", html, "footer", re.S),
        "layoffs": parse_js_array("layoffs", html),
        "india": parse_js_array("india", html),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the legacy HTML into structured JSON content.")
    parser.add_argument("--input", required=True, help="Path to the current HTML file.")
    parser.add_argument("--output", default="data/content.json", help="Path to write the structured JSON content.")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    content = build_content(input_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
