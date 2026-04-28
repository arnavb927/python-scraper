---
repo_name: oxylabs/how-to-scrape-google-images
url: "https://github.com/oxylabs/how-to-scrape-google-images"
stars: 1686
forks: 3
contributors_count: 3
last_commit_date: "2026-03-24T08:49:33+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 2
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-04-27T17:13:59.746693+00:00"
model: auto
duration_s: 46.6
clone_size_kb: 147
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a small Python CLI scraper that takes an input image URL, submits it to Google Lens/Google Images via Selenium, extracts related image result metadata, and writes the output to a CSV file. A user runs `make scrape URL="..."` (or `python -m google_images_scraper --url=...`) and receives an `images.csv` file with `title`, image URL, and source page URL fields. The core flow is deterministic browser automation plus HTML element extraction, not an interactive AI system. The README also documents an alternative paid Oxylabs API workflow, but that code is tutorial text, not runtime code in the package.

## 2. Agent Framework & Architecture

No LLM agent framework is used in the actual codebase. There are no imports or runtime dependencies for LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, OpenAI/Anthropic SDKs, or any prompt/LLM components (`pyproject.toml:11-19`, `src/google_images_scraper/*.py`).

Architecture is a simple 3-layer scraper pipeline: CLI entrypoint -> collector/orchestrator -> Selenium scraper. The CLI parses `--url` and calls `GoogleImagesDataCollector.save_image_data_for_url()` (`src/google_images_scraper/__main__.py:15-24`). The collector calls the scraper, handles errors, and writes results to CSV through pandas (`src/google_images_scraper/collector.py:18-56`). The scraper initializes Chrome WebDriver, accepts consent, navigates to an upload-by-URL endpoint, parses result cards, and returns `Image` models (`src/google_images_scraper/scraper.py:35-114`, `src/google_images_scraper/models.py:8-11`).

There is no multi-agent decomposition, planner, router, role-based prompting, or graph state machine. “Intelligence” is entirely procedural scraping logic and DOM selectors.

## 3. Orchestration Pattern

Closest match: **sequential** (single-process workflow automation), not hierarchical/graph/swarm/event-driven.

Control flow is linear:
1) CLI receives URL -> 2) collector requests scrape -> 3) scraper executes browser steps -> 4) collector serializes to CSV.

Example flow wiring:

`src/google_images_scraper/__main__.py:21-24`
```python
def scrape_google_images(url: str) -> None:
    collector = GoogleImagesDataCollector()
    collector.save_image_data_for_url(url)
```

`src/google_images_scraper/collector.py:44-56`
```python
self._logger.info(f"Getting Google Images data for image url {url}..")
try:
    images = self._scraper.query_images_for_url(url)
except Exception:
    self._logger.exception(f"Error when scraping Google Images for url {url}.")
    return

if not images:
    self._logger.info("No images found.")
    return

self._save_to_csv(images)
```

## 4. Tools & External Integrations

- **Selenium browser automation (Chrome WebDriver)**: core runtime tool for browsing Google Lens and extracting page elements (`src/google_images_scraper/scraper.py:10-14`, `42-83`).
- **WebDriver Manager**: downloads/installs compatible ChromeDriver automatically (`src/google_images_scraper/scraper.py:14`, `48-49`).
- **Google Lens web endpoint**: target service for reverse-image search upload-by-URL (`src/google_images_scraper/conf.py:13-16`, used at `scraper.py:80`).
- **Pandas CSV output**: stores scraped objects in `images.csv` (`src/google_images_scraper/collector.py:9`, `30-35`).
- **Click CLI**: command-line interface for user input (`src/google_images_scraper/__main__.py:7`, `15-21`).
- **No MCP, vector DB, RAG stack, or LLM API integration** in runtime package code.

## 5. Notable Code Walkthrough

- `src/google_images_scraper/__main__.py:15-27` - Defines the CLI command and required `--url` parameter, then triggers the collection pipeline; this is the user-facing entrypoint.
- `src/google_images_scraper/collector.py:18-56` - Implements application-level orchestration: invokes scraper, handles failures/no-results, persists output CSV.
- `src/google_images_scraper/scraper.py:42-114` - Core scraping engine: sets up headless Chrome, accepts consent form, navigates to Google Lens upload URL, and parses image cards into structured objects.
- `src/google_images_scraper/conf.py:10-19` - Encapsulates configurable base URL and constructs the upload-by-URL endpoint used by the scraper.
- `src/google_images_scraper/models.py:8-11` - Defines the typed `Image` data model (`title`, `url`, `source_url`) for clean transfer between scraping and persistence layers.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is partially accurate because the package automates a real browser (Selenium/Chrome) and is executed from terminal commands (`Makefile:10-17`, `scraper.py:42-83`). However, this is better categorized as **Workflow Automation** for this taxonomy: it is a scripted ETL-style pipeline (input URL -> scrape -> structured CSV output) without interactive browser agent behavior, tool-using LLM, or autonomous decision loops. So the stronger final mapping is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, minimal pipeline with separation between CLI, scraping, and persistence (`__main__.py`, `collector.py`, `scraper.py`).
  - Practical browser-based reverse image scraping that handles consent flow and headless execution (`scraper.py:51-65`).
  - Typed output model and straightforward CSV export improve downstream usability (`models.py:8-11`, `collector.py:30-35`).
  - Easy local execution via Make targets and Poetry setup (`Makefile:4-17`).

- **Limitations:**
  - Fragile DOM dependency: hardcoded consent XPath and class names may break on UI changes (`scraper.py:40`, `81`).
  - No retry/backoff, pagination, rate handling, or anti-bot robustness.
  - Broad exception handling hides root-cause granularity at collector level (`collector.py:45-49`).
  - No tests, benchmarks, or reproducibility harness in repository source tree.
  - README includes additional API examples not integrated into package runtime, which can blur expected behavior.

- **Research relevance:**
  - Useful as evidence of **non-agent workflow automation** patterns in scraping pipelines.
  - Illustrates deterministic orchestration vs. LLM-agentic orchestration in practical tooling.
  - Demonstrates browser automation integration (Selenium + driver management) in a compact architecture.
  - Not suitable as evidence for multi-agent coordination, planning, or emergent agent behavior.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
