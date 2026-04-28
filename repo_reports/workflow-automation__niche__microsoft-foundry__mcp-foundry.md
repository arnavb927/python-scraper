---
repo_name: microsoft-foundry/mcp-foundry
url: "https://github.com/microsoft-foundry/mcp-foundry"
stars: 240
forks: 111
contributors_count: 17
last_commit_date: "2025-11-19T00:02:05+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T16:37:08.261263+00:00"
model: auto
duration_s: 67.9
clone_size_kb: 1282
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`mcp-foundry` is an MCP (Model Context Protocol) server that exposes Azure AI Foundry operations as callable tools for an LLM client (for example, Copilot Agent mode or a PydanticAI client). A user runs the server entrypoint (`run-azure-ai-foundry-mcp` / `mcp_foundry.__main__`) and then asks natural-language requests; the client LLM selects and invokes MCP tools for model catalog lookup, deployment actions, search-index management, fine-tuning APIs, and evaluation workflows. The server’s job is to translate tool invocations into Azure SDK, REST, and CLI calls, then return structured results. So the concrete output is a tool-enabled assistant workflow over Azure resources, not a standalone chatbot inside this repo.

## 2. Agent Framework & Architecture

The repo does **not** implement LangGraph/LangChain/AutoGen/CrewAI-style in-process agent graphs. It is built around the Python MCP SDK (`mcp.server.fastmcp.FastMCP`) and registers many tool functions via decorators (`@mcp.tool`) in capability modules such as model, knowledge, finetuning, and evaluation (`src/mcp_foundry/mcp_server.py:5-7`, `src/mcp_foundry/mcp_foundry_model/tools.py:33-34`, `src/mcp_foundry/mcp_foundry_knowledge/tools.py:18-19`, `src/mcp_foundry/mcp_foundry_evaluation/tools.py:406-407`).

Architecture is plugin-like: startup calls `auto_import_modules("mcp_foundry", targets=["tools","resources","prompts"])`, which dynamically imports subpackage modules so tool/resource decorators execute and register endpoints (`src/mcp_foundry/__main__.py:41-43`, `src/mcp_foundry/mcp_server.py:11-33`). The “intelligence” (planning/tool choice) is expected to live in the **external MCP client LLM**, not in server-side planners/routers.

There is agent-related functionality, but it is adapter-style: evaluation tools can query Azure AI Agent Service (`AIProjectClient`) and run evaluators on those runs (`src/mcp_foundry/mcp_foundry_evaluation/tools.py:287-357`, `620-748`, `900-985`). That means the repo can operate on agents, but it does not orchestrate multiple internal agents itself.

## 3. Orchestration Pattern

Closest match: **event-driven tool server (other)**, not multi-agent orchestration.

Control flow is request/response per tool call: MCP client invokes a named tool, function executes, returns data. Server composition is via module auto-import rather than runtime agent graph.

```27:33:src/mcp_foundry/mcp_server.py
            try:
                importlib.import_module(module_name)
                logger.info(f"✅ Imported: {module_name}")
            except ModuleNotFoundError:
                logger.warning(f"⚠️ Skipping {module_name} (not found)")
```

```41:43:src/mcp_foundry/__main__.py
    auto_import_modules("mcp_foundry", targets=["tools", "resources", "prompts"])
    mcp.run(transport=specified_transport)
```

Inside specific tools there can be short sequential workflows (e.g., query Azure agent, then evaluate), but still as a single tool pipeline rather than coordinating multiple peer agents (`src/mcp_foundry/mcp_foundry_evaluation/tools.py:674-724`).

## 4. Tools & External Integrations

