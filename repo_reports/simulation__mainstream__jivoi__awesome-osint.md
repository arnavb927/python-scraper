---
repo_name: jivoi/awesome-osint
url: "https://github.com/jivoi/awesome-osint"
stars: 25941
forks: 3565
contributors_count: 251
last_commit_date: "2026-04-22T11:03:26+00:00"
primary_use_case: Simulation
user_tier: Mainstream
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T11:44:28.671394+00:00"
model: auto
duration_s: 53.9
clone_size_kb: 338
uses_mas: no
final_use_case: None
---
## 1. Overview

`jivoi/awesome-osint` is a curated knowledge repository, not an executable AI system. The core artifact is a large Markdown catalog of OSINT tools/resources organized by category, which users browse directly on GitHub (`README.md`) rather than run as software. Contributors expand the list via pull requests following formatting and sorting rules in `CONTRIBUTING.md`. The output a user gets is a human-readable reference list of links, not programmatic results from an agent pipeline.

## 2. Agent Framework & Architecture

No LLM agent framework is implemented in this repository. I found no runtime source files (`*.py`, `*.js`, `*.ts`, notebooks, Docker/runtime manifests) and no imports for LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, or OpenAI SDKs.

The repository is documentation-only: a single large list in `README.md` and contribution policy in `CONTRIBUTING.md`. The “intelligence” is human curation by maintainers/contributors, not prompts, planners, routers, graphs, or role-based agent code. Example: the repo describes itself as “A curated list...” and then immediately presents category headings and link bullets (`README.md:1-7`, `README.md:99-130`).

## 3. Orchestration Pattern

Closest match: **other (manual editorial workflow), not agent orchestration**.

There is no machine control flow between agents. Instead, the only explicit workflow is contributor guidance (search duplicates, sort alphabetically, open one PR per suggestion) in `CONTRIBUTING.md:3-16`.

Short evidence excerpts:

```1:10:CONTRIBUTING.md
Please ensure your pull request adheres to the following guidelines:

- Read the awesome manifesto...
- Search previous suggestions before making a new one...
- Insert a new entry alphabetically.
- Make an individual pull request for each suggestion.
```

```87:103:README.md
## [↑](#-table-of-contents) Contributing

Please read [CONTRIBUTING](./CONTRIBUTING.md) if you wish to add tools or resources.
...
## [↑](#-table-of-contents) General Search
* [Aol](https://search.aol.com) - The web for America.
```

## 4. Tools & External Integrations

No executable integrations are wired in code. What exists is a Markdown index of third-party OSINT websites/tools (e.g., search engines and security resources) as outbound links.

- **External websites listed as references:** `README.md:103-130` (Aol, Bing, Perplexity, Phind, Dork tools, etc.).
- **Static site presentation config only:** Jekyll theme setting in `_config.yml:1`.
- **No API clients / SDK wiring:** no source files or dependency manifests were found in-repo.

## 5. Notable Code Walkthrough

- `README.md:1-7` — Establishes repo purpose as a curated OSINT resource list; this is the core “product” users consume.
- `README.md:13-86` — Massive table of contents defining taxonomy of OSINT domains; this is the primary organizational structure.
- `README.md:99-130` — Representative section content: bullet links with short descriptions; demonstrates data model is plain Markdown entries.
- `CONTRIBUTING.md:3-17` — Defines governance/workflow for human contributors, which is how the repository evolves.
- `_config.yml:1` — Minimal static-site config (`jekyll-theme-hacker`), confirming doc-hosting orientation rather than application runtime.

## 6. Use-Case Mapping

The assigned primary use case (`Simulation`) does not match the actual repository contents. This repo does not simulate environments, agents, or scenarios; it curates links and descriptions for OSINT tooling. It also does not implement RAG pipelines, code generation agents, browser automation, or terminal-driving agent behavior. Best category from the allowed set is **`None`** (documentation/awesome-list repository with no agent runtime).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Very broad OSINT coverage with clear taxonomy (`README.md` TOC spans many domains).
  - Low-friction discoverability: direct links plus concise annotations per item.
  - Strong contributor process for consistency (`CONTRIBUTING.md` alphabetical and PR rules).
  - Maintained as a community knowledge base (large contributor ecosystem implied by repo activity).

- **Limitations:**
  - No executable code, so no reproducible pipelines or benchmarkable system behavior.
  - No runtime architecture to analyze for agent coordination, planning, or tool use.
  - Quality control is editorial/manual; no automated validation of link freshness or metadata.
  - Not suitable for evaluating LLM-agent performance, safety, latency, or failure modes.

- **Research relevance:**
  - Useful as evidence of **human-curated tooling ecosystems** around security/OSINT.
  - Can be cited as a dataset source for downstream tool-selection or retrieval studies (after external preprocessing).
  - Not valid evidence for multi-agent orchestration techniques in deployed software.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
