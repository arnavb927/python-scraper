---
repo_name: llmsresearch/paperbanana
url: "https://github.com/llmsresearch/paperbanana"
stars: 1348
forks: 208
contributors_count: 28
last_commit_date: "2026-04-22T18:28:59+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T12:51:29.784033+00:00"
model: auto
duration_s: 90.4
clone_size_kb: 52769
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`paperbanana` is an agentic Python system for generating academic visuals (methodology diagrams and statistical plots) from paper text, captions, and optional data files. A user typically runs `paperbanana` CLI commands (single-run, batch, or full-paper orchestration) or the MCP server tools, and gets output images plus metadata, prompts, and packaging artifacts like `figures.tex` and `captions.md` (`paperbanana/core/workflow_runner.py:64-87`, `paperbanana/core/orchestrate.py:737-792`, `mcp_server/server.py:420-490`). The core value is automating a multi-step visual-production workflow: retrieve examples, plan/stylize instructions, generate image/code, critique/refine iteratively, then export final assets (`paperbanana/core/pipeline.py:148-154`, `paperbanana/core/pipeline.py:644-1017`). It also supports paper-level orchestration that plans many figure tasks and runs them concurrently with retries and checkpoints (`paperbanana/core/orchestrate.py:576-691`).

## 2. Agent Framework & Architecture

This repo uses a **custom multi-agent architecture**, not LangGraph/LangChain/CrewAI/AutoGen. There are no imports of those frameworks, and agent classes are implemented directly as subclasses of a local `BaseAgent` (`paperbanana/agents/base.py:16-42`), with orchestration in `PaperBananaPipeline` (`paperbanana/core/pipeline.py:148-253`).

The architecture is role-based with specialized agents: `InputOptimizer`, `Retriever`, `Planner`, `Stylist`, `Visualizer`, `Critic`, plus optional `Caption`, `Structurer`, and `IRPlanner` (`paperbanana/core/pipeline.py:218-253`). “Intelligence” lives mainly in prompt templates loaded per agent/diagram type (`paperbanana/agents/base.py:44-57`) and in pipeline control logic (phase sequencing, retries, early stop, budget checks, and iterative critique loop) (`paperbanana/core/pipeline.py:82-103`, `paperbanana/core/pipeline.py:570-1170`).

Providers are pluggable and abstracted behind local interfaces (`paperbanana/providers/base.py:14-45`, `paperbanana/providers/base.py:70-106`), then created by a registry for OpenAI/Gemini/OpenRouter/Anthropic/Bedrock/Ollama/Claude Code and image backends (`paperbanana/providers/registry.py:82-164`, `paperbanana/providers/registry.py:167-213`).

## 3. Orchestration Pattern

Closest pattern: **hierarchical sequential pipeline with an iterative refinement sub-loop** (manager-worker style). `PaperBananaPipeline` is the manager, invoking specialist agents in order, then looping `Visualizer <-> Critic` until convergence or iteration/budget limit (`paperbanana/core/pipeline.py:151-154`, `paperbanana/core/pipeline.py:644-1017`).

Control-flow excerpt 1 (linear phases):
```python
# from paperbanana/core/pipeline.py
examples = await _call_with_retry("retriever", self.retriever.run, ...)
description, planner_ratio = await _call_with_retry("planner", self.planner.run, ...)
optimized_description = await _call_with_retry("stylist", self.stylist.run, ...)
```
(`paperbanana/core/pipeline.py:692-785`)

Control-flow excerpt 2 (iterative refinement loop):
```python
# from paperbanana/core/pipeline.py
image_path = await _call_with_retry("visualizer", self.visualizer.run, ...)
critique = await _call_with_retry("critic", self.critic.run, ...)
if critique.needs_revision and critique.revised_description:
    current_description = critique.revised_description
else:
    break
```
(`paperbanana/core/pipeline.py:877-1005`)

At paper-package level, orchestration is also manager-worker: task planner + concurrent task workers with semaphore/retry/checkpointing (`paperbanana/core/orchestrate.py:607-684`).

## 4. Tools & External Integrations

