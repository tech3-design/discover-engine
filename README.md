# SIGNAL Discovery Engine

A comprehensive site discovery and analysis engine that produces formal, detailed reports about any URL. It examines 22 distinct aspects of a webpage across 7 analysis domains and generates a professional **Site Discovery Report** — a structured document that describes exactly what was found, with full evidence.

This is not a scoring tool. It is a discovery tool. Every analysis describes **what was analyzed**, **what was found**, and provides the **raw evidence** behind each observation.

## What It Analyzes

The engine performs **22 independent analyses** organized into 7 domains:

| Domain | Analyses | What It Discovers |
|--------|----------|-------------------|
| **Site Foundation** | 9 | robots.txt configuration, XML/image/video/news sitemaps, HTTPS, canonical tags, crawl traps, robots meta directives |
| **Indexability & Performance** | 2 | Viewport & resource hints, JS rendering strategy (SSR vs CSR) |
| **Graph & Discovery** | 2 | Internal linking structure & anchor text, llms.txt presence |
| **Node Readability** | 3 | JSON-LD structured data (19 schema types), Open Graph & Twitter Card metadata, semantic HTML |
| **Authority & Trust** | 3 | Author E-E-A-T (byline, credentials, trust domains, trust pages, publication dates, source diversity, transparency), entity & brand identity, expertise schema |
| **LLM Extraction** | 2 | AI visibility (answer-first format, citations, self-contained paragraphs, definitions, quotability, content chunking), FAQ/Q&A extractability |
| **Content Quality** | 1 | Citations, statistics, expert quotes, authoritative tone, readability (Flesch-Kincaid), technical terminology, vocabulary diversity, paragraph structure, keyword repetition |

## Report Output

The engine produces a **Site Discovery Report** — a formal analysis document:

```json
{
  "document_type": "Site Discovery Report",
  "generated_at": "2026-03-10T12:00:00+00:00",
  "url": "https://example.com",
  "executive_summary": "Site infrastructure: HTTPS, robots.txt present, XML sitemap present. Structured data includes 4 schema type(s): Article, Organization, WebSite, BreadcrumbList. Content analysis: 2,450 words, 7 citation patterns, 12 statistical references...",
  "methodology": "This report was generated through automated static analysis...",
  "sections": [
    {
      "title": "Site Foundation",
      "description": "This section examines the fundamental technical infrastructure...",
      "analyses": [
        {
          "subject": "Robots.txt Configuration",
          "methodology": "Analysis of the robots.txt file, which controls how search engine and AI crawlers access the site...",
          "observations": [
            "A robots.txt file was found at the root of the site.",
            "The robots.txt does not contain a blanket Disallow: / directive.",
            "A Sitemap directive was found in robots.txt.",
            "No restrictions on AI-specific crawlers were found."
          ],
          "evidence": {
            "blocked_bots": [],
            "has_sitemap_directive": true
          }
        }
      ]
    }
  ]
}
```

Each analysis includes:
- **Subject** — what was analyzed
- **Methodology** — how it was analyzed
- **Observations** — what was found (formal, factual statements)
- **Evidence** — the raw extracted data

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/discovery-engine.git
cd discovery-engine

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -e ".[dev]"

# Copy environment config
cp .env.example .env
```

### Run the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

### Run a Discovery

```bash
# 1. Start a discovery
curl -X POST http://localhost:8000/api/v1/discover \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Response: {"audit_id": "abc123", "status": "pending", "url": "https://example.com"}

# 2. Check status
curl http://localhost:8000/api/v1/discover/abc123/status

# 3. Get the full discovery report (PDF)
curl -o report.pdf http://localhost:8000/api/v1/discover/abc123/report

# Optional: request JSON instead of PDF
curl http://localhost:8000/api/v1/discover/abc123/report?format=json
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/discover` | Start a new site discovery (returns `202`) |
| `GET` | `/api/v1/discover/{id}/status` | Check discovery status |
| `GET` | `/api/v1/discover/{id}/results` | Get raw analysis results |
| `GET` | `/api/v1/discover/{id}/report` | Get the formal Site Discovery Report (PDF by default, `format=json` for JSON) |

Interactive API documentation is available at `/docs` (Swagger UI) when the server is running.

## Architecture

```
app/
├── main.py                    # FastAPI app, checker registration
├── config.py                  # Environment-based settings
├── api/v1/                    # API routes
├── checkers/                  # 22 analysis checkers (7 domains)
│   ├── base.py                # BaseChecker abstract class
│   ├── registry.py            # Singleton checker registry
│   ├── site_foundation/       # 9 checkers
│   ├── indexability_speed/    # 2 checkers
│   ├── graph_discovery/       # 2 checkers
│   ├── node_readability/      # 3 checkers
│   ├── authority_trust/       # 3 checkers
│   ├── llm_extraction/        # 2 checkers
│   └── content_quality/       # 1 checker
├── models/                    # Pydantic models & enums
├── services/                  # Crawler, audit, scoring, report
├── store/                     # In-memory audit store
└── utils/                     # HTML/URL helpers
```

**Key design decisions:**
- **Async throughout** — httpx for crawling, FastAPI for serving
- **Checker registry pattern** — checkers self-register on import, easy to add new ones
- **Background processing** — discoveries run as background tasks, clients poll for status
- **Discovery-first** — every checker extracts and reports data; scores are a secondary byproduct

## Adding a New Checker

1. Create a file in the appropriate domain folder (e.g., `app/checkers/content_quality/my_checker.py`)
2. Extend `BaseChecker`:

```python
from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult


class MyChecker(BaseChecker):
    check_id = "my_checker"
    check_number = 23
    name = "My Analysis"
    layer = Layer.CONTENT_QUALITY

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings = []
        details = {}

        # Discover things...
        findings.append("something_found")
        details["extracted_data"] = [...]

        return self._make_result(score, findings, details)
```

3. Register it in the domain's `__init__.py`:

```python
from .my_checker import MyChecker
registry.register(MyChecker())
```

4. Add a methodology description in `app/services/report_service.py` → `_SECTION_DESCRIPTIONS`
5. Add finding text in `_FINDING_TEXT` or parameterized handlers in `_humanize_finding()`

## Configuration

All settings are configurable via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | SIGNAL Discovery Engine | Service name |
| `DEBUG` | false | Debug mode |
| `CORS_ORIGINS` | localhost:3000,8000 | Allowed CORS origins |
| `LOG_LEVEL` | INFO | Logging level |
| `CRAWLER_TIMEOUT` | 15 | HTTP request timeout (seconds) |
| `CRAWLER_MAX_RETRIES` | 2 | Retry count for failed requests |

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test
pytest tests/test_health.py
```

## License

[MIT](LICENSE)
# discover-engine
