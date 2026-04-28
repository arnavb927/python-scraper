---
repo_name: langgenius/dify
url: "https://github.com/langgenius/dify"
stars: 138815
forks: 21757
contributors_count: 1276
last_commit_date: "2026-04-23T03:03:20+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T10:03:24.336338+00:00"
model: auto
duration_s: 136.3
clone_size_kb: 130438
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`langgenius/dify` is a production platform for building and running LLM apps as configurable pipelines: chat assistants, agent chat, and workflow apps with triggers, tools, and memory. In practice, users run the Dify backend/frontend, configure an app in the UI, and the runtime executes a graph of nodes (LLM, tool, agent, HTTP, trigger, etc.) against incoming requests. The code shows two major execution modes: an app-level agent chat runner and a workflow graph engine that can embed agent nodes. The result is not just a chatbot SDK; it is an orchestration system for automating multi-step AI workflows with operational features (quotas, observability, plugin integrations, MCP, and tool providers).

## 2. Agent Framework & Architecture

The repository does **not** directly import LangChain, LangGraph, CrewAI, AutoGen, or LlamaIndex in core runtime paths; agent orchestration is custom (`api/core/agent/*`, `api/core/workflow/*`) on top of Dify’s internal `graphon` runtime (`api/core/workflow/workflow_entry.py:33-41`, `:180-223`).

At the app level, agent execution is implemented by custom runners selected at runtime: chain-of-thought (`CotChatAgentRunner` / `CotCompletionAgentRunner`) or function-calling (`FunctionCallAgentRunner`) in `api/core/app/apps/agent_chat/app_runner.py:197-231`. The “intelligence” is in prompt assembly, iterative reasoning/tool loops, and tool schemas built from runtime tool providers (`api/core/agent/base_agent_runner.py:223-250`).

At the workflow level, an `AgentNode` is one node type in a broader graph engine. Node construction is centralized in `DifyNodeFactory`, which wires agent strategy resolver/presentation/runtime/message transformation (`api/core/workflow/node_factory.py:435-440`). Agent strategies can be plugin-provided (`api/core/workflow/nodes/agent/plugin_strategy_adapter.py:8-20`, `api/core/plugin/impl/agent.py:78-117`), so runtime behavior can be extended beyond built-ins.

## 3. Orchestration Pattern

Closest match: **graph + hierarchical manager-worker hybrid**.

- **Graph orchestration**: workflow execution is driven by `GraphEngine` over node graph configs, including child engines and layers (`api/core/workflow/workflow_entry.py:180-223`, `:69-112`).
- **Manager-worker loop inside agent nodes/runners**: one manager loop repeatedly calls LLM, parses action/tool calls, invokes tools, appends observations, and iterates until final answer (`api/core/agent/cot_agent_runner.py:103-252`; `api/core/agent/fc_agent_runner.py:77-307`).

Control flow excerpt 1 (graph engine bootstrap):
- `WorkflowEntry` builds `GraphEngine(...)`, attaches limits/quota/observability layers, then `yield from graph_engine.run()` (`api/core/workflow/workflow_entry.py:180-223`).

Control flow excerpt 2 (agent loop):
- `while function_call_state and iteration_step <= max_iteration_steps:`
- invoke model
- detect tool/action
- `ToolEngine.agent_invoke(...)`
- append tool response into thought/history
- iterate (`api/core/agent/fc_agent_runner.py:77-99`, `:227-307`; similar in `cot_agent_runner.py:103-124`, `:220-252`).

## 4. Tools & External Integrations

- **Tool runtime abstraction (built-in/API/workflow/plugin/MCP)**: central dispatch in `ToolManager.get_tool_runtime(...)` with provider-type branching (`api/core/tools/tool_manager.py:182-390`).
- **Tool invocation engine**: normalized execution/callback/error/meta pipeline in `ToolEngine.agent_invoke` and `generic_invoke` (`api/core/tools/tool_engine.py:48-127`, `:158-199`).
- **MCP integration**:
  - MCP tools as provider type in tool manager (`api/core/tools/tool_manager.py:379-387`, `:845-863`).
  - Dify can also expose app-as-MCP-tool over JSON-RPC (`api/core/mcp/server/streamable_http.py:28-96`, `:117-160`).
