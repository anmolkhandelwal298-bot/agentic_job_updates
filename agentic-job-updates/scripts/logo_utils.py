from __future__ import annotations

import urllib.parse
from urllib.parse import urlparse


COMPANY_DOMAINS = {
    "Oracle": "oracle.com",
    "Block (Square)": "block.xyz",
    "Atlassian": "atlassian.com",
    "Ocado": "ocado.com",
    "Dell": "dell.com",
    "Meta (Reality Labs)": "meta.com",
    "Baker McKenzie": "bakermckenzie.com",
    "Amazon": "amazon.com",
    "Autodesk": "autodesk.com",
    "UPS": "ups.com",
    "Dow": "dow.com",
    "ASML": "asml.com",
    "Accenture": "accenture.com",
    "Omnicom": "omnicomgroup.com",
    "McKinsey": "mckinsey.com",
    "C.H. Robinson": "chrobinson.com",
    "Fiverr": "fiverr.com",
    "Salesforce": "salesforce.com",
    "IBM": "ibm.com",
    "BlackRock": "blackrock.com",
    "Klarna": "klarna.com",
    "Duolingo": "duolingo.com",
    "AI Hiring Surge": "foundit.in",
    "Tech Hiring +12-15%": "adecco.co.in",
    "ML Engineer Demand": "adecco.co.in",
    "Hiring Intent +11%": "taggd.in",
    "Bengaluru Leads": "foundit.in",
    "Semiconductor Boom": "taggd.in",
    "GCC Expansion": "zyoin.com",
    "BFSI AI Surge": "foundit.in",
    "Global Offshoring to India": "ibtimes.co.in",
    "170M Global Tech Jobs": "weforum.org",
    "Pay Premium": "adecco.co.in",
    "IndiaAI Mission": "indiaai.gov.in",
}

FAVICON_URL = "https://www.google.com/s2/favicons"


def logo_url_for_domain(domain: str) -> str:
    params = urllib.parse.urlencode({"domain": domain, "sz": "128"})
    return f"{FAVICON_URL}?{params}"


def source_domain_from_link(link: str) -> str | None:
    hostname = urlparse(link).hostname or ""
    return hostname.replace("www.", "") or None


def attach_logo(item: dict) -> dict:
    enriched = dict(item)
    domain = COMPANY_DOMAINS.get(enriched.get("c", ""))
    if not domain:
        domain = source_domain_from_link(enriched.get("lk", ""))
    existing = enriched.get("logo", "")
    if domain and (not existing or not existing.startswith("http")):
        enriched["logo"] = logo_url_for_domain(domain)
    return enriched


def enrich_collection(items: list[dict]) -> list[dict]:
    return [attach_logo(item) for item in items]