- **LLM/VLM APIs (OpenAI, Gemini, OpenRouter, Anthropic, Bedrock, Ollama, Claude Code CLI):** wired in provider factory and provider implementations (`paperbanana/providers/registry.py:82-213`, `paperbanana/providers/vlm/claude_code.py:95-170`).
- **Image generation APIs (Google/OpenAI/OpenRouter/Bedrock Imagen):** selected through same registry (`paperbanana/providers/registry.py:167-213`).
- **External exemplar retrieval HTTP service:** optional adapter via `httpx` POST with retries; feeds Retriever candidate set (`paperbanana/reference/exemplar_retrieval.py:33-137`, `paperbanana/core/pipeline.py:482-519`).
- **Local Python subprocess execution for plot code generation:** Visualizer executes generated matplotlib code in a subprocess (`paperbanana/agents/visualizer.py:216-299`).
- **Graphviz `dot` binary for vector export:** IR-to-DOT + `subprocess.run(dot ...)` for SVG/PDF (`paperbanana/vector/graphviz_render.py:48-50`, `paperbanana/vector/graphviz_render.py:132-175`).
- **MCP integration via FastMCP:** exposes generation/evaluation/batch/orchestration tools to external MCP clients (`mcp_server/server.py:29-43`, `mcp_server/server.py:146-621`).
- **Gradio web app (“Studio”):** local browser UI wrapper around pipeline/workflow runners (`paperbanana/studio/app.py:45-95`, `paperbanana/studio/app.py:166-871`).

No browser automation stack (e.g., Playwright/Selenium) is present.

## 5. Notable Code Walkthrough

- `paperbanana/core/pipeline.py:148-253,644-1170` - Central runtime: initializes all agents/providers, runs phase-based orchestration, performs iterative visualizer-critic refinement, handles retries/budget/progress, and assembles final outputs/metadata.
- `paperbanana/agents/visualizer.py:139-195,216-299` - Key generation backend for plots: prompts VLM for matplotlib code, executes code in subprocess, handles failures and vector side-exports.
- `paperbanana/agents/planner.py:42-103,220-264` - Planning agent that uses retrieved examples (including optional images) to produce the generation description and recommended aspect ratio.
- `paperbanana/core/orchestrate.py:264-345,576-735` - Paper-level planner/executor: builds multi-figure plans, checkpoints task state, and runs concurrent figure jobs with retries.
- `mcp_server/server.py:146-281,420-552` - MCP tool surface that operationalizes the same engine for external agent environments (diagram/plot generation, orchestration, and batch commands).

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is mostly inaccurate for the core agent behavior. This codebase is primarily an **automated visual-content workflow system**: ingest context/data, run multi-agent generation/refinement, and package outputs (`paperbanana/core/pipeline.py:644-1017`, `paperbanana/core/workflow_runner.py:521-687`). It does expose terminal-facing CLI commands and a browser-based Gradio UI, but agents are not doing browser navigation or terminal-operation tasks themselves. Better category: **Workflow Automation** (with a secondary RAG-like retrieval component via exemplar retrieval/reference store).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear role-specialized multi-agent decomposition with explicit phase boundaries (`paperbanana/core/pipeline.py:151-154`, `218-253`).
  - Robust orchestration features: retries, checkpointing, resumability, and concurrency at batch/package level (`paperbanana/core/orchestrate.py:389-443`, `607-691`; `paperbanana/core/workflow_runner.py:186-257`).
  - Provider abstraction cleanly separates orchestration from model backends (`paperbanana/providers/base.py:14-45`, `paperbanana/providers/registry.py:78-213`).
  - Supports both single-run and scalable workflows (batch/orchestrate/MCP/Studio), useful for production-like pipelines.
  - Captures rich artifacts (prompts, metadata, timing, costs), good for reproducibility/analysis (`paperbanana/core/pipeline.py:1108-1152`).

- **Limitations:**
  - Orchestration is hardcoded procedural flow, not a declarative graph/policy engine; extensibility requires code edits (`paperbanana/core/pipeline.py:644-1017`).
  - Plot path executes LLM-generated Python code in subprocess with limited sandboxing (timeout only), which is a security/runtime risk (`paperbanana/agents/visualizer.py:216-299`).
  - Heavy dependence on prompt quality and provider behavior; limited formal guarantees on output faithfulness.
  - External retrieval adapter is optional and HTTP-contract based; no built-in vector DB pipeline in core repo (`paperbanana/reference/exemplar_retrieval.py:33-154`).
  - Multi-agent coordination is centralized; no peer-to-peer negotiation/swarm behaviors.

- **Research relevance:**
  - Strong example of **role-based cooperative MAS** in applied content generation workflows.
  - Demonstrates iterative self-critique/refinement loops with explicit stopping logic and budget awareness.
  - Useful evidence for studying provider-agnostic agent architectures and orchestration robustness in real tools.
  - Illustrates how MCP interfaces can expose multi-agent pipelines as composable tool endpoints.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
