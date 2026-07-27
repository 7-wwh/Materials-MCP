# Web Search and Scraping

An AI-orchestrated web research agent that finds, scrapes, extracts, and analyzes structured data from the web — using **Tavily + Exa.ai** to discover sources and a **scraper layer** to extract data, keeping concerns fully separated.

The Orchestrator ties it together: plan → search → scrape → extract → aggregate.

---

## Architecture

```
  ╔══════════════════════════════════╗
  ║  STEP 1: RECEIVE GOAL            ║
  ║  Orchestrator decomposes goal    ║
  ║  into search queries             ║
  ╚══════════════════════════════════╝
                   │
                   ▼
  ╔══════════════════════════════════╗
  ║  STEP 1.5: CHECK SCRAPE INDEX    ║
  ║  Load scrape_index.csv for this  ║
  ║  goal → set of scraped URLs      ║
  ╚══════════════════════════════════╝
                   │
                   ▼
  ╔══════════════════════════════════╗
  ║  STEP 2: SEARCH                  ║
  ║  Tavily / Exa.ai returns         ║
  ║  candidates → filter out         ║
  ║  URLs already in scrape index    ║
  ╚══════════════════════════════════╝
                   │
                   ▼
  ╔══════════════════════════════════╗
  ║  STEP 3: SCRAPE                  ║
  ║  Playwright / BS4 fetches        ║
  ║  pages → raw/{domain}/           ║
  ║  + append to scrape_index.csv    ║
  ╚══════════════════════════════════╝
                   │
                   ▼
  ╔══════════════════════════════════╗
  ║  STEP 4: EXTRACT                 ║
  ║  LLM reads raw/ → writes         ║
  ║  structured JSON to              ║
  ║  processed/{domain}.json         ║
  ╚══════════════════════════════════╝
                   │
                   ▼
  ╔══════════════════════════════════╗
  ║  STEP 5: AGGREGATE               ║
  ║  Collect all processed/          ║
  ║  files → analyzed/results.json   ║
  ╚══════════════════════════════════╝
```

**Key principle:** Search finds candidates. Scraper extracts pages. LLM analyzes. Each layer is independent and swappable.

---

## Workflow

| Step | What happens | Output |
|---|---|---|---|
| **1. Orchestrator receives goal** | Decomposes goal into search queries | `queries.json` in goal folder |
| **1.5. Check scrape index** | Loads `scrape_index.csv` for this goal | Set of already-scraped URLs |
| **2. Search API returns candidates** | Tavily / Exa.ai finds URLs → filters out indexed URLs | Filtered URL list with snippets |
| **3. Scraper visits each site** | Fetches pages, saves raw HTML, appends to index | `raw/{domain}/*.html`, `scrape_index.csv` row |
| **4. LLM extraction** | Processes raw files → structured JSON | `processed/{domain}.json` |
| **5. Aggregation** | Orchestrator collects all processed JSONs | `analyzed/results.json` |

### Step 1 — Orchestrator receives objective

Example: *"Find aluminium suppliers in Malaysia that provide extrusion profiles."*

The Orchestrator decomposes this into search queries:

```
- aluminium supplier Malaysia
- aluminium extrusion manufacturer Malaysia
- aluminium profile supplier Johor
- aluminium sheet supplier Malaysia
- aluminium alloy distributor Malaysia
```

### Step 1.5 — Check scrape index

Before searching, the Orchestrator loads `scrape_index.csv` for this goal:

```csv
domain,url,complete,timestamp
abc-aluminium.com,https://abc-aluminium.com,yes,2026-07-27T05:00:00Z
badsite.com,https://badsite.com,403,2026-07-27T05:02:00Z
```

Any URL with a non-empty `complete` has already been attempted — skip it.

| `complete` value | Meaning |
|---|---|
| `yes` | Scraped successfully |
| `403` / `timeout` / `captcha` / `login-wall` | Failed — but still indexed, won't retry |

### Step 2 — Search API returns candidates

Tavily or Exa.ai returns structured results. The Orchestrator filters out any URL already present in `scrape_index.csv`:

```json
[
  {
    "title": "ABC Aluminium Sdn Bhd",
    "url": "https://abc-aluminium.com",
    "snippet": "Manufacturer of aluminium extrusion profiles..."
  },
  {
    "title": "XYZ Metal Supplier",
    "url": "https://xyz-metal.com",
    "snippet": "Aluminium sheets and plates supplier..."
  }
]
```

At this point we know **who exists** — but not product catalogue, dimensions, alloys, certifications, MOQ, location, or contact details.

### Step 3 — Scraper visits each site

For each new URL, the scraper:

1. Fetches the page (Playwright or BS4)
2. Saves raw HTML + metadata → `raw/{domain}/`
3. Appends a row to `scrape_index.csv`

```
raw/abc-aluminium.com/
├── index.html
├── products.html
├── contact.html
├── about.html
└── meta.json              # HTTP status, content-type, scrape timestamp
```

The scraper fetches the homepage first. An LLM-powered **link router** decides which additional links to follow:

> "This page contains product info — follow it."
> "Careers page? Ignore."

Each followed page is also saved to `raw/{domain}/` and logged in `scrape_index.csv`.

