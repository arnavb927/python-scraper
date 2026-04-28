---
repo_name: oxylabs/how-to-scrape-google-flights
url: "https://github.com/oxylabs/how-to-scrape-google-flights"
stars: 1633
forks: 7
contributors_count: 3
last_commit_date: "2026-03-26T11:24:49+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 2
architecture_labels: [Custom/Other]
use_case_labels: [Browser / Terminal Use]
generated_at: "2026-04-27T17:14:59.926002+00:00"
model: auto
duration_s: 60.2
clone_size_kb: 167
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a Python scraping utility for extracting flight listings from Google Flights and saving them as structured output. A user runs a CLI command (`python -m google_flights_scraper --url=...` via `make scrape`) that launches a headless Chrome session, accepts Google’s consent form, scrapes visible flight cards, and writes results to `flights.csv` (`src/google_flights_scraper/__main__.py:15-27`, `src/google_flights_scraper/collector.py:37-56`). It captures fields like price, departure/arrival time, airline, stops, and full details (`src/google_flights_scraper/models.py:8-15`). The repo also includes a standalone example script that uses Oxylabs’ Realtime API plus BeautifulSoup to fetch and parse flight HTML (`examples/google_flights_scraper_example.py:49-101`). In practice, this is a deterministic data-collection workflow, not an LLM-driven system.

## 2. Agent Framework & Architecture

No LLM agent framework is used here. There are no imports or runtime usage of LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, OpenAI/Anthropic SDKs, prompt templates, planner/router components, or tool-calling abstractions (`pyproject.toml:11-21`; codebase-wide imports in `src/google_flights_scraper/*.py` and `examples/*.py`).

Architecture is a straightforward scraper pipeline:
1) CLI entrypoint receives URL,  
2) collector invokes scraper and handles errors/output,  
3) scraper drives Selenium to fetch and parse DOM nodes into `Flight` models.  
Key flow lives in `src/google_flights_scraper/__main__.py:15-27`, `src/google_flights_scraper/collector.py:18-56`, and `src/google_flights_scraper/scraper.py:36-162`.

“Intelligence” is rule-based DOM extraction (fixed CSS class names/XPath and string splits), not model-based reasoning (`src/google_flights_scraper/scraper.py:41-106`).

## 3. Orchestration Pattern

Closest match: **sequential** (single-process pipeline), not multi-agent.

Control flow is linear from CLI to collector to scraper:

```python
# src/google_flights_scraper/__main__.py (approx 15-24)
@click.command()
@click.option("--url", required=True)
def scrape_google_flights(url: str) -> None:
    collector = GoogleFlightsDataCollector()
    collector.save_flight_data_for_url(url)
```

```python
# src/google_flights_scraper/collector.py (approx 44-56)
try:
    flights = self._scraper.get_flights_for_url(url)
except Exception:
    self._logger.exception(...)
    return

if not flights:
    self._logger.info("No flights found.")
    return

self._save_to_csv(flights)
```

Inside the scraper, browser init -> consent click -> page scrape happens in fixed order (`src/google_flights_scraper/scraper.py:145-161`).

## 4. Tools & External Integrations

- **Selenium + Chrome WebDriver** for browser automation and DOM extraction, wired in `GoogleFlightsScraper` (`src/google_flights_scraper/scraper.py:11-15`, `43-51`, `108-130`).
- **webdriver-manager** to auto-install/manage Chromedriver (`src/google_flights_scraper/scraper.py:15`, `49-50`).
- **Google Flights website** as the target source (URL input + default flights URL for consent page) (`src/google_flights_scraper/conf.py:8-14`, `src/google_flights_scraper/scraper.py:56`, `113`).
- **Pandas** for CSV serialization (`src/google_flights_scraper/collector.py:9`, `30-35`).
- **Oxylabs Realtime API** appears in the example script only (POST to `https://realtime.oxylabs.io/v1/queries` with basic auth), not integrated into the main package runtime (`examples/google_flights_scraper_example.py:49-68`).
- **No MCP servers, vector DBs, RAG stack, LLM APIs, or agent tool-runtime** detected.

## 5. Notable Code Walkthrough

- `src/google_flights_scraper/scraper.py:36-162` - Core scraper engine: initializes headless Chrome, accepts consent, locates flight cards (`pIav2d`), extracts fields from nested DOM nodes, and returns typed `Flight` objects. This file contains the main business logic and operational failure points.
- `src/google_flights_scraper/collector.py:18-56` - Orchestration and persistence layer: calls scraper, handles exceptions/empty results, converts model objects into a DataFrame, and writes CSV output.
- `src/google_flights_scraper/__main__.py:15-27` - Minimal CLI entrypoint using Click; this is what users invoke from terminal workflows.
- `src/google_flights_scraper/models.py:8-15` - Pydantic schema for normalized flight records, enforcing required fields.
- `examples/google_flights_scraper_example.py:49-118` - Alternative tutorial script using Oxylabs API + BeautifulSoup parsing; useful for paid API-based scraping but separate from packaged CLI flow.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is partially accurate because the primary tool runs from terminal and automates a real browser session via Selenium (`Makefile:10-17`, `src/google_flights_scraper/scraper.py:43-51`). However, this repository does **not** implement agentic behavior (no planning, role specialization, iterative tool selection, or model-guided interaction). Functionally, it is better categorized as **Workflow Automation**: a scripted ETL-like flow from URL input -> scrape -> structured file output (`src/google_flights_scraper/collector.py:37-56`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, minimal CLI-to-output path; easy to run and understand (`__main__.py`, `Makefile`).
  - Typed output model via Pydantic improves schema consistency (`models.py`).
  - Separation of concerns between scraping, orchestration, and config (`scraper.py`, `collector.py`, `conf.py`).
  - Includes both free Selenium approach and API-based tutorial variant (`examples/google_flights_scraper_example.py`).

- **Limitations:**
  - Fragile selectors/XPath tied to Google Flights markup; likely to break on UI changes (`scraper.py:41`, `69-94`, `115`).
  - Uses fixed `time.sleep` waits instead of explicit Selenium waits; reliability/performance risk (`scraper.py:65`, `114`).
  - Broad exception handling may mask root causes (`collector.py:45-49`, `scraper.py:150-159`).
  - No test suite or CI-visible validation of scraper behavior in repo files.
  - No proxy/session rotation/retry logic in core scraper, limiting robustness at scale.

- **Research relevance:**
  - Useful as an example of **non-agent automation pipelines** often mislabeled as “agentic.”
  - Demonstrates deterministic browser automation architecture for structured data extraction.
  - Can serve as a baseline comparator against true multi-agent/LLM orchestration systems.
  - Illustrates practical brittleness challenges (selector drift, wait strategy) in web automation.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
