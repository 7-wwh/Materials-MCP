#!/usr/bin/env python3
"""
Hybrid web scraper: tries static requests + BeautifulSoup first, falls back to
Playwright when a page is JS-rendered or blocks plain HTTP.

Usage:
    python scripts/scrape.py --file urls.txt
    python scripts/scrape.py --file urls.txt --out /tmp/scraped --max-text 5000

Input file: one URL per line; blank lines and lines starting with # are ignored.

Output: one JSON file per URL at <out>/<hostname>/<slug>_<timestamp>.json
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data"
DEFAULT_MAX_TEXT = 10000
DEFAULT_TIMEOUT = 20
MIN_TEXT = 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "index"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_urls(path: str) -> list[str]:
    urls = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls


def _extract_text(html: str) -> tuple[str, str]:
    """Return (title, readable_text) with boilerplate stripped."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    for tag in soup.find_all(
        ["script", "style", "noscript", "header", "footer", "nav", "aside", "form"]
    ):
        tag.decompose()
    for el in soup.find_all(attrs={"aria-hidden": "true"}):
        el.decompose()
    lines = [ln.strip() for ln in soup.get_text(separator="\n").splitlines()]
    return title, "\n".join(ln for ln in lines if ln)


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def _static_fetch(url: str, timeout: int) -> tuple[int, str]:
    resp = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    resp.raise_for_status()
    return resp.status_code, resp.text


def _playwright_fetch(url: str, timeout: int) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=UA)
            page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            except Exception:
                pass
            return page.content()
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# Scraping + persistence
# ---------------------------------------------------------------------------

def _scrape_url(url: str, timeout: int, max_text: int) -> dict:
    payload = {
        "url": url,
        "title": "",
        "status": None,
        "engine": "failed",
        "scraped_at": _now(),
        "text": "",
    }
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        payload["error"] = f"invalid URL: {url}"
        return payload

    status = None
    html = None
    try:
        status, html = _static_fetch(url, timeout)
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
    except Exception as exc:
        payload["error"] = f"{type(exc).__name__}: {exc}"

    title, text = "", ""
    if html:
        title, text = _extract_text(html)

    if status != 200 or not html or len(text) < MIN_TEXT:
        try:
            html = _playwright_fetch(url, timeout)
            title, text = _extract_text(html)
            payload.update({"status": 200, "engine": "playwright"})
            payload.pop("error", None)
        except Exception as exc:
            if not (status and html):
                payload["error"] = f"{type(exc).__name__}: {exc}"
                payload["status"] = status
                return payload
            payload["engine"] = "static"
            payload.pop("error", None)
    else:
        payload["engine"] = "static"

    payload.update({
        "status": status if status is not None else payload.get("status"),
        "title": title,
        "text": text[:max_text],
    })
    return payload


def save(payload: dict, out_dir: Path) -> Path:
    parsed = urlparse(payload["url"])
    host = parsed.hostname or "unknown"
    slug = _slugify(parsed.path)
    run_dir = out_dir / host
    run_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = run_dir / f"{slug}_{ts}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main():
    p = argparse.ArgumentParser(description="Hybrid static/JS web scraper")
    p.add_argument("--file", required=True, help="Path to a file with one URL per line")
    p.add_argument("--out", default="", help=f"Output root (default: {DEFAULT_OUT})")
    p.add_argument(
        "--max-text",
        type=int,
        default=DEFAULT_MAX_TEXT,
        help=f"Max chars saved per page (default: {DEFAULT_MAX_TEXT})",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Per-request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    args = p.parse_args()

    out_dir = Path(args.out).expanduser() if args.out else DEFAULT_OUT
    urls = _read_urls(args.file)
    if not urls:
        print("no URLs found in file")
        sys.exit(1)

    ok = failed = 0
    for url in urls:
        result = _scrape_url(url, args.timeout, args.max_text)
        path = save(result, out_dir)
        if result["engine"] == "failed":
            failed += 1
            print(f"[failed] {url} — {result.get('error')}")
        else:
            ok += 1
            print(f"[{result['engine']}] {result['status']} {url} — text: {len(result['text'])} chars -> {path}")

    print(f"\nDone: {ok} scraped, {failed} failed. Output: {out_dir}")


if __name__ == "__main__":
    main()