- **Plugin agent strategies**: remote plugin daemon can provide/invoke agent strategies (`api/core/plugin/impl/agent.py:15-44`, `:78-117`).
- **RAG / dataset retrieval as agent tools**: dataset retrievers wrapped as tool instances (`api/core/tools/utils/dataset_retriever_tool.py:28-87`, `:111-128`).
- **HTTP / web access tools**: built-in web scraper tool fetches URLs (`api/core/tools/builtin_tool/providers/webscraper/tools/webscraper.py:10-37`).
- **Workflow triggers for automation**:
  - schedule trigger (`api/core/workflow/nodes/trigger_schedule/trigger_schedule_node.py:12-43`)
  - webhook trigger (`api/core/workflow/nodes/trigger_webhook/node.py:22-75`)
  - plugin event trigger (`api/core/workflow/nodes/trigger_plugin/trigger_event_node.py:13-66`)

No evidence of native browser automation frameworks like Playwright/Selenium in core agent runtime paths inspected.

## 5. Notable Code Walkthrough

- `api/core/app/apps/agent_chat/app_runner.py:179-231`  
  Chooses strategy (CoT vs function-calling) based on model features, instantiates the corresponding runner, and executes the agent chat pipeline; this is the top-level entry for app-mode agent behavior.

- `api/core/agent/fc_agent_runner.py:77-145` and `:227-307`  
  Implements iterative function-calling orchestration: invoke LLM with tools, collect tool calls, execute tools, feed tool outputs back, and continue until no tool call or max iterations.

- `api/core/agent/cot_agent_runner.py:103-179` and `:220-241`  
  Implements ReAct-like Thought/Action/Observation loops with parsing and tool execution, including explicit max-iteration guard and persisted “agent thoughts.”

- `api/core/workflow/workflow_entry.py:180-223`  
  Constructs and runs `GraphEngine` with execution limits, quota, and observability layers; this is the core workflow orchestration runtime.

- `api/core/workflow/node_factory.py:431-440`  
  Wires the `AGENT` node dependencies (strategy resolver, runtime support, message transformer), showing how agent capabilities are embedded into a general workflow graph.

## 6. Use-Case Mapping

The assigned label `Browser / Terminal Use` looks **partially mismatched**. The codebase does include a web-scraping tool (`webscraper`) and rich tool invocation, but the dominant architecture is a **workflow automation platform** with triggers (schedule/webhook/plugin), graph execution, and pluggable tool/provider orchestration (`workflow_entry.py`, trigger nodes, tool manager). There is no strong evidence in inspected core paths of terminal/shell-agent control loops as a primary product behavior. A better primary category is **Workflow Automation** (with secondary **RAG + Agents** due to dataset retrieval tooling).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong production orchestration substrate: graph execution with limits/quota/observability layers.
  - Flexible agent strategy model (CoT/function-calling + plugin-provided strategies).
  - Unified tool abstraction across built-in, API, workflow, plugin, and MCP providers.
  - Practical trigger model (schedule/webhook/plugin events) enabling real automation entrypoints.
  - Tight integration of memory, tool traces, and persisted thought records for app UX/ops.

- **Limitations:**
  - No direct in-repo use of prominent research frameworks (LangGraph/AutoGen/CrewAI), reducing comparability to those ecosystems.
  - Agent loops are mostly single-manager iterative patterns; explicit multi-role agent teams are limited.
  - Some capabilities depend on external plugin daemon and provider config, increasing deployment complexity.
  - Core graph runtime implementation (`graphon`) appears largely externalized, so end-to-end reasoning about scheduler internals is split across packages.
  - Built-in browser/terminal-action coverage in inspected code appears limited (web fetch/scrape rather than robust browser automation).

- **Research relevance:**
  - Evidence of industrialized agent orchestration embedded in a general workflow engine.
  - Useful example of hybrid architecture: graph workflow + iterative tool-using agent loops.
  - Demonstrates practical MCP/tool-provider integration in production LLM systems.
  - Illustrates event-triggered AI workflows (webhook/schedule/plugin) as real MAS-adjacent automation patterns.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
