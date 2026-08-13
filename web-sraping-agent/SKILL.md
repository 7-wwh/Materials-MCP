---
name: web-sraping-agent
description: >
  Agent skill for searching the internet and scraping web content using Tavily and Exa.ai APIs
  with automatic fallback between providers. Scraped content is automatically cleaned,
  restructured into semantic chunks, and exported to CSV/Parquet for visualization and querying.
  Use this skill whenever the user needs to search the web, find current information online,
  scrape links, research a topic via live internet results, or fetch content from URLs.
  Triggers on phrases like "search the web", "look this up online", "find me links about",
  "scrape this page", "what's the latest on", or any task that requires live internet data
  beyond the model's training cutoff. Always prefer this skill over guessing at current facts.
---

# Web Search & Scraping Skill

Provides internet search and web scraping via **Tavily** and **Exa.ai**, with automatic
failover when one provider's quota is exhausted. Scraped results are automatically cleaned,
normalized, and exported to **CSV** and **Parquet** for easy visualization and analysis.

## Architecture

```
web-sraping-agent/
├── SKILL.md                       ← this file
├── data/                          ← persisted run data (gitignored)
│   └── <query-slug>/
│       ├── tavily_<timestamp>.json
│       ├── exa_<timestamp>.json
│       └── csv/                   ← structured exports
│           ├── results_<timestamp>.csv
│           └── results_<timestamp>.parquet
└── scripts/
    ├── tavily_search.py           ← Tavily search + scrape
    ├── exa_search.py              ← Exa.ai search + scrape
    └── scrape_to_structured.py    ← JSON → CSV/Parquet + cleanup
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

### Step 4 — Transform to Structured Format (NEW)
After successful scraping, automatically process the JSON results:
```bash
python scripts/scrape_to_structured.py \
  --input data/<query-slug>/tavily_<timestamp>.json \
  --output-dir data/<query-slug>/csv/ \
  --format csv+parquet \
  --chunk-size 300 \
  --normalize
```

This step:
- **Cleans** boilerplate, normalizes whitespace and formatting
- **Chunks** long content into semantic segments (~300 chars each)
- **Extracts** metadata (URL, title, source domain, chunk index)
- **Exports** to both CSV (human-readable) and Parquet (queryable)
- **Saves** results to `data/<query-slug>/csv/` with automatic timestamping

### Step 5 — Synthesize & Present Results
Parse the CSV/Parquet output and present to user:
- Display a summary table of sources (URL, domain, title, chunk count)
- Highlight key findings across chunks
- Offer the CSV file for download / further analysis
- Link to the underlying JSON for full audit trail

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

## Search Output Format (JSON)

Both search scripts emit **one JSON object** to stdout:
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

## Structured Export Format (CSV & Parquet)

The `scrape_to_structured.py` script transforms search JSON into a normalized table:

| Column       | Type   | Description |
|--------------|--------|-------------|
| `source_url` | string | Original URL scraped |
| `domain`     | string | Extracted domain (e.g., `example.com`) |
| `title`      | string | Page title from JSON result |
| `chunk_id`   | int    | Sequential chunk number within the page |
| `chunk_text` | string | Normalized, cleaned content (~300 chars) |
| `chunk_order`| int    | Position in original text (for reassembly) |
| `extracted_at`| string| ISO timestamp when content was scraped |
| `provider`   | string | `"tavily"` or `"exa"` |
| `query`      | string | Original search query |

**Example CSV rows:**
```
source_url,domain,title,chunk_id,chunk_text,chunk_order,extracted_at,provider,query
https://example.com/news,example.com,Breaking News,1,"Latest developments in AI research show promise...",0,2026-08-08T10:30:00Z,tavily,AI research updates
https://example.com/news,example.com,Breaking News,2,"Companies are investing heavily in machine learning...",1,2026-08-08T10:30:00Z,tavily,AI research updates
```

## Persistence (data/ folder)

Every run saves outputs in three forms:

1. **Raw JSON** (source of truth): `data/<query-slug>/tavily_<timestamp>.json`
   - Full unmodified scrape results
   - Includes all metadata
   - Used for re-processing and auditing

2. **CSV** (human-readable): `data/<query-slug>/csv/results_<timestamp>.csv`
   - Normalized table format
   - One row per content chunk
   - Import into Excel, pandas, or visualization tools

3. **Parquet** (queryable): `data/<query-slug>/csv/results_<timestamp>.parquet`
   - Columnar format for fast queries
   - Smaller file size than CSV
   - Use with DuckDB, Polars, or other analytical tools

**Run folder naming:**
- Named after the research prompt (slugified query, e.g. `fire truck seller` → `data/fire-truck-seller/`)
- Scrape-only runs use the first URL's domain instead

**Filenames are unique per run:**
- JSON: `tavily_20260805-085100.json`
- CSV: `results_20260805-085100.csv`
- Parquet: `results_20260805-085100.parquet`

**All runs are saved**, including failures — unsuccessful runs are marked by
their `status` field in JSON (`missing_key`, `bad_input`, `quota_exhausted`, etc.).

**Folders default to** `<project>/data` (relative to the scripts) and can be
overridden with `--data-dir /path/to/folder`.

Stdout JSON and exit codes are unchanged; saving is additive.
`data/` is gitignored.

## Cleanup & Normalization Logic

The `scrape_to_structured.py` script performs these cleaning steps:

1. **Remove boilerplate**
   - Navigation menus, headers, footers
   - Common ad patterns and tracking scripts
   - Sidebar content, related-articles sections

2. **Normalize formatting**
   - Collapse multiple whitespace to single space
   - Remove control characters
   - Standardize line breaks
   - Decode HTML entities

3. **Split into chunks**
   - Semantic sentence/paragraph boundaries (~300 chars, configurable)
   - Preserve chunk order for reassembly
   - Avoid mid-word breaks

4. **Extract metadata**
   - Page title, domain, extraction timestamp
   - Provider (Tavily/Exa) and original query
   - Chunk sequence numbers

## Chunking Strategy

Content is split using a tiered approach:

1. **Sentence-aware**: Split on `.`, `!`, `?` + space
2. **Paragraph-aware**: Then split on `\n\n` if sentences are too long
3. **Word-aware**: Then split on spaces if still exceeding max length
4. **Fallback**: Hard split at max length if no boundary found

Each chunk is assigned:
- `chunk_id`: sequential within the page
- `chunk_order`: position in document (preserves reading order)
- Character count and word count (metadata for filtering)

## Configuration Options

`scrape_to_structured.py` supports these flags:

```bash
--input <path>                       # Path to source JSON (required)
--output-dir <path>                  # CSV/Parquet output directory (required)
--format csv|parquet|csv+parquet|both  # Export format (default: both)
--chunk-size <int>                   # Target chunk size in chars (default: 300)
--normalize                          # Enable whitespace normalization (default: true)
--remove-duplicates                  # Remove duplicate chunks (default: true)
```

## Notes for Future Configuration
- Rate-limit retry logic (backoff/jitter) — to be added in scripts
- Result deduplication across providers — to be added in synthesis step
- Caching layer — to be added later
- ML-based boilerplate detection — to replace regex patterns
- Automatic schema detection from query type — to vary CSV columns by task
- Integration with vector DB (e.g., Chroma, Pinecone) for semantic search