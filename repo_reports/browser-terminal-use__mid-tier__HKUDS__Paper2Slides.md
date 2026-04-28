---
repo_name: HKUDS/Paper2Slides
url: "https://github.com/HKUDS/Paper2Slides"
stars: 3446
forks: 449
contributors_count: 5
last_commit_date: "2026-03-15T11:29:22+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 5
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T13:44:10.173213+00:00"
model: auto
duration_s: 83.0
clone_size_kb: 39611
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`Paper2Slides` is a document-to-presentation generation system that takes one or more input files (typically PDFs) and produces either slide images plus a PDF (`slides.pdf`) or a poster image, via CLI (`python -m paper2slides ...`) or a FastAPI backend. The runtime pipeline first parses/indexes documents (or directly queries markdown in fast mode), extracts structured paper content, plans presentation sections, then generates final visuals with an image model. In practice, users run a single command or API call and receive ready-to-use visual outputs under `outputs/...` with checkpointed intermediate artifacts. The main problem it solves is automating the end-to-end transformation from technical documents to presentation materials with minimal manual layout/design work.

## 2. Agent Framework & Architecture

This repo uses a **custom orchestration architecture**, not LangGraph/LangChain/AutoGen/CrewAI. Core evidence: orchestration is implemented in in-house stage functions (`paper2slides/core/pipeline.py:16-81`) and direct SDK/API calls to OpenAI-compatible endpoints (`paper2slides/generator/content_planner.py:111-133`, `paper2slides/core/stages/summary_stage.py:17-33`, `paper2slides/rag/client.py:14-16`).

High-level architecture is a 4-stage sequential pipeline: `rag -> summary -> plan -> generate` (`paper2slides/core/state.py:15`, `paper2slides/core/pipeline.py:64-71`). “Intelligence” is concentrated in prompt templates and role-specific transforms rather than interacting autonomous agents:  
- RAG query templates (`paper2slides/rag/query.py:16-85`)  
- structured extraction prompts (`paper2slides/prompts/paper_extraction.py:7-120`)  
- planning prompts for slides/posters (`paper2slides/prompts/content_planning.py:7-140`)  
- image generation prompt construction (`paper2slides/generator/image_generator.py:292-331`).

There are multiple LLM-powered components (RAG Q&A, summarizer/extractor, planner, style processor, image generator), but they are pipeline modules, not independent agents negotiating or routing among themselves.

## 3. Orchestration Pattern

Closest match: **sequential workflow pipeline (other: staged DAG-like linear pipeline)**.

Control flow is explicitly stage-ordered:

```python
# paper2slides/core/pipeline.py:64-71
if stage == "rag":
    await run_rag_stage(base_dir, config)
elif stage == "summary":
    await run_summary_stage(base_dir, config)
elif stage == "plan":
    await run_plan_stage(base_dir, config_dir, config)
elif stage == "generate":
    await run_generate_stage(base_dir, config_dir, config)
```

Stage transitions are checkpoint-driven, not planner-agent-driven:

```python
# paper2slides/core/state.py:46-57
if not get_rag_checkpoint(base_dir, config).exists():
    return "rag"
if not get_summary_checkpoint(base_dir, config).exists():
    return "summary"
if not get_plan_checkpoint(config_dir).exists():
    return "plan"
return "generate"
```

There is concurrency inside stages (parallel queries/extractions/slide rendering), but no manager-worker LLM agent hierarchy or graph-state routing.

## 4. Tools & External Integrations

- **OpenAI-compatible chat/completions APIs** for extraction/planning and fast-mode querying (`paper2slides/core/stages/summary_stage.py:17-33`, `paper2slides/core/stages/rag_stage.py:322-336`, `paper2slides/generator/content_planner.py:294-303`).
- **OpenRouter image generation endpoint** via OpenAI client with multimodal payload (`paper2slides/generator/image_generator.py:106-112`, `410-481`).
- **Google Gemini REST API** for image generation (`paper2slides/generator/image_generator.py:483-585`).
- **LightRAG + RAGAnything integration** for document parsing/indexing/retrieval (`paper2slides/rag/client.py:14-16`, `132-145`; `paper2slides/rag/config.py:206-235`).
- **FastAPI web service** exposing upload, run, status, and result retrieval endpoints (`api/server.py:145-287`, `550-720`).
- **Local filesystem checkpoints/artifacts** for resumable workflow (`paper2slides/core/state.py:23-40`, `paper2slides/core/stages/*` save/load checkpoints).
- **No browser automation / terminal-control tools** (no Playwright/Browserbase/shell-agent loops observed).

## 5. Notable Code Walkthrough

- `paper2slides/core/pipeline.py:16-89` - Central orchestrator that executes the 4 stages in order, updates stage state, handles cancellation/error, and supports resume behavior.
- `paper2slides/core/stages/rag_stage.py:256-415` - Implements two ingestion/query modes: fast direct multimodal querying over parsed markdown+images, and normal indexing/querying through `RAGClient`.
- `paper2slides/summary/paper.py:178-235` - Converts raw RAG outputs into structured paper sections; uses per-section extraction prompts and optional parallel LLM extraction.
- `paper2slides/generator/content_planner.py:134-227` - Produces a `ContentPlan` (sections, table/figure refs, metadata) by calling a multimodal LLM with summary + source assets.
- `paper2slides/generator/image_generator.py:113-263` - Renders poster/slides from the plan; includes style processing, prompt assembly, provider routing, and parallel generation for later slides.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** looks inaccurate based on the code. This repo does not implement browser interaction agents or terminal-operation agents; instead it automates a multi-step content-processing workflow from documents to visual outputs via LLM/RAG/image APIs. The better fit is **Workflow Automation**, with a secondary flavor of **RAG + Agents-like components** (but not true multi-agent runtime). So the final category should be **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, reproducible staged pipeline with persistent checkpoints and resume (`paper2slides/core/state.py`, `core/pipeline.py`).
  - Practical multimodal handling: markdown + inline base64 figures in fast-mode query path (`core/stages/rag_stage.py:45-117`, `139-205`).
  - Strong prompt modularization for extraction/planning tasks (`prompts/paper_extraction.py`, `prompts/content_planning.py`).
  - Flexible deployment surfaces (CLI + FastAPI) over same core pipeline (`paper2slides/main.py`, `api/server.py`).
  - Supports multi-file sessions and parallel generation for throughput (`api/server.py:345-408`, `generator/image_generator.py:220-261`).

- **Limitations:**
  - Not a true multi-agent system: no autonomous agent roles coordinating at runtime; mostly sequential modules.
  - Heavy reliance on prompt formatting + regex JSON extraction can be brittle (`content_planner.py:328-339`).
  - Limited failure recovery granularity inside individual LLM calls beyond retries in image generation.
  - Fast mode only supports `content_type='paper'` (`core/stages/rag_stage.py:337`), reducing generality.
  - Potential cost/latency due to many LLM calls across RAG, extraction, planning, and rendering stages.

- **Research relevance:**
  - Good case study for **LLM-orchestrated workflow pipelines** with checkpointed stage execution.
  - Useful evidence for **multimodal document-to-presentation automation** (RAG + extraction + generation stack).
  - Illustrates engineering tradeoffs between **fast direct context mode** and **indexed RAG mode** in one system.
  - Less suitable as evidence for emergent coordination in true multi-agent architectures.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
