# MAS GitHub Scraper

A production-ready scraper that discovers, filters, scores, and classifies
public GitHub repositories related to **Multi-Agent Systems (MAS)** and
**agentic AI**, for use in academic research on practical real-world usage
patterns.

## Features

- **Discovery** via the GitHub REST Search API:
  - Topic queries: `multi-agent-systems`, `multi-agent-system`, `agentic-ai`
  - Keyword (README) queries: agent orchestration, LLM agent framework,
    swarm intelligence, agent collaboration, multi-agent workflow, agent
    handoff, tool use.
  - Deduplicated by `owner/repo`.
- **Hard quality filters**: stars ≥ 50, contributors ≥ 3, last commit within
  6 months, non-empty README.
- **Additive scoring model** covering popularity tiers, forks tiers, activity
  signals, README docs quality, LangGraph usage, arXiv links and GAIA
  mentions.
- **Architecture classification**: LangGraph, LangChain, AutoGen, CrewAI, or
  Custom/Other (multi-label).
- **Use-case classification**: Workflow Automation, Code Generation,
  RAG + Agents, Browser / Terminal Use, Simulation, or Uncategorised
  (multi-label).
- **Rate-limit aware** (`X-RateLimit-*` headers) with exponential backoff on
  403/429 and a courtesy 0.5 s pause between calls.
- **Outputs**: `mas_repos.csv` (sorted by score desc) + `mas_repos_summary.json`.
- **Console summary** with totals, use-case / architecture / tier breakdowns,
  and top-10 repos by score.

## Setup

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1
# Windows (recommended, avoids .py file-association issues)
# py -m venv .venv

pip install -r requirements.txt
```

## Authentication

A personal access token (classic or fine-grained, public-repo read scope is
enough) is strongly recommended. Without it, GitHub caps you at 60
unauthenticated requests per hour and the scraper will stall.

```bash
# macOS / Linux
export GITHUB_TOKEN=ghp_xxx

# Windows PowerShell
$env:GITHUB_TOKEN = "ghp_xxx"
```

## Run

```bash
python mas_scraper.py
# Windows (recommended)
# py mas_scraper.py
# or use wrapper:
# .\mas_scraper.cmd
```

## Windows convenience wrappers

If your Windows `.py` association is broken, run these wrappers (they call
`py` directly and bypass file-association dialogs):

- `.\mas_scraper.cmd`
- `.\build_balanced_sample.cmd`
- `.\analyze_repos.cmd`

Expect the full run to take anywhere from ~15 minutes to an hour depending on
how many repos survive discovery and your current rate-limit budget. Progress
and diagnostics are streamed to `stderr` while the final summary prints to
`stdout`.

## Outputs

- `mas_repos.csv` — one row per surviving repo, all fields, sorted by
  `total_score` descending. List fields (`topics`, `architecture_labels`,
  `use_case_labels`) are pipe-joined inside a cell.
- `mas_repos_summary.json` — the same data as a JSON array for programmatic
  downstream analysis.

## Scoring reference

| Signal | Points |
| --- | --- |
| Stars > 5000 | +3 |
| Stars 500–5000 | +2 |
| Stars 100–500 | +1 |
| Forks > 500 | +2 |
| Forks 100–500 | +1 |
| Open issues > 10 | +1 |
| Watchers > 100 | +1 |
| README "Architecture" / "How it Works" section | +1 |
| LangGraph primitives (`StateGraph` / `add_node` / `add_edge`) | +2 |
| arXiv link in README | +1 |
| GAIA mention in README | +1 |

## Notes / caveats

- GitHub's Search API caps every query at 1000 results (10 pages × 100). The
  scraper sorts by stars descending to keep the most relevant hits inside that
  window.
- Contributor count is derived from the `Link: rel="last"` page number on
  `/contributors?per_page=1&anon=true`; repos with fewer than one full page
  fall back to counting the returned list.
- Architecture detection only samples up to three top-level `.py` files per
  repo to keep API usage bounded; the README is the primary signal source.
