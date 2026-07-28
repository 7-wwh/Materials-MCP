#!/usr/bin/env python3
"""
Exa.ai Search & Scrape Script
-------------------------------
Fallback web search provider. Mirrors the interface of tavily_search.py so the
skill can swap providers transparently.

Usage:
    python exa_search.py --query "AI news 2025" --mode search --max-results 5
    python exa_search.py --urls "https://example.com" --mode scrape
    python exa_search.py --query "AI news" --mode both --max-results 3

Environment:
    EXA_API_KEY  — required
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_BASE = "https://api.exa.ai"
SEARCH_ENDPOINT = f"{API_BASE}/search"
CONTENTS_ENDPOINT = f"{API_BASE}/contents"
DEFAULT_MAX_RESULTS = 5
DEFAULT_MAX_CONTENT = 2000  # chars per scraped page


# ---------------------------------------------------------------------------
# Output helpers  (identical contract to tavily_search.py)
# ---------------------------------------------------------------------------

def emit(payload: dict):
    """Print a single JSON object to stdout."""
    print(json.dumps(payload, ensure_ascii=False))


def fatal(status: str, message: str, provider: str = "exa"):
    emit({"status": status, "provider": provider, "message": message})
    sys.exit(1 if status not in ("ok",) else 0)


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def _post(url: str, payload: dict, api_key: str) -> dict:
    """
    Minimal HTTP POST using only stdlib — no third-party dependencies.
    Returns parsed JSON or raises urllib.error.HTTPError.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,           # Exa uses x-api-key header
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search(query: str, api_key: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]:
    """Run an Exa neural search and return a normalised list of result dicts."""
    payload = {
        "query": query,
        "numResults": max_results,
        "type": "auto",            # let Exa pick neural vs keyword
        "contents": {
            "text": False,         # skip body text in search phase
            "highlights": {
                "numSentences": 2,
                "highlightsPerUrl": 1,
            },
        },
    }
    data = _post(SEARCH_ENDPOINT, payload, api_key)
    results = []
    for item in data.get("results", []):
        # Flatten highlights into a single snippet string
        highlights = item.get("highlights", []) or []
        snippet = " … ".join(highlights) if highlights else ""
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": snippet,
        })
    return results


def scrape(urls: list[str], api_key: str, max_content: int = DEFAULT_MAX_CONTENT) -> list[dict]:
    """Fetch full text content for a list of URLs via Exa /contents."""
    payload = {
        "ids": urls,               # Exa accepts URLs directly as IDs
        "contents": {
            "text": True,
        },
    }
    data = _post(CONTENTS_ENDPOINT, payload, api_key)
    results = []
    for item in data.get("results", []):
        text = item.get("text", "") or ""
        results.append({
            "url": item.get("url", ""),
            "title": item.get("title", ""),
            "snippet": "",
            "content": text[:max_content],
        })
    return results


# ---------------------------------------------------------------------------
# Quota / error detection
# ---------------------------------------------------------------------------

def _is_quota_error(exc: urllib.error.HTTPError) -> bool:
    """Return True if the HTTP error indicates quota/rate-limit exhaustion."""
    if exc.code == 429:
        return True
    if exc.code == 402:
        return True
    try:
        body = exc.read().decode("utf-8")
        body_lower = body.lower()
        if any(kw in body_lower for kw in ("quota", "limit exceeded", "rate limit", "credits")):
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Exa.ai search/scrape wrapper")
    p.add_argument("--query", default="", help="Search query string")
    p.add_argument(
        "--mode",
        choices=["search", "scrape", "both"],
        default="search",
        help="Operation mode (default: search)",
    )
    p.add_argument(
        "--urls",
        nargs="*",
        default=[],
        help="URLs to scrape (required for scrape/both modes without a query)",
    )
    p.add_argument(
        "--max-results",
        type=int,
        default=DEFAULT_MAX_RESULTS,
        help=f"Max search results (default: {DEFAULT_MAX_RESULTS})",
    )
    p.add_argument(
        "--max-content",
        type=int,
        default=DEFAULT_MAX_CONTENT,
        help=f"Max chars per scraped page (default: {DEFAULT_MAX_CONTENT})",
    )
    return p.parse_args()


def main():
    args = parse_args()

    # --- Key check ---
    api_key = os.environ.get("EXA_API_KEY", "").strip()
    if not api_key:
        fatal("missing_key", "Set the EXA_API_KEY environment variable.")

    # --- Validate inputs ---
    if args.mode in ("search", "both") and not args.query:
        fatal("bad_input", "--query is required for mode 'search' or 'both'.")
    if args.mode == "scrape" and not args.urls:
        fatal("bad_input", "--urls is required for mode 'scrape'.")

    search_results: list[dict] = []
    scrape_results: list[dict] = []
    urls_to_scrape: list[str] = list(args.urls)

    try:
        # --- Search phase ---
        if args.mode in ("search", "both"):
            search_results = search(args.query, api_key, args.max_results)
            if args.mode == "both" and not urls_to_scrape:
                urls_to_scrape = [r["url"] for r in search_results if r["url"]]

        # --- Scrape phase ---
        if args.mode in ("scrape", "both") and urls_to_scrape:
            scrape_results = scrape(urls_to_scrape, api_key, args.max_content)

    except urllib.error.HTTPError as exc:
        if _is_quota_error(exc):
            fatal("quota_exhausted", f"Exa quota exhausted (HTTP {exc.code}). Both providers are at limit.")
        else:
            fatal("http_error", f"Exa HTTP error {exc.code}: {exc.reason}")
    except urllib.error.URLError as exc:
        fatal("network_error", f"Network error contacting Exa: {exc.reason}")
    except Exception as exc:  # noqa: BLE001
        fatal("unexpected_error", f"Unexpected error: {exc}")

    # --- Merge results ---
    merged: dict[str, dict] = {}
    for r in search_results:
        merged[r["url"]] = r
    for r in scrape_results:
        url = r["url"]
        if url in merged:
            merged[url]["content"] = r["content"]
            if r.get("title"):
                merged[url]["title"] = merged[url]["title"] or r["title"]
        else:
            merged[url] = r

    emit({
        "status": "ok",
        "provider": "exa",
        "query": args.query,
        "mode": args.mode,
        "results": list(merged.values()),
    })


if __name__ == "__main__":
    main()
