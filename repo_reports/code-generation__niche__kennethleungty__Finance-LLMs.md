---
repo_name: kennethleungty/Finance-LLMs
url: "https://github.com/kennethleungty/Finance-LLMs"
stars: 118
forks: 21
contributors_count: 3
last_commit_date: "2026-03-16T15:43:12+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 5
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents]
generated_at: "2026-04-27T14:44:14.582492+00:00"
model: auto
duration_s: 47.3
clone_size_kb: 838
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`kennethleungty/Finance-LLMs` is a curated dataset-style repository, not an executable agent system. The main artifact is a large `README.md` table that catalogs real-world finance LLM deployments, fine-tuned models, and integrated products across banking, wealth, markets, payments, and insurance. A user “runs” this repo by browsing or contributing entries, following the contribution template in `CONTRIBUTING.md`. The output is a structured knowledge base of external case studies and papers, rather than generated code, workflows, or live agent behavior.

## 2. Agent Framework & Architecture

No agent framework is actually implemented in this repository. There are no Python/JS source files and no runtime imports for LangGraph, LangChain, CrewAI, AutoGen, LlamaIndex, or similar orchestration libraries; repository contents are markdown documents (`README.md`, `CONTRIBUTING.md`).

Architecturally, this is a manually maintained taxonomy of external systems. The “intelligence” is editorial: contributors classify each external example by segment (`Retail & Commercial Banking`, `Wealth & Asset Management`, etc.) and type (`Enterprise Platform`, `Fine-Tuned Model`, `Integrated Solution`) in markdown tables (`README.md:36-160` and onward). The contribution process is lightweight governance rules for formatting and sourcing (`CONTRIBUTING.md:5-33`), not LLM planning/routing logic.

## 3. Orchestration Pattern

Closest match: **other (static documentation / curated index), not an orchestration runtime**.

There is no control-flow code between agents in this repo. The only “flow” is contributor workflow: follow submission guidelines and append a row in markdown.

Example excerpts:

`CONTRIBUTING.md:5-19`
```text
## Submission Guidelines
1. Verify your contribution isn't already listed ...
...
## Entry Format
| Company/Model Name | Type | Month Year | Brief description | ...
```

`README.md:38-41`
```text
## Retail & Commercial Banking
| Name | Type | Date | Description | Site | Paper |
| --- | --- | --- | --- | --- | --- |
| HSBC & Harvey AI | Enterprise Platform | Jan 2026 | ...
```

## 4. Tools & External Integrations

No external tools or APIs are wired up in code within this repository.

What exists is **references to external platforms** inside documentation entries (e.g., OpenAI, Azure OpenAI, Amazon Bedrock, Google Vertex/Gemini, LangChain in third-party case descriptions), but these are not integrated by repository code (`README.md` table rows such as `README.md:41-49`, `README.md:84-90`, `README.md:116-121`).

## 5. Notable Code Walkthrough

- `README.md:7-32` — Defines project scope and categorization scheme for finance LLM use cases; this is the conceptual backbone of the repo.
- `README.md:36-160` — Representative section showing the core data format: large tabular entries of company/model, type, date, description, and links.
- `README.md:106-123` — Capital-markets segment with examples that mention multi-agent systems externally (e.g., FinRpt, Moody’s AI Studio), illustrating the repo’s role as an index of *other* implementations.
- `CONTRIBUTING.md:5-29` — Contribution protocol and strict row template; governs how new records are added and standardized.
- `CONTRIBUTING.md:21-24` — Defines the three classification labels contributors must use, reinforcing consistency in the curated dataset.

## 6. Use-Case Mapping

The assigned primary use case (**Code Generation**) does **not** match the actual repository contents. This repo does not generate code, run LLM pipelines, or execute agents; it curates and categorizes external examples in markdown. A better category from the provided list is **Workflow Automation** only in a very loose sense (human editorial workflow), but technically this is closer to a static “awesome-list/knowledge base” pattern outside the taxonomy options. Given the forced label set, **Workflow Automation** is the nearest fit.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad, up-to-date coverage across multiple financial subdomains in one place (`README.md` sectioned tables).
  - Consistent schema (name/type/date/description/links) enables easy downstream scraping or meta-analysis.
  - Contribution guide enforces quality signals (reputable sources, non-duplicate entries).
  - Includes both industry deployments and research papers, useful for triangulating practice vs. academia.

- **Limitations:**
  - No executable code, benchmarks, or reproducible pipelines for any listed system.
  - No verification layer beyond contributor curation; claims rely on external sources.
  - Not a true multi-agent repository despite frequent mention of agentic systems in descriptions.
  - No metadata validation, CI checks, or structured data export (JSON/CSV) for analysis workflows.

- **Research relevance:**
  - Useful evidence of market adoption patterns of LLMs in finance (by segment and deployment type).
  - Can support qualitative studies on enterprise vs. fine-tuned vs. integrated-solution trends.
  - Provides a source list for selecting candidate systems to study in depth elsewhere.
  - Not suitable as direct evidence of agent architecture implementation details.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
