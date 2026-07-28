---
name: web-search
description: >
  Agent skill for searching the internet and scraping web content using Tavily and Exa.ai APIs
  with automatic fallback between providers. Use this skill whenever the user needs to search
  the web, find current information online, scrape links, research a topic via live internet
  results, or fetch content from URLs. Triggers on phrases like "search the web", "look this up
  online", "find me links about", "scrape this page", "what's the latest on", or any task that
  requires live internet data beyond the model's training cutoff. Always prefer this skill over
  guessing at current facts.
---

# Web Search Skill

Provides internet search and web scraping via **Tavily** and **Exa.ai**, with automatic
failover when one provider's quota is exhausted.

## Architecture

```
web-search-skill/
├── SKILL.md                  ← this file
└── scripts/
    ├── tavily_search.py      ← Tavily search + scrape
    └── exa_search.py         ← Exa.ai search + scrape
```

## Provider Selection Logic

Always attempt **Tavily first**. Fall back to **Exa** when Tavily returns any of:
- HTTP 429 (rate limit / quota exhausted)
- `{"error": "quota exceeded"}` or similar in the response body
- Any non-2xx status that indicates a usage limit

If both providers fail, surface the error clearly to the user and suggest they check their
API keys or quota dashboards.

## Workflow

### Step 1 — Understand the request
Determine what the user needs:
- **Search only** → find relevant links and titles
- **Search + scrape** → find links then fetch full page content
- **Scrape only** → user provides URL(s) directly

### Step 2 — Run Tavily script
```bash
python scripts/tavily_search.py \
  --query  "<search query>" \
  --mode   search|scrape|both \
  --urls   "https://..." \          # only for scrape/both
  --max-results 5                   # default 5
```
Check exit code and stdout for quota errors (see Quota Detection below).

### Step 3 — Fallback to Exa if needed
If Tavily signals quota exhaustion:
```bash
python scripts/exa_search.py \
  --query  "<search query>" \
  --mode   search|scrape|both \
  --urls   "https://..." \
  --max-results 5
```

### Step 4 — Synthesize results
Parse the JSON output from whichever script succeeded and present:
- For **search**: numbered list of titles + URLs + short snippets
- For **scrape**: the extracted text content of each page
- For **both**: search results followed by scraped content of the top results

## Quota Detection

Both scripts print a JSON line to stdout on failure:
```json
{"status": "quota_exhausted", "provider": "tavily", "message": "..."}
```
Check for `status == "quota_exhausted"` before treating the output as a result.

## API Keys

Keys are read from environment variables:
| Variable          | Provider |
|-------------------|----------|
| `TAVILY_API_KEY`  | Tavily   |
| `EXA_API_KEY`     | Exa.ai   |

If a key is missing the script exits with code 1 and prints:
```json
{"status": "missing_key", "provider": "...", "message": "Set TAVILY_API_KEY / EXA_API_KEY"}
```

## Output Format

Both scripts emit **one JSON object** to stdout:
```json
{
  "status": "ok",
  "provider": "tavily",
  "query": "...",
  "results": [
    {
      "title": "...",
      "url": "...",
      "snippet": "...",
      "content": "..."   // present only when scraping
    }
  ]
}
```

## Notes for Future Configuration
- Rate-limit retry logic (backoff/jitter) — to be added in scripts
- Result deduplication across providers — to be added in synthesis step
- Caching layer — to be added later
- Max content length per scraped page — configurable via `--max-content` flag (default: 2000 chars)
