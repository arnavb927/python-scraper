---
repo_name: keon/awesome-physical-ai
url: "https://github.com/keon/awesome-physical-ai"
stars: 217
forks: 20
contributors_count: 3
last_commit_date: "2026-03-30T22:14:05+00:00"
primary_use_case: Simulation
user_tier: Niche
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T15:45:17.272816+00:00"
model: auto
duration_s: 49.6
clone_size_kb: 169
uses_mas: no
final_use_case: None
---
## 1. Overview

This repository is not an executable agent system; it is an “awesome list” knowledge curation project. The main artifact is a long `README.md` containing categorized links to papers, projects, datasets, simulators, and companies in Physical AI (VLA models, world models, embodied robotics). A user does not run code here; they browse the Markdown taxonomy to discover literature and external resources. The practical output is a curated reading map, not model inference, agent orchestration, or simulation runtime behavior.

## 2. Agent Framework & Architecture

No LLM/agent framework is actually implemented in this repo. I found no Python/JS source files, no package manifests, and no runtime imports for LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, OpenAI SDKs, or similar. The repository content is effectively `README.md` + `LICENSE` (+ git metadata), with no executable architecture.

The “intelligence” in this project is editorial structure in Markdown headings and bullet lists, not computational logic. For example, the repo defines taxonomic sections such as “VLA Architectures,” “World Models,” and “Simulation Platforms,” then manually lists references under each (`README.md:9-53`, `README.md:56-90`, `README.md:1226-1235`).

## 3. Orchestration Pattern

Closest match: **other (static curated document), not an orchestration system**.  
There is no runtime control flow between agents because there are no agents defined or executed.

Evidence snippets:

```9:20:README.md
## Table of Contents

- [Foundations](#foundations)
  - [Vision-Language Backbones](#vision-language-backbones)
...
- [Resources](#resources)
  - [Datasets & Benchmarks](#datasets--benchmarks)
  - [Simulation Platforms](#simulation-platforms)
```

```1226:1235:README.md
## Contributing

We welcome contributions! Please submit a pull request to add relevant papers, correct errors, or improve organization.

### Guidelines

- Focus on **Physical AI** papers (robotics, embodied agents, world models, VLAs)
- Each paper should appear in only one category
```

## 4. Tools & External Integrations

No runtime tool integrations are wired up in code, because no runnable agent code exists.  
What exists are outbound links in Markdown to external papers/projects (e.g., arXiv, GitHub, lab websites) as references (`README.md` throughout, e.g., `README.md:62-72`, `README.md:1196-1205`).

## 5. Notable Code Walkthrough

- `README.md:1-53` — Defines project scope and taxonomy; this is the core “product” users interact with.
- `README.md:56-260` — Representative content section listing Physical AI papers/resources with paper/project/code links; demonstrates manual curation pattern.
- `README.md:1192-1207` — “Related Works” section linking other awesome lists, reinforcing this repo’s role as a meta-index.
- `README.md:1210-1235` — Citation and contribution guidelines; explains maintenance workflow (community PRs) rather than software execution.
- `LICENSE:1-122` — CC0 license text; confirms this is open reference content distribution rather than a software package.

## 6. Use-Case Mapping

The assigned primary use case (**Simulation**) appears incorrect for this repository itself. While it contains a “Simulation Platforms” subsection and many simulation-related paper links, the repo does not implement a simulator, simulation workflow, or agent-in-simulation loop. It is best categorized as a curated reference list and does not fit the provided operational categories as an executable system. Therefore the better classification is **None**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad, well-structured coverage of Physical AI topics across VLA, world models, reasoning, deployment, and benchmarks.
  - High discoverability via detailed table of contents and fine-grained thematic sections.
  - Includes many direct links (paper/project/code), reducing search friction for researchers.
  - Contribution guidance is clear, which supports ongoing curation quality.

- **Limitations:**
  - No executable code, experiments, or reproducible pipelines in this repo.
  - No implemented LLM agents, orchestration logic, or tool-calling runtime.
  - No versioned dataset snapshots/metadata validation scripts for link integrity.
  - As a manually maintained list, quality/coverage can drift without active curation.

- **Research relevance:**
  - Useful as evidence of **community curation practices** in embodied/physical AI literature.
  - Useful as a bibliographic entry point for surveying VLA/world-model trends.
  - Not suitable as evidence of multi-agent architecture design, agent coordination, or tool-using agent behavior.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
