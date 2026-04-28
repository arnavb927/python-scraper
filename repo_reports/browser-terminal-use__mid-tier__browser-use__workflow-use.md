---
repo_name: browser-use/workflow-use
url: "https://github.com/browser-use/workflow-use"
stars: 3960
forks: 315
contributors_count: 10
last_commit_date: "2026-01-31T00:58:16+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T13:36:35.647216+00:00"
model: auto
duration_s: 71.4
clone_size_kb: 5687
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`workflow-use` is a Python toolkit/CLI for creating and running browser automation workflows from recorded interactions or natural-language tasks. A user can run commands like `create-workflow`, `generate-workflow`, `run-workflow`, and `run-workflow-no-ai` to produce a `.workflow.yaml/.json` definition and execute it against a live browser (`workflows/cli.py:870-1182`, `workflows/cli.py:2303-2350`). The core runtime executes ordered workflow steps (navigation, click/input/select, extraction, optional agent task) and stores outputs into context for downstream steps (`workflows/workflow_use/workflow/service.py:851-946`). It targets robust RPA-style browser automation with semantic element targeting (`target_text`) and optional AI extraction/agent fallback paths (`workflows/workflow_use/schema/views.py:45-57`, `workflows/workflow_use/workflow/semantic_executor.py:31-57`).

## 2. Agent Framework & Architecture

The repo is **not CrewAI/LangGraph**. It is built on the `browser-use` framework (`from browser_use import Agent, Browser, Controller`) plus its chat model abstraction (`browser_use.llm.base.BaseChatModel`) (`workflows/workflow_use/workflow/service.py:11-15`, `workflows/workflow_use/healing/service.py:8-12`, `workflows/workflow_use/controller/service.py:4-7`). It also exposes workflows through `FastMCP` for MCP tool use (`workflows/workflow_use/mcp/service.py:7`, `workflows/workflow_use/mcp/service.py:13-23`).

Architecture is centered on a `Workflow` orchestrator class that runs a typed list of steps from `WorkflowDefinitionSchema` (`workflows/workflow_use/workflow/service.py:39-55`, `workflows/workflow_use/schema/views.py:216-238`). Most steps are deterministic controller actions (`navigation`, `click`, `input`, etc.), while `type: "agent"` steps instantiate a `browser_use.Agent` with a custom controller that can terminate the step (`workflows/workflow_use/workflow/service.py:329-353`, `workflows/workflow_use/workflow/step_agent/controller.py:9-16`). LLM “intelligence” lives in prompt templates and direct `ainvoke` calls for structured output/input parsing and extraction (`workflows/workflow_use/workflow/service.py:763-769`, `workflows/workflow_use/workflow/service.py:1028-1037`, `workflows/workflow_use/builder/service.py:170-231`).

There is a generation pipeline (`HealingService.generate_workflow_from_prompt`) that first runs one exploration agent in browser, then converts the history to workflow schema via LLM or deterministic conversion, with optional AI validation (`workflows/workflow_use/healing/service.py:420-429`, `workflows/workflow_use/healing/service.py:806-817`, `workflows/workflow_use/healing/service.py:844-853`, `workflows/workflow_use/healing/service.py:855-877`).

## 3. Orchestration Pattern

Closest match: **sequential pipeline with optional single-agent steps** (not graph/swarm/hierarchical multi-agent).

Execution flow is a simple ordered loop over steps with type-based branching:

```891:921:workflows/workflow_use/workflow/service.py
for step_index, step_dict in enumerate(self.schema.steps):
    ...
    step_resolved = self._resolve_placeholders(step_dict)
    result = await self._execute_step(step_index, step_resolved)
```

Type dispatch sends deterministic steps to controller/semantic execution, and `agent` steps to a single `Agent` instance:

```635:704:workflows/workflow_use/workflow/service.py
if isinstance(step_resolved, DeterministicWorkflowStep):
    ...
elif isinstance(step_resolved, AgenticWorkflowStep):
    result = await self._run_agent_step(step_resolved, step_index)
```

So control is centrally orchestrated by `Workflow.run()`, with no peer-to-peer agent negotiation or LangGraph-style state graph.

## 4. Tools & External Integrations

