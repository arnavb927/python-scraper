---
repo_name: tkmru/awesome-edr-bypass
url: "https://github.com/tkmru/awesome-edr-bypass"
stars: 1520
forks: 153
contributors_count: 3
last_commit_date: "2026-01-26T18:06:04+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [RAG + Agents]
generated_at: "2026-04-27T15:17:22.599717+00:00"
model: auto
duration_s: 49.1
clone_size_kb: 46
uses_mas: no
final_use_case: None
---
## 1. Overview

This repository is not an executable software project; it is an “awesome list” that curates links about EDR bypass techniques, tools, workshops, talks, blogs, and books. A user does not run code from this repo; they read `README.md` and follow external links to other projects and references. The content is aimed at ethical hacking and defensive awareness, as explicitly stated in the intro (`README.md:3-8`). In practice, the output a user gets is a categorized bibliography, not an agent workflow, model response, or programmatic artifact.

## 2. Agent Framework & Architecture

No LLM or agent framework is used in this repository. There are no source files implementing LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, or custom agent loops; the repo contains only `README.md` (`git ls-tree -r --name-only HEAD` returns just `README.md`).

Architecturally, this is a static documentation index organized by headings such as “PoC,” “Tool,” “Workshop,” “Presentation,” and “Blog” (`README.md:9-115`). There are no agent definitions, prompts, planner/router logic, runtime state, or orchestration code.

## 3. Orchestration Pattern

Closest match: **other (none / non-applicable)**.

There is no runtime control flow between agents because no agents are implemented. The structure is editorial categorization of links, e.g.:

```9:14:README.md
## PoC
- [trickster0/TartarusGate: TartarusGate, Bypassing EDRs](https://github.com/trickster0/TartarusGate)
- [am0nsec/HellsGate: Original C Implementation of the Hell's Gate VX Technique](https://github.com/am0nsec/HellsGate)
    - The paper PDF has a nice summary of EDR Bypass techniques.
- [Maldev-Academy/HellHall: Performing Indirect Clean Syscalls](https://github.com/Maldev-Academy/HellHall)
```

and:

```66:73:README.md
## Blog
- [Living-Off-the-Blindspot - Operating into EDRs’ blindspot | Naksyn’s blog](https://www.naksyn.com/edr%20evasion/2022/09/01/operating-into-EDRs-blindspot.html)
  - Type of person who works hard in Python; uses [PEP 578 – Python Runtime Audit Hooks](https://peps.python.org/pep-0578/).
- [Bypass CrowdStrike Falcon EDR protection against process dump like lsass.exe | by bilal al-qurneh | Medium](https://medium.com/@balqurneh/bypass-crowdstrike-falcon-edr-protection-against-process-dump-like-lsass-exe-3c163e1b8a3e)
```

## 4. Tools & External Integrations

No internal tools, APIs, services, or integrations are wired up in code in this repository.

What exists is outbound documentation links to third-party resources (GitHub repos, conference PDFs, blog posts), all referenced directly in `README.md` (e.g., `README.md:27-40`, `README.md:49-65`, `README.md:91-109`), but none are programmatically integrated.

## 5. Notable Code Walkthrough

- `README.md:1-8` — Defines the project scope and ethical framing; this is the only “entry point” users interact with.
- `README.md:9-40` — Curated sections for PoCs and tools; this is where most practical external repositories are indexed.
- `README.md:41-65` — Workshop and presentation references; useful for learning context rather than runnable artifacts.
- `README.md:66-109` — Blog and subtopic collections (including BYOVD and sandbox/container); provides research-oriented reading paths.
- `README.md:110-115` — Book and related awesome-list pointers; extends discovery but still no executable implementation.

## 6. Use-Case Mapping

The assigned use case (`RAG + Agents`) does **not** match the actual repository contents. There is no retrieval pipeline, embedding/vector DB workflow, prompt orchestration, or multi-agent runtime behavior. This repo is best classified as **None** from the allowed categories, because it is a curated reference list rather than an agentic application or automation system.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Broad, well-structured curation across PoCs, tools, talks, and blogs in one place.
- Explicit ethical-use framing that clarifies intended audience and boundaries.
- Includes both offensive and defensive perspectives (e.g., “Silencing the EDR Silencers”).
- Provides topical sub-grouping (BYOVD, Sandbox/Container, macOS) that aids targeted research.

- **Limitations:**
- No executable source code, so no reproducible pipeline to run or evaluate directly.
- No versioned metadata/schema for entries (dates, tags, quality scores, maintenance status).
- No automation for validation of dead links or stale resources.
- No agentic/LLM components despite upstream labeling as RAG/Agents.

- **Research relevance:**
- Useful as a qualitative corpus seed list for cybersecurity literature/repo discovery.
- Can support dataset construction for studying EDR bypass techniques and trends.
- Not suitable as evidence of multi-agent architecture or LLM orchestration design.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
