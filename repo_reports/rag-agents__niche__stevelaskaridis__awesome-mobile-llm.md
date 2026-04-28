---
repo_name: stevelaskaridis/awesome-mobile-llm
url: "https://github.com/stevelaskaridis/awesome-mobile-llm"
stars: 328
forks: 20
contributors_count: 4
last_commit_date: "2026-04-04T23:55:37+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T17:30:16.694613+00:00"
model: auto
duration_s: 45.3
clone_size_kb: 121
uses_mas: no
final_use_case: None
---
## 1. Overview

This repository is an **awesome list**, not an executable agent system. A user does not run an application here; they browse `README.md` to discover papers, model families, frameworks, benchmarks, and related links for mobile/on-device LLMs. The repo’s value is curation and organization of references (e.g., deployment frameworks, optimization papers, mobile-agent papers) rather than shipping code. In practice, the output a user gets is a structured knowledge index for research and engineering scouting.

## 2. Agent Framework & Architecture

No LLM agent framework is implemented in this repository. There are no source files for LangGraph, LangChain, CrewAI, AutoGen, LlamaIndex, or custom runtime orchestration; the repository contains only Markdown and metadata docs (`README.md`, `contributing.md`, `code-of-conduct.md`).

The “intelligence” is editorial, not programmatic: the maintainer curates categories and links in `README.md` (for example, sections like “Mobile-First LLMs,” “Infrastructure / Deployment,” and “Mobile-Related Use-cases”), but there is no runtime planner, router, prompt template, tool-calling loop, or agent graph in code.

## 3. Orchestration Pattern

Closest match: **other (static curated taxonomy), not an orchestration pattern**.  
There is no control flow between agents because there are no agents at runtime.

Representative evidence:

```30:36:README.md
## Mobile-First LLMs

The following Table shows sub-3B models designed for on-device deployments, sorted by year.

| Name   | Year | Sizes               | Primary Group/Affiliation                               | Publication                                 | Code Repository                                  | HF Repository                                             |
```

```103:111:README.md
## Infrastructure / Deployment of LLMs on Device

This section showcases frameworks and contributions for supporting LLM inference on mobile and edge devices.

### Deployment Frameworks

#### On-Device Inference Frameworks
```

These excerpts show documentation structure and categorization, not executable coordination logic.

## 4. Tools & External Integrations

No external tools/APIs are wired into a runnable agent pipeline in this repo.

What exists are outbound links to third-party projects/resources (e.g., `llama.cpp`, `MLC-LLM`, `Ollama`, arXiv, Hugging Face) listed in `README.md` as references, not integrated dependencies or called services. There are no package manifests, scripts, or code modules that invoke these systems.

## 5. Notable Code Walkthrough

- `README.md:1-27` — Defines project scope and table of contents; establishes this as a curated list for mobile/embedded LLM ecosystem tracking.
- `README.md:30-101` — Large tabular catalog of mobile-first/small models across years with links to papers, code repos, and model hubs.
- `README.md:103-153` — Curates deployment ecosystem (on-device inference frameworks and local model-serving options), useful for practitioners mapping tooling options.
- `README.md:454-504` — “Mobile-Related Use-cases” section includes agentic/mobile automation papers, but as citations only (no local implementation).
- `contributing.md:1-25` — Minimal contribution process; confirms maintenance workflow for list updates rather than software releases.

## 6. Use-Case Mapping

The assigned use case (`RAG + Agents`) does **not** match the repository contents after inspection. This repo does not implement retrieval pipelines, vector stores, agent planning loops, or multi-agent runtime collaboration. It is better categorized as **None** (from your allowed set), because it is a reference/curation repository rather than an executable system for workflow automation, code generation, browser/terminal control, simulation, or RAG+agents.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad and current curation of mobile/on-device LLM landscape with frequent updates (`README.md:5`, extensive 2024–2026 entries).
  - Strong taxonomy spanning models, deployment, benchmarking, optimization, surveys, and workshops.
  - High practical utility for literature review and tool discovery via centralized links.
  - Includes both academic and industry artifacts, improving ecosystem coverage.

- **Limitations:**
  - No executable code, experiments, or reproducible pipelines in-repo.
  - No agent architecture implementation despite listing agent-related papers.
  - No benchmarking scripts or datasets bundled locally.
  - Contribution guide is minimal and does not enforce data schema/validation for entries.

- **Research relevance:**
  - Useful as evidence of how the mobile-LLM field is being organized and tracked by practitioners.
  - Useful as a seed index for systematic literature review on on-device LLMs and mobile agents.
  - Not suitable as direct evidence of multi-agent system implementation techniques.
  - Can support meta-analysis of trends (model sizes, deployment stacks, publication venues) over time.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