- **MCP runtime / protocol**: `FastMCP` server with decorated tools/resources (`src/mcp_foundry/mcp_server.py:5-7`, `src/mcp_foundry/mcp_foundry_knowledge/resources.py:3-7`).
- **Azure AI Foundry model & deployment management**: Azure Cognitive Services SDK (`azure.mgmt.cognitiveservices`) plus custom deployment helpers (`src/mcp_foundry/mcp_foundry_model/tools.py:9-15`, `253-314`, `401-471`).
- **Azure AI Search**: index/indexer/document/query operations through Azure Search SDK DAOs (`src/mcp_foundry/mcp_foundry_knowledge/tools.py:60-373`, `src/mcp_foundry/mcp_foundry_knowledge/data_access_objects/dao.py:89-537`).
- **Azure OpenAI fine-tuning REST APIs**: direct `requests` calls to `/openai/fine_tuning/jobs` and related endpoints (`src/mcp_foundry/mcp_foundry_finetuning/tools.py:145-173`, `175-309`).
- **Swagger-driven dynamic API tooling**: auto-registers operations from swagger and executes by tool name (`src/mcp_foundry/mcp_foundry_finetuning/tools.py:12`, `25-27`, `33-89`, `91-143`).
- **Azure AI Evaluation + Agent Service**: evaluators (`azure.ai.evaluation`) and Azure AI Agents (`azure.ai.projects`) for querying/evaluating remote agents (`src/mcp_foundry/mcp_foundry_evaluation/tools.py:13-43`, `143-173`, `287-357`, `900-985`).
- **Azure CLI subprocess integration**: helper executes `python -m azure.cli ... -o json` (`src/mcp_foundry/mcp_foundry_evaluation/tools.py:360-398`).
- **Generic HTTP/file fetch helpers**: local file read and URL fetch tools exposed to MCP clients (`src/mcp_foundry/mcp_foundry_knowledge/tools.py:18-58`).

## 5. Notable Code Walkthrough

- `src/mcp_foundry/__main__.py:15-43` - CLI entrypoint parses transport/env args, loads `.env`, auto-imports capability modules, and starts the MCP server; this is the runtime bootstrap.
- `src/mcp_foundry/mcp_server.py:11-33` - dynamic module loader that discovers subpackages and imports `tools/resources/prompts`, enabling a modular “capabilities by folder” pattern.
- `src/mcp_foundry/mcp_foundry_model/tools.py:33-519` - core Foundry model/deployment/project tools; shows how MCP endpoints map to Azure SDK calls and REST requests for real cloud actions.
- `src/mcp_foundry/mcp_foundry_knowledge/tools.py:60-373` - Azure AI Search operations (index lifecycle, documents, querying, indexers/data sources/skillsets), a strong workflow-automation surface.
- `src/mcp_foundry/mcp_foundry_evaluation/tools.py:620-748` - most agent-like pipeline: query remote Azure AI agent run, convert run data, then evaluate with selected evaluators; still a single tool function, not MAS coordination.

## 6. Use-Case Mapping

The assigned use case **Workflow Automation** is accurate. This repo automates cloud operational workflows by exposing many Azure operations as natural-language-invocable MCP tools: model discovery/deployment, search index management, fine-tune monitoring, and evaluation runs (`README.md:24-92`, `src/mcp_foundry/mcp_foundry_model/tools.py:237-519`, `src/mcp_foundry/mcp_foundry_knowledge/tools.py:60-373`). The LLM-driven client acts as the orchestrator that picks tool sequences, while this repo provides the executable workflow primitives.

However, it is **not** a multi-agent runtime in itself: there is no planner/worker team or agent graph executing inside the server code.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad Azure operation coverage exposed through a single MCP interface (models, knowledge/search, finetuning, evaluation).
  - Clear modular registration pattern (`tools/resources/prompts`) makes capabilities easy to extend.
  - Practical integration depth with official Azure SDKs and service APIs, including agent evaluation tooling.
  - Includes client example (`pydantic-ai`) showing real MCP consumption flow (`clients/python/pydantic-ai/main.py:28-37`).
  - Supports both static and dynamic (Swagger-derived) tool surfaces for finetuning APIs.

- **Limitations:**
  - No true in-repo multi-agent coordination; orchestration intelligence is delegated to external LLM clients.
  - Some flows rely on environment-heavy configuration and ad hoc HTTP calls, increasing fragility.
  - Several tool docstrings include prompt-like behavioral instructions but no enforced policy layer.
  - Deprecated status noted in README; repository is marked outdated versus cloud-hosted successor (`README.md:11-21`).
  - Limited explicit testing evidence for complex agent/evaluation workflows compared to breadth of exposed operations.

- **Research relevance:**
  - Good evidence for **MCP-as-tooling-layer** architecture in agentic systems (tool server separated from planner LLM).
  - Illustrates how enterprise cloud workflows are operationalized as callable tool endpoints for agent clients.
  - Useful for studying evaluation instrumentation around external agent runs (query + convert + evaluate pipeline).
  - Less suitable as evidence of emergent multi-agent coordination algorithms, since those are not implemented here.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