- **Browser automation (core):** `browser_use.Browser`, page operations, selector maps, CDP-style element operations (`workflows/workflow_use/workflow/service.py:76-79`, `workflows/workflow_use/controller/service.py:63-244`, `workflows/workflow_use/healing/service.py:451-483`).
- **LLM backends via browser-use:** `BaseChatModel`, `ChatBrowserUse`, `ainvoke`, structured output parsing (`workflows/cli.py:13-15`, `workflows/cli.py:37-39`, `workflows/workflow_use/workflow/service.py:1028-1037`).
- **Agent runtime:** `browser_use.Agent` for step-level agent tasks and workflow generation exploration (`workflows/workflow_use/workflow/service.py:342-352`, `workflows/workflow_use/healing/service.py:806-817`).
- **Custom action tools/controllers:** `WorkflowController` registers deterministic actions (navigate/click/input/select/key/scroll/extract) (`workflows/workflow_use/controller/service.py:55-244`).
- **MCP server integration:** scans workflow files and registers each as MCP tools using `FastMCP` (`workflows/workflow_use/mcp/service.py:20-37`, `workflows/workflow_use/mcp/service.py:103-109`, `workflows/cli.py:2133-2157`).
- **Storage & batch execution:** local workflow metadata storage and CSV-driven batch runs (`workflows/cli.py:21`, `workflows/cli.py:1743-2130`).
- **No vector DB / RAG index backend found:** dependencies and code show no Chroma/Pinecone/pgvector pipeline; extraction is page-content prompt-based (`workflows/pyproject.toml:14-25`, `workflows/workflow_use/workflow/service.py:382-403`).

## 5. Notable Code Walkthrough

- `workflows/workflow_use/workflow/service.py:39-946` - Primary runtime orchestrator: validates inputs, resolves placeholders, dispatches deterministic vs agentic steps, persists step outputs, and returns run results.
- `workflows/workflow_use/controller/service.py:55-244` - Defines the deterministic action surface exposed to workflows; this is the concrete browser action tool layer used by execution.
- `workflows/workflow_use/healing/service.py:420-895` - “Generation mode” pipeline: runs exploration agent, captures interactions, converts history to workflow definition, and optionally validates/corrects.
- `workflows/workflow_use/schema/views.py:63-182` - Canonical step taxonomy (`agent` plus deterministic step union) that determines what the runtime can execute.
- `workflows/workflow_use/mcp/service.py:13-109` - MCP exposure layer turning saved workflows into callable tools with dynamic signatures.

## 6. Use-Case Mapping

This repo strongly implements **Workflow Automation** over web UIs: users generate or record reusable workflows, parameterize inputs, and run them repeatedly (including CSV bulk runs) (`workflows/cli.py:1743-2130`, `workflows/workflow_use/workflow/service.py:851-946`). It does use browser interaction heavily, but the product intent is end-to-end automation workflows rather than a generic browser-use agent playground. So the assigned “Browser / Terminal Use” is partially true at mechanism level (browser control), but the better top-level category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong typed workflow schema with explicit step union and validation constraints (`workflows/workflow_use/schema/views.py:160-258`).
  - Hybrid execution design: deterministic actions first, optional agentic steps where needed (`workflows/workflow_use/workflow/service.py:630-720`).
  - Practical reliability features: selector strategy fallback, semantic mapping, wait handling, debug screenshots (`workflows/workflow_use/workflow/service.py:167-283`, `workflows/workflow_use/workflow/service.py:810-849`).
  - End-to-end lifecycle support (record/build/generate/run/store/MCP expose) from one CLI (`workflows/cli.py:870-2662`).

- **Limitations:**
  - Not a true multi-agent coordination system; mostly single orchestrator + occasional single-agent invocation.
  - Some fallback/agent-retry logic is commented out or incomplete, reducing resilience (`workflows/workflow_use/workflow/service.py:421-494`, `workflows/workflow_use/workflow/service.py:691-696`).
  - Very large monolithic modules (notably `cli.py`, `semantic_executor.py`) increase maintenance complexity (`workflows/cli.py`, `workflows/workflow_use/workflow/semantic_executor.py`).
  - Hard requirement that workflow ends with extract-like step may constrain broader automation patterns (`workflows/workflow_use/schema/views.py:240-256`).

- **Research relevance:**
  - Good case study for **LLM-assisted workflow synthesis** from browser interaction histories (`workflows/workflow_use/healing/service.py:171-295`, `workflows/workflow_use/healing/service.py:420-853`).
  - Demonstrates **hybrid deterministic-agentic orchestration** in production-style automation tooling.
  - Useful example of **agent output distillation** into reusable declarative workflow artifacts.
  - Illustrates how MCP can operationalize generated workflows as tool endpoints (`workflows/workflow_use/mcp/service.py:26-109`).

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
