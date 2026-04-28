---
repo_name: google/adk-python
url: "https://github.com/google/adk-python"
stars: 19196
forks: 3283
contributors_count: 273
last_commit_date: "2026-04-22T18:38:51+00:00"
primary_use_case: Workflow Automation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T10:47:10.041751+00:00"
model: auto
duration_s: 74.1
clone_size_kb: 39740
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`google/adk-python` is a Python SDK for building and running LLM agents as structured applications, not just prompt calls. A developer defines agent trees (e.g., `LlmAgent`, `SequentialAgent`, `ParallelAgent`, `LoopAgent`), wires tools, and runs them through a `Runner` that handles sessions, events, memory, artifacts, and plugins (`src/google/adk/runners.py:112-140`, `src/google/adk/agents/llm_agent.py:195-373`). Users typically run `adk run <agent_dir>` for interactive CLI usage, `adk web <agents_dir>` for a local UI, or `adk api_server <agents_dir>` for service mode (`src/google/adk/cli/cli_tools_click.py:605-675`, `1596-1754`). The runtime yields event streams (model outputs, tool calls/responses, agent-state transitions), enabling resumable and observable multi-agent workflows.

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework (ADK itself)**, not LangGraph/LangChain/CrewAI/AutoGen as the core runtime. Core orchestration imports are internal (`google.adk.*`) in `Runner`, `BaseAgent`, `LlmAgent`, and flow modules (`src/google/adk/runners.py:34-64`, `src/google/adk/agents/llm_agent.py:46-68`, `src/google/adk/flows/llm_flows/base_llm_flow.py:31-53`).  
There are optional adapters/integrations (e.g., LangChain/CrewAI wrappers), but those are tool adapters, not the execution backbone (`src/google/adk/integrations/langchain/langchain_tool.py:21-42`, `src/google/adk/tools/crewai_tool.py:19-30`).

Architecturally, the intelligence is split across:
- **LLM agent behavior** (`instruction`, model/tool config, callbacks, planner hooks) in `LlmAgent` (`src/google/adk/agents/llm_agent.py:215-464`).
- **Flow engine** that runs LLM-call/tool-call loops, handles function calls, and agent transfer in `BaseLlmFlow` + `AutoFlow` (`src/google/adk/flows/llm_flows/base_llm_flow.py:803-903`, `1111-1153`; `src/google/adk/flows/llm_flows/auto_flow.py:23-45`).
- **Runner-level orchestration** for sessions, persistence, resumability, plugin lifecycle, and active-agent selection (`src/google/adk/runners.py:502-633`, `1148-1200`).

It supports multi-agent hierarchies explicitly: `SequentialAgent`, `ParallelAgent`, and `LoopAgent` delegate to sub-agents with stateful resume semantics (`src/google/adk/agents/sequential_agent.py:48-93`, `src/google/adk/agents/parallel_agent.py:150-206`, `src/google/adk/agents/loop_agent.py:52-125`).

## 3. Orchestration Pattern

Closest match: **hierarchical + graph-like event/state orchestration (other/hybrid)**.

- Hierarchical because agents are organized as parent/sub-agent trees and can transfer control (`transfer_to_agent`) across parent/sub/peer boundaries (`src/google/adk/flows/llm_flows/auto_flow.py:24-39`, `src/google/adk/tools/transfer_to_agent_tool.py:26-41`).
- Graph-like because execution is event-driven over branches/invocations with resumability and explicit state markers rather than a fixed linear pipeline (`src/google/adk/runners.py:568-601`, `1330-1429`; `src/google/adk/agents/parallel_agent.py:35-48`).

Short control-flow excerpts:

From `src/google/adk/flows/llm_flows/base_llm_flow.py:1146-1153`:
```python
transfer_to_agent = function_response_event.actions.transfer_to_agent
if transfer_to_agent:
  agent_to_run = self._get_agent_to_run(invocation_context, transfer_to_agent)
  async with Aclosing(agent_to_run.run_async(invocation_context)) as agen:
    async for event in agen:
      yield event
```

From `src/google/adk/agents/parallel_agent.py:177-194`:
```python
for sub_agent in self.sub_agents:
  sub_agent_ctx = _create_branch_ctx_for_sub_agent(self, sub_agent, ctx)
  if not sub_agent_ctx.end_of_agents.get(sub_agent.name):
    agent_runs.append(sub_agent.run_async(sub_agent_ctx))
...
async with Aclosing(merge_func(agent_runs)) as agen:
  async for event in agen:
    yield event
```

## 4. Tools & External Integrations

