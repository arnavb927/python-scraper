---
repo_name: bansky-cl/diffusion-nlp-paper-arxiv
url: "https://github.com/bansky-cl/diffusion-nlp-paper-arxiv"
stars: 289
forks: 16
contributors_count: 3
last_commit_date: "2026-04-22T09:21:56+00:00"
primary_use_case: Simulation
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T17:34:37.531579+00:00"
model: auto
duration_s: 56.6
clone_size_kb: 1695
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a scheduled paper-harvesting automation script, not an interactive AI app. A GitHub Action runs `daily_arxiv.py` twice a day, queries arXiv for diffusion-related papers, filters to NLP-relevant categories, optionally enriches each paper with a code repo link from Papers With Code, and rewrites `docs/arxiv-daily.json`, `imgs/trend.png`, and `README.md` (`.github/workflows/main.yml:3-57`, `daily_arxiv.py:62-113`, `daily_arxiv.py:310-332`). In practice, the user “runs” it via GitHub Actions (or `python daily_arxiv.py` locally) and gets an updated markdown paper list plus a trend plot. The output is a continuously refreshed bibliography-style tracker.

## 2. Agent Framework & Architecture

No LLM agent framework is used. I found no imports/usages of LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, OpenAI SDKs, or prompt/orchestration code; the runtime logic is plain Python data processing (`daily_arxiv.py:1-11`, `daily_arxiv.py:62-113`).

Architecture is single-process ETL-style automation:
1) fetch papers from arXiv via the `arxiv` Python client,  
2) filter categories (`KEEP`/`BLOCKS`),  
3) enrich with Papers With Code API via `requests`,  
4) persist merged JSON,  
5) render markdown table,  
6) generate trend chart via `matplotlib` (`daily_arxiv.py:21-23`, `daily_arxiv.py:62-149`, `daily_arxiv.py:150-307`).

There are no multiple roles, no planner/worker split, no routing logic, and no autonomous decision loop beyond deterministic filters and loops.

## 3. Orchestration Pattern

Closest match: **sequential workflow automation (single-agent / non-agentic script)**.

Control flow is linear in `__main__`, with fixed function calls:

```310:332:daily_arxiv.py
if __name__ == "__main__":
    data_collector = []
    keywords = dict()
    keywords["diffusion"] = "ti:\"diffusion\""  + "OR" + "ti:\" diffus\""
    ...
    update_json_file(json_file, data_collector)
    json_to_trend(json_file, img_file)
    json_to_md(json_file, md_file)
```

Scheduling/orchestration is externalized to GitHub Actions cron:

```6:12:.github/workflows/main.yml
on:
  workflow_dispatch:
  schedule:
    - cron: '0 8,22 * * *'
```

So orchestration exists, but it is CI job scheduling + function sequencing, not multi-agent coordination.

## 4. Tools & External Integrations

- **arXiv API (via `arxiv` Python package):** search/retrieval of papers (`daily_arxiv.py:4`, `daily_arxiv.py:68-83`).
- **Papers With Code API (HTTP):** code repository enrichment (`daily_arxiv.py:19`, `daily_arxiv.py:97-103`).
- **GitHub Actions:** periodic execution and auto-commit back to repo (`.github/workflows/main.yml:3-12`, `.github/workflows/main.yml:52-60`).
- **Matplotlib:** local chart generation (`daily_arxiv.py:7`, `daily_arxiv.py:244-307`).
- **Filesystem JSON/Markdown writes:** local persistence of harvested data (`daily_arxiv.py:134-149`, `daily_arxiv.py:172-243`).

No MCP servers, browser automation, shell tool-calling by an LLM, vector DB, or RAG retrieval stack were found.

## 5. Notable Code Walkthrough

- `daily_arxiv.py:62-113` - Core ingestion/enrichment loop. Executes arXiv search, category filtering, optional Papers With Code lookup, and markdown row construction; this is the heart of the pipeline.
- `daily_arxiv.py:134-149` - Merge/update persistence logic for `docs/arxiv-daily.json`, including backward-compatible wrapping of older rows with collapsible abstracts.
- `daily_arxiv.py:150-243` - Markdown renderer that rewrites `README.md` with badges, update timestamp, table headers, and all rows for each keyword bucket.
- `daily_arxiv.py:244-307` - Monthly trend computation + image export (`imgs/trend.png`) from IDs in JSON.
- `.github/workflows/main.yml:24-60` - Operational wiring: installs deps, runs script on cron, and commits generated artifacts back to `main`.

## 6. Use-Case Mapping

The upstream assigned use case (`Simulation`) looks incorrect based on code. This repository does not simulate environments/agents; it automates a repeatable data collection and publishing pipeline for papers. The better category is **Workflow Automation**: scheduled fetch → transform/enrich → publish artifacts (`daily_arxiv.py:310-332`, `.github/workflows/main.yml:48-57`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, reproducible scheduled pipeline with minimal operational overhead (`.github/workflows/main.yml:6-12`).
  - Practical data enrichment by combining arXiv metadata with Papers With Code links (`daily_arxiv.py:97-103`).
  - Output artifacts are immediately usable (README table + JSON + trend chart) (`daily_arxiv.py:150-243`, `daily_arxiv.py:244-307`).
  - Handles arXiv pagination edge cases via `UnexpectedEmptyPageError` (`daily_arxiv.py:51-60`).

- **Limitations:**
  - No LLM/agent functionality despite topic overlap with “diffusion NLP” papers (`daily_arxiv.py:1-11`).
  - Hard-coded keyword and category filters reduce flexibility (`daily_arxiv.py:21-23`, `daily_arxiv.py:315-317`).
  - Broad exception handling around API calls may hide specific failure modes (`daily_arxiv.py:98-103`).
  - README regeneration is full overwrite; no incremental diffing or provenance metadata (`daily_arxiv.py:172-177`).

- **Research relevance:**
  - Useful as evidence of **automation around AI literature monitoring**, not evidence of multi-agent system design.
  - Illustrates lightweight integration of scholarly APIs and CI/CD for continuously updated knowledge artifacts.
  - Can be cited as an example of “AI-adjacent DevOps workflow,” not agent orchestration or LLM planning.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
