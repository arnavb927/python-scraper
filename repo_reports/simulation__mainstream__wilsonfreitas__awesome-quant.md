---
repo_name: wilsonfreitas/awesome-quant
url: "https://github.com/wilsonfreitas/awesome-quant"
stars: 25746
forks: 3430
contributors_count: 187
last_commit_date: "2026-04-23T00:43:31+00:00"
primary_use_case: Simulation
user_tier: Mainstream
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T09:31:23.744780+00:00"
model: auto
duration_s: 63.7
clone_size_kb: 1666
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`awesome-quant` is a curated-list repository plus a small data pipeline that converts `README.md` entries into a browsable static website. Maintainers run `parse.py` (with a GitHub token) to parse list items, enrich them with GitHub metadata (stars, last commit), and write `site/projects.csv`; then they run `site/generate.py` to produce `site/index.html`. A scheduled GitHub Action executes this pipeline daily and on relevant pushes, then deploys the site to GitHub Pages (`.github/workflows/build.yml:1-40`). Users get an updated quant-project catalog with filtering/search UI, not an LLM assistant or agent runtime.

## 2. Agent Framework & Architecture

No LLM agent framework is implemented in this codebase. I found no runtime imports/usages of LangGraph, LangChain, CrewAI, AutoGen, LlamaIndex, OpenAI/Anthropic SDKs, or prompt/planner/router abstractions in executable project scripts (`parse.py`, `site/generate.py`, `topic.py`, `cranscrape.py`, `scripts/migrate_readme.py`).

The architecture is a deterministic ETL-style workflow:
1) parse markdown entries from `README.md`,
2) enrich metadata via APIs/web scraping,
3) emit CSV,
4) generate static HTML from CSV/readme,
5) deploy via CI (`parse.py:251-296`, `site/generate.py:487-511`, `.github/workflows/build.yml:17-40`).

There are references to “agents” inside list-item descriptions in `README.md`, but those are cataloged third-party projects, not this repository’s own runtime behavior.

## 3. Orchestration Pattern

Closest match: **sequential workflow automation** (not multi-agent orchestration).

Control flow is linear in CI (`build.yml`), while `parse.py` does parallel I/O using Python threads for each project entry. That is concurrency, but not coordinated LLM agents.

Example 1 (pipeline sequencing in CI): `.github/workflows/build.yml:26-37`
```yaml
- name: Run parser
  run: |
    export GITHUB_ACCESS_TOKEN=${{ secrets.GITHUB_TOKEN }}
    uv run python parse.py
- name: Generate site
  run: |
    uv run python site/generate.py
```

Example 2 (thread fan-out/fan-in in parser): `parse.py:270-291`
```python
p = Project(m, primary_language, current_category, current_category)
p.languages = languages
p.clean_description = clean_description
p.start()
projects.append(p)

while True:
    checks = [not p.is_alive() for p in projects]
    if all(checks):
        break
```

## 4. Tools & External Integrations

- **GitHub REST API via PyGithub**: fetches repository commits/stars and topic search (`parse.py:9-14`, `parse.py:159-173`, `topic.py:3-25`).
- **CRAN web pages (HTML scrape)**: obtains publication date and possible GitHub URL (`parse.py:34-98`).
- **PyPI JSON API**: resolves last-updated dates for PyPI packages (`parse.py:100-128`, `.claude/skills/update-pypi-dates/scripts/check_pypi_dates.py:26-55`).
- **GitHub Actions + GitHub Pages deployment**: scheduled/triggered automation and publish step (`.github/workflows/build.yml:1-40`).
- **Local filesystem artifacts**: reads `README.md`, writes `site/projects.csv` and `site/index.html` (`parse.py:253-296`, `site/generate.py:488-507`).

No MCP client wiring, vector DB, browser automation framework, terminal-agent loop, or LLM tool-calling runtime is implemented in project code.

## 5. Notable Code Walkthrough

- `parse.py:141-173,175-248,251-296` - Core ingestion/enrichment script: regex-parse README entries, extract language tags, call GitHub/CRAN/PyPI sources, and emit structured CSV.
- `site/generate.py:26-110,113-141,275-484,487-511` - Static-site generator: loads CSV/readme, normalizes fields, builds HTML table/filter UI, and writes the final page.
- `.github/workflows/build.yml:1-40` - Operational backbone: daily and push-triggered pipeline that runs parser + generator and deploys to `gh-pages`.
- `scripts/migrate_readme.py:237-295,298-359,379-447` - One-off migration utility for reorganizing README sections and inline language tags; demonstrates deterministic rule-based transformations.
- `topic.py:19-25` - Auxiliary GitHub topic discovery script; simple API search helper, no autonomous planning/agent behavior.

## 6. Use-Case Mapping

The assigned primary use case (**Simulation**) looks incorrect for this repository’s own code. The repo does not simulate environments/agents; it curates links and automates content processing/deployment. A better category is **Workflow Automation**: scheduled ETL-style parsing, metadata enrichment, static-site generation, and deployment (`parse.py`, `site/generate.py`, `.github/workflows/build.yml`). Also, this is not a multi-agent system; it is an automation pipeline for maintaining an awesome list.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, reproducible pipeline from markdown source to deployable site.
  - Practical metadata enrichment (stars/activity dates) using lightweight APIs.
  - Resilient fallback logic for non-GitHub sources (CRAN/PyPI dates).
  - Minimal dependency footprint and straightforward CI automation.
  - Good separation of parsing (`parse.py`) vs presentation (`site/generate.py`).

- **Limitations:**
  - No internal LLM/agent runtime despite “agent” content in listed projects.
  - Threading model in `parse.py` has no explicit rate-limit/backoff controls for large-scale GitHub API usage.
  - Limited test scaffolding visible for parser/generator correctness regressions.
  - Some automation ideas exist only as docs/specs, not implemented runtime files (e.g., PR-review agent spec).
  - Data quality depends on strict README formatting conventions and regex assumptions.

- **Research relevance:**
  - Useful as evidence of **non-agentic automation pipelines** in open-source curation workflows.
  - Useful for studying markdown-to-structured-data transformation and CI-driven publishing.
  - Not suitable as evidence of multi-agent coordination, LLM planning, or tool-using autonomous agents.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
