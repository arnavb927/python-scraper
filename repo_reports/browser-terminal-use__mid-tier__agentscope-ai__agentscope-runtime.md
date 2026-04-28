---
repo_name: agentscope-ai/agentscope-runtime
url: "https://github.com/agentscope-ai/agentscope-runtime"
stars: 746
forks: 141
contributors_count: 36
last_commit_date: "2026-04-20T09:24:34+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 6
architecture_labels: [LangGraph, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-04-27T13:03:30.389788+00:00"
model: auto
duration_s: 103.4
clone_size_kb: 10954
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`agentscope-runtime` is a serving/runtime layer for turning agent code into production APIs rather than a single built-in assistant. A developer defines an `AgentApp`, registers a query handler for a chosen framework (AgentScope, LangGraph, Agno, etc.), and runs or deploys it via FastAPI/Uvicorn (`src/agentscope_runtime/engine/app/agent_app.py:60-66`, `:722-740`, `:881-924`). At runtime it standardizes streaming events, protocol compatibility (A2A, AG-UI, OpenAI Responses), and deployment/lifecycle controls (`src/agentscope_runtime/engine/runner.py:199-356`, `src/agentscope_runtime/engine/deployers/adapter/responses/response_api_protocol_adapter.py:285-315`). It also provides sandbox and MCP-backed tool infrastructure so user agents can safely use browser/GUI/filesystem/mobile environments (`src/agentscope_runtime/engine/services/sandbox/sandbox_service.py:11-143`, `src/agentscope_runtime/sandbox/box/browser/browser_sandbox.py:31-57`).

## 2. Agent Framework & Architecture

This repo is **custom runtime infrastructure** with adapters for multiple external agent frameworks, not a pure LangGraph/AutoGen/CrewAI implementation. Framework selection is explicit at runtime (`agentscope`, `autogen`, `agno`, `langgraph`) in `AgentApp.query()` (`src/agentscope_runtime/engine/app/agent_app.py:722-740`), and `Runner.stream_query()` dispatches to framework-specific message adapters (`src/agentscope_runtime/engine/runner.py:246-312`). Optional deps confirm this multi-framework stance (`langgraph`, `autogen-agentchat`, `langchain`, `agno`) in `pyproject.toml:68-99`.

High-level architecture is: user-defined handler -> `Runner` execution -> adapter-normalized event stream -> FastAPI endpoints/protocol adapters. The “intelligence” (prompting, planning, graph logic, tool policies) mostly lives in the **user’s agent code**, while this repo handles orchestration plumbing, streaming, schema conversion, and deployment. The integrated LangGraph test shows the intended pattern: user builds a `StateGraph`, compiles it, and streams graph outputs through `AgentApp` (`tests/integrated/test_langgraph_agent_app.py:54-70`, `:88-114`).

It includes protocol-layer interop (A2A, AG-UI, OpenAI Responses) and registry hooks, but these expose agents as services; they do not themselves implement multi-agent reasoning/planning loops (`src/agentscope_runtime/engine/deployers/adapter/a2a/a2a_protocol_adapter.py:136-258`).

## 3. Orchestration Pattern

Closest match: **event-driven adapter pipeline** (with optional graph logic only when user supplies LangGraph in their own app).

Control flow is event-stream-centric: `Runner.stream_query()` picks adapter by framework and yields normalized events until completion/failure (`src/agentscope_runtime/engine/runner.py:246-356`):

```291:330:src/agentscope_runtime/engine/runner.py
if self.framework_type == "langgraph":
    from ..adapters.langgraph.stream import adapt_langgraph_message_stream
    ...
    stream_adapter = adapt_langgraph_message_stream
...
async for event in stream_adapter(
    source_stream=self._call_handler_streaming(
        self.query_handler,
        **query_kwargs,
        **kwargs,
    ),
```

`AgentApp` then exposes this as SSE endpoint output (`src/agentscope_runtime/engine/app/agent_app.py:798-807`, `:690-703`):

```695:703:src/agentscope_runtime/engine/app/agent_app.py
async for chunk in self._runner.stream_query(request, **kwargs):
    if hasattr(chunk, "model_dump_json"):
        data = chunk.model_dump_json()
    ...
    yield f"data: {data}\n\n"
```

When users choose LangGraph, graph-style orchestration exists in their app code (example test), not in the runtime core (`tests/integrated/test_langgraph_agent_app.py:66-70`, `:103-113`).

## 4. Tools & External Integrations

- **MCP server/tool integration**: `MCPWrapper` dynamically wraps runtime tools into FastMCP tools (`src/agentscope_runtime/tools/mcp_wrapper.py:14-216`); MCP utility and sandbox MCP routers are present (`src/agentscope_runtime/tools/utils/mcp_util.py`, `src/agentscope_runtime/sandbox/box/shared/routers/mcp.py`).
- **Browser automation**: Browser sandbox wraps many browser actions (`browser_navigate`, `browser_click`, screenshots, tabs) via MCP tool calls (`src/agentscope_runtime/sandbox/box/browser/browser_sandbox.py:104-157`, `:159-301`), with Playwright MCP server config (`src/agentscope_runtime/sandbox/box/browser/box/mcp_server_configs.json:2-13`).
- **GUI/computer-use automation**: GUI sandbox ships `computer-use-mcp` server wiring (`src/agentscope_runtime/sandbox/box/gui/box/mcp_server_configs.json:2-10`).
- **Sandbox management service**: session-scoped environment provisioning/connect/release across sandbox types (`src/agentscope_runtime/engine/services/sandbox/sandbox_service.py:48-103`, `:144-231`).
- **Framework tool adapters**: runtime tools are adapted for AgentScope and AutoGen tool interfaces (`src/agentscope_runtime/adapters/agentscope/tool/tool.py:17-169`, `src/agentscope_runtime/adapters/autogen/tool/tool.py:28-212`).
- **Protocol integrations**: A2A endpoints/registry (`src/agentscope_runtime/engine/deployers/adapter/a2a/a2a_protocol_adapter.py:222-331`), OpenAI Responses compatibility endpoint (`src/agentscope_runtime/engine/deployers/adapter/responses/response_api_protocol_adapter.py:22-31`, `:285-315`), and AG-UI adapter (wired from `agent_app.py:349-357`).
- **Model/tool services**: DashScope-oriented search/generation/ASR/TTS/payment tools are registered in tool metadata (`src/agentscope_runtime/tools/__init__.py:76-119`).

## 5. Notable Code Walkthrough

- `src/agentscope_runtime/engine/app/agent_app.py:60-66,722-740,760-846`  
  Core app abstraction: binds user hooks, sets framework type, builds the internal runner, and mounts `/process` SSE plus task endpoints.
- `src/agentscope_runtime/engine/runner.py:199-356`  
  Central execution pipeline: validates requests, routes by framework adapter, streams normalized events, and emits terminal status/error envelopes.
- `src/agentscope_runtime/adapters/langgraph/stream.py:28-44,64-94,198-230`  
  Converts LangGraph/LangChain message objects (AI/tool/system/human) into runtime message/event schema, including tool-call and tool-output events.
- `src/agentscope_runtime/engine/services/sandbox/sandbox_service.py:82-143,144-231`  
  Lifecycle for creating/reconnecting/releasing sandbox environments per session context, enabling safe external tool execution.
- `tests/integrated/test_langgraph_agent_app.py:54-70,88-115`  
  Representative end-to-end usage: user defines a LangGraph `StateGraph`, registers it with `@agent_app.query(framework="langgraph")`, and streams graph outputs through runtime APIs.

## 6. Use-Case Mapping

The assigned `Browser / Terminal Use` label is **partially supported but not primary**. The repo clearly includes browser/GUI/mobile sandbox + MCP wiring for computer/browser tools (`browser_sandbox.py`, `mcp_server_configs.json`), so browser-use workloads are feasible. However, the dominant codebase focus is a generic runtime for deploying/serving agent workflows across frameworks, protocols, and environments (`agent_app.py`, `runner.py`, deployer/adapters), which aligns better with **Workflow Automation** as the principal category.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong multi-framework interoperability with one runtime API surface (`agent_app.py:722-740`, `runner.py:246-312`).
  - Protocol breadth (A2A + OpenAI Responses + AG-UI) for ecosystem compatibility (`a2a_protocol_adapter.py`, `response_api_protocol_adapter.py`).
  - Practical secure-execution orientation via managed sandboxes and MCP tool boundaries (`sandbox_service.py`, `mcp_wrapper.py`).
  - Streaming-first design with consistent event schema normalization across frameworks (`runner.py`, adapter `stream.py` files).
  - Deployment-aware architecture (local/container/k8s/serverless components in `engine/deployers/*`).

- **Limitations:**
  - Runtime core does not provide built-in multi-agent coordination logic (planner-worker/swarm); intelligence is delegated to user app code.
  - No native graph/planner DSL in runtime itself; graph orchestration appears only via external framework integrations (e.g., LangGraph in tests).
  - Framework-specific adapter complexity is high and may be brittle as upstream message schemas evolve (`adapters/agentscope/stream.py` is large/branchy).
  - Tool catalog is skewed toward specific vendor ecosystems (notably DashScope-centric modules in `tools/*`).

- **Research relevance:**
  - Useful evidence for **agent runtime standardization** across heterogeneous frameworks/protocols.
  - Shows an implementation pattern for **agent API compatibility layers** (A2A + OpenAI Responses on top of one execution core).
  - Relevant to studies on **safe tool execution** via sandbox+MCP mediation in production settings.
  - Less suitable as evidence of novel multi-agent reasoning algorithms (it is infrastructure-first).

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
