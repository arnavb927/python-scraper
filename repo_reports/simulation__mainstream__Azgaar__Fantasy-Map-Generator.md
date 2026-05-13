---
repo_name: Azgaar/Fantasy-Map-Generator
url: "https://github.com/Azgaar/Fantasy-Map-Generator"
stars: 5600
forks: 888
contributors_count: 69
last_commit_date: "2026-04-22T14:52:22+00:00"
primary_use_case: Simulation
user_tier: Mainstream
total_score: 7
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, RAG + Agents, Simulation]
generated_at: "2026-05-05T08:10:42.854434+00:00"
model: auto
duration_s: 75.5
clone_size_kb: 46413
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`Azgaar/Fantasy-Map-Generator` is a browser-based procedural worldbuilding app that generates editable fantasy maps with terrain, climate, rivers, cultures, states, religions, routes, and labels. Users run it as a web app (locally via Vite or deployed static hosting with a server context), then click generate/regenerate to produce a full synthetic world from a seed and parameter set. The core output is an interactive SVG map plus structured world data (`pack`, `grid`) that can be edited and exported. This repository’s main problem is simulation-heavy content generation for cartography and narrative world design, not autonomous task execution. It does include a small optional AI text helper for note-writing, but that is peripheral to the map engine.

## 2. Agent Framework & Architecture

No multi-agent framework is used (no LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex imports in the runtime code or dependencies). The `package.json` dependencies are simulation/rendering-oriented (`d3`, `delaunator`, etc.) rather than agent frameworks (`package.json:26-47`).

The only LLM-related code is a UI utility that makes direct HTTP calls to provider APIs (`OpenAI`, `Anthropic`, local `Ollama`) from `public/modules/ui/ai-generator.js:3-108`. It sends a single system prompt + user prompt and streams text back into a text area (`public/modules/ui/ai-generator.js:45-61`, `64-86`, `197-223`). This is a single-call generation helper, not an autonomous planner/worker architecture.

Project intelligence for world generation is algorithmic and procedural: the main pipeline in `public/main.js` sequences deterministic/stochastic simulation modules (heightmap, precipitation, cultures, states, etc.) (`public/main.js:621-680`), with domain logic in TS modules such as `src/modules/heightmap-generator.ts`, `src/modules/cultures-generator.ts`, and `src/modules/states-generator.ts`.

## 3. Orchestration Pattern

Closest match: **sequential pipeline (custom simulation orchestration)**, not a multi-agent pattern.

Control flow is centrally orchestrated in `generate()` by invoking domain modules in a fixed order:

```621:636:public/main.js
async function generate(options) {
  ...
  if (shouldRegenerateGrid(grid, precreatedSeed)) grid = precreatedGraph || generateGrid();
  else delete grid.cells.h;
  grid.cells.h = await HeightmapGenerator.generate(grid);
  pack = {}; // reset pack
  Features.markupGrid();
```

Then downstream simulation passes continue in sequence:

```652:666:public/main.js
Rivers.generate();
Biomes.define();
Features.defineGroups();

Ice.generate();

rankCells();
Cultures.generate();
Cultures.expand();

Burgs.generate();
States.generate();
Routes.generate();
Religions.generate();
```

The LLM helper is also single-step routing by provider key (no agent-to-agent handoff): `PROVIDERS[provider].generate(...)` in `public/modules/ui/ai-generator.js:205-223`.

## 4. Tools & External Integrations

- **OpenAI Chat Completions API** — wired via `fetch("https://api.openai.com/v1/chat/completions")` with streaming in `public/modules/ui/ai-generator.js:50-54`.
- **Anthropic Messages API** — wired via `fetch("https://api.anthropic.com/v1/messages")` in `public/modules/ui/ai-generator.js:74-78`.
- **Ollama local HTTP API** — wired via `fetch("http://localhost:11434/api/generate")` in `public/modules/ui/ai-generator.js:91-101`.
- **Rich text editor CDN import (TinyMCE)** — dynamic import from project-hosted CDN URL in `public/modules/ui/notes-editor.js:68-76`; used for note editing, not LLM orchestration.
- **Service Worker / PWA** — registered in `public/main.js:16-22`.
- **No MCP/vector DB/RAG pipeline/terminal-agent/browser-agent loop** — no code evidence of retrieval systems, tool-calling agents, or multi-agent runtime coordination.

## 5. Notable Code Walkthrough

- `public/main.js:621-711` — Central map generation orchestrator; executes the full simulation pipeline, catches generation errors, and updates UI/state.
- `src/modules/heightmap-generator.ts:595-668` — Produces terrain heights from either procedural templates or precreated image heightmaps; foundational for all downstream simulation.
- `src/modules/cultures-generator.ts:1025-1403` — Generates culture centers/types, then expands cultures across cells using cost-based propagation with a priority queue.
- `src/modules/states-generator.ts:131-234` — Creates states from capitals and expands borders using weighted geography/culture costs; core political simulation stage.
- `public/modules/ui/ai-generator.js:3-231` — Optional single-shot AI text generator UI (OpenAI/Anthropic/Ollama) used to draft note descriptions, not to control simulation.
- `public/modules/ui/notes-editor.js:147-164` — Integration point where user notes invoke AI text generation (`generateWithAi(prompt, onApply)`).

## 6. Use-Case Mapping

The assigned primary use case **Simulation** is correct for the repository’s core behavior. The map creation flow computes terrain, climate, hydrology, biomes, population suitability, cultures, and political entities through chained procedural models (`public/main.js:635-680`, `src/modules/heightmap-generator.ts:610-630`, `src/modules/states-generator.ts:145-227`). The LLM feature is auxiliary (note text drafting) and does not drive world generation logic. If classified strictly for agentic-AI, this repo is MAS-adjacent at best (because of an optional single LLM call UI), but functionally it is a simulation engine.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong end-to-end procedural pipeline with explicit module boundaries and deterministic seed-based reproducibility (`public/main.js:621-711`).
  - Rich domain simulation depth (terrain, climate, sociopolitical layers) rather than superficial randomization.
  - Cost-based expansion algorithms for cultures/states provide interpretable generative behavior (`src/modules/cultures-generator.ts:1360-1400`, `src/modules/states-generator.ts:181-227`).
  - Optional multi-provider LLM text streaming support is practical and lightweight (`public/modules/ui/ai-generator.js:39-108`).

- **Limitations:**
  - No true LLM-agent abstraction (no planning, memory, role-based collaboration, tool-calling graph, or agent lifecycle manager).
  - AI integration is UI-bound and narrow (notes generation only), not connected to core simulation modules (`public/modules/ui/notes-editor.js:147-164`).
  - Browser-side direct key usage for external LLM APIs may raise key-handling/security concerns (`public/modules/ui/ai-generator.js:40-43`, `65-70`).
  - No automated evaluation harness for AI output quality/safety in generated notes.

- **Research relevance:**
  - Useful as evidence for **algorithmic simulation pipelines** in creative worldbuilding software.
  - Useful contrast case in MAS studies: a complex generative system with minimal LLM usage and no multi-agent orchestration.
  - Can be cited for hybrid human-in-the-loop workflows where deterministic simulation is primary and LLM is a secondary authoring assist.
  - Not suitable as evidence of runtime multi-agent coordination architectures.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