If a page fails (403, timeout, CAPTCHA, login wall), the failure reason is recorded in `scrape_index.csv` and scraping continues to the next URL.

> "This page contains product info — follow it."
> "Careers page? Ignore."

### Step 4 — LLM extraction

Reads raw HTML from `raw/{domain}/`, extracts structured data, writes to `processed/`:

```json
{
  "company": "ABC Aluminium Sdn Bhd",
  "location": "Johor, Malaysia",
  "website": "https://abc-aluminium.com",
  "products": [
    {"name": "aluminium extrusion", "category": "profiles"},
    {"name": "custom profile", "category": "custom"}
  ],
  "materials": ["6063 aluminium alloy"],
  "services": ["cutting", "anodizing"],
  "certifications": ["ISO 9001:2015"],
  "contact": {
    "email": "sales@abc-aluminium.com",
    "phone": "+60-7-555-0123"
  },
  "source_urls": [
    "https://abc-aluminium.com/products.html",
    "https://abc-aluminium.com/contact.html"
  ]
}
```

### Step 5 — Aggregation

All suppliers are treated equally. Orchestrator collects all `processed/*.json` files into a single results collection:

```json
{
  "goal": "Find aluminium suppliers in Malaysia...",
  "generated_at": "2026-07-27T05:00:00Z",
  "suppliers": [
    { ... ABC Aluminium ... },
    { ... XYZ Metal ... },
    { ... }
  ]
}
```

---

## Staged Folder Structure

```
output/
└── goals/
    └── find-aluminium-suppliers-malaysia/
        ├── queries.json              # Search queries generated by Orchestrator
        ├── candidates.json           # Raw results from Tavily / Exa.ai
        ├── scrape_index.csv          # Dedup index — domain,url,complete,timestamp
        ├── raw/
        │   ├── abc-aluminium.com/
        │   │   ├── index.html
        │   │   ├── products.html
        │   │   ├── contact.html
        │   │   └── meta.json
        │   └── xyz-metal.com/
        │       ├── index.html
        │       └── meta.json
        ├── processed/
        │   ├── abc-aluminium.com.json
        │   └── xyz-metal.com.json
        └── analyzed/
            └── results.json          # Aggregated, deduplicated
```

Each stage is a plain directory on disk. You can inspect, re-run, or fix individual steps without restarting from scratch.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | Python, direct API calls (no framework) |
| Search APIs | Tavily SDK + Exa.ai SDK (configurable) |
| Scraping | Playwright (dynamic JS), BeautifulSoup (static HTML) |
| Link routing | Small LLM (e.g. GPT-4o-mini, Claude Haiku) |
| Extraction | Large LLM — structured output mode (OpenAI / Claude) |
| Output | JSON files on filesystem |

---

## Project Structure

```
web-search-scraping/
├── main.py                       # Entry point
├── config.py                     # API keys, env vars, default goal
├── orchestrator.py               # Agent loop: plan → index check → search → scrape → extract → analyze
├── index/
│   └── scrape_index.py           # Read/write scrape_index.csv, check duplicates
├── search/
│   ├── client.py                 # Unified Tavily / Exa.ai wrapper
│   └── query_generator.py        # Decompose goal into search queries
├── scrape/
│   ├── playwright_scraper.py     # JS-heavy pages
│   ├── static_scraper.py         # Simple HTML pages
│   └── link_router.py            # LLM decides which links to follow per page
├── extract/
│   └── llm_extractor.py          # Reads raw HTML → writes processed JSON
├── aggregate/
│   └── aggregator.py             # Merge processed JSONs into results.json
├── schemas/
│   ├── supplier.py               # Pydantic models
│   ├── product.py
│   └── base.py
├── output/                       # Staged folder root (gitignored)
│   └── .gitkeep
└── .env.example
```

---

## Implementation Phases

| Phase | Description |
|---|---|
| **1. Scaffold** | Project structure, config, env, Pydantic schemas |
| **2. Search + Index module** | Tavily + Exa.ai integration, query generation, scrape index read/write |
| **3. Scraper module** | Playwright + BS4, raw folder output, link router |
| **4. Extractor** | LLM reads `raw/` → writes `processed/` structured JSON |
| **5. Aggregation** | Build aggregator, `analyzed/` output |
| **6. Orchestrator loop** | Wire full pipeline end-to-end, iterative refinement |
| **7. Anti-blocking** | Proxies, rotating user-agents, rate limiting |
| **8. DB migration (future)** | Only if JSON output grows beyond filesystem practicality |

---

## Design Principles

- **Separation of concerns**: Search finds pages. Scraper extracts data. LLM analyses. One component never does another's job.
- **Never scrape the same URL twice**: The scrape index prevents redundant work across multiple runs of the same goal.
- **Filesystem as pipeline**: `raw/ → processed/ → analyzed/`. You can inspect, edit, or resume any stage manually.
- **Start narrow, stay narrow**: Target a specific goal (e.g. "Find 100 Malaysian aluminium suppliers"), not a general crawl.
- **LLM as decision-maker, not crutch**: Small models for routing and classification. Large models for extraction and analysis.
- **Pluggable search**: Tavily and Exa.ai are both supported via a common interface. Adding a new provider is a single adapter.