- **Model APIs (Google GenAI / Gemini)**: LLM calls and live connections via `google.genai` types/connections (`src/google/adk/flows/llm_flows/base_llm_flow.py:26`, `523-535`, `1231-1235`).
- **Built-in Google Search tool**: Adds native model tool declarations for Gemini search (`src/google/adk/tools/google_search_tool.py:32-89`).
- **OpenAPI-backed HTTP tools**: Parses OpenAPI specs to runtime REST tools (`src/google/adk/tools/openapi_tool/openapi_spec_parser/openapi_toolset.py:44-63`, `227-243`).
- **MCP servers**: Connects over stdio/SSE/streamable HTTP to list/call MCP tools/resources (`src/google/adk/tools/mcp_tool/mcp_toolset.py:66-105`, `330-374`, `399-423`).
- **RAG/retrieval integrations**: Includes LlamaIndex retrieval adapters and file-based vector indexing (`src/google/adk/tools/retrieval/llama_index_retrieval.py`, `src/google/adk/tools/retrieval/files_retrieval.py:22-26`).
- **Data/infra toolsets**: Spanner, BigQuery/Bigtable-style modules, Pub/Sub, Vertex AI Search/RAG are present under `src/google/adk/tools/` (e.g., `src/google/adk/tools/spanner/spanner_toolset.py`, `src/google/adk/tools/pubsub/pubsub_toolset.py`, `src/google/adk/tools/vertex_ai_search_tool.py`).
- **Service integrations for runtime state**: configurable session/artifact/memory backends through CLI URIs (`src/google/adk/cli/cli_tools_click.py:523-584`, `1668-1689`, `1760-1778`).

## 5. Notable Code Walkthrough

- `src/google/adk/runners.py:502-633`  
  Main invocation loop: loads/creates session, sets up context, runs active agent, streams/persists events, and performs post-invocation compaction.

- `src/google/adk/agents/llm_agent.py:466-505`  
  Core LLM-agent execution logic: resumes sub-agent if needed, runs LLM flow, emits end-of-agent state for resumable workflows.

- `src/google/adk/flows/llm_flows/base_llm_flow.py:803-903`  
  Implements iterative reason-act loop (“one step = one LLM call”), with preprocess/tool registration, model call, and postprocess.

- `src/google/adk/flows/llm_flows/base_llm_flow.py:1111-1153`  
  Handles function-call execution and routes control to transferred agents after tool responses.

- `src/google/adk/agents/parallel_agent.py:150-206`  
  Spawns sub-agent runs in isolated branches and merges async event streams, enabling concurrent multi-agent execution.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** is accurate. The codebase is designed to automate structured, multi-step tasks via orchestrated agents + tools: agents can call APIs/tools, hand off work to specialized sub-agents, run parallel branches, pause/resume long-running calls, and persist state across sessions (`src/google/adk/agents/sequential_agent.py:49-93`, `src/google/adk/agents/parallel_agent.py:150-206`, `src/google/adk/runners.py:395-435`, `502-633`).  
This is broader than a chatbot and not primarily code generation or browser automation; it is a programmable agent workflow runtime.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - First-class multi-agent patterns (sequential/parallel/loop + transfer) built into runtime (`src/google/adk/agents/*.py`).
  - Strong execution substrate: resumability, session persistence, branch tracking, and event streaming (`src/google/adk/runners.py:568-601`, `1330-1429`).
  - Rich tool ecosystem including MCP, OpenAPI, search, retrieval, and cloud integrations (`src/google/adk/tools/...`).
  - Live/bidirectional mode with transcription/audio artifact handling for real-time agents (`src/google/adk/flows/llm_flows/base_llm_flow.py:475-655`).
  - Extensibility via callbacks/plugins around model and tool calls (`src/google/adk/agents/llm_agent.py:375-463`, `src/google/adk/runners.py:833-965`).

- **Limitations:**
  - Architecture is complex; many moving parts (flows, plugins, session state, branching) increase implementation/debug burden.
  - Some functionality is marked experimental/deprecated, indicating API churn risk (e.g., live features, deprecated fields/options) (`src/google/adk/runners.py:1046-1095`, `src/google/adk/agents/llm_agent.py:229-240`).
  - Parallel/loop live support is incomplete (`ParallelAgent`/`LoopAgent` `run_live` not implemented) (`src/google/adk/agents/parallel_agent.py:212-216`, `src/google/adk/agents/loop_agent.py:149-154`).
  - Heavy Google-ecosystem coupling in defaults and many integrations, though model-agnostic interfaces exist.

- **Research relevance:**
  - Useful evidence for **production-grade hierarchical multi-agent orchestration** with explicit control transfer and resume.
  - Demonstrates **event-sourced agent runtime design** (events as the canonical interaction/state record).
  - Provides a concrete implementation of **tool-mediated agent coordination** (function calls driving inter-agent transitions).
  - Offers a real-world testbed for studying reliability concerns in multi-agent systems (long-running tools, pause/resume, live reconnect).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
