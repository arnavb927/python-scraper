---
repo_name: Idun-Group/idun-agent-platform
url: "https://github.com/Idun-Group/idun-agent-platform"
stars: 161
forks: 7
contributors_count: 4
last_commit_date: "2026-04-22T14:10:13+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 5
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T14:43:26.842049+00:00"
model: auto
duration_s: 110.1
clone_size_kb: 125783
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`Idun-Group/idun-agent-platform` is a deployment/control-plane stack for turning an existing agent (mainly LangGraph, also ADK/Haystack) into a production API service with auth, guardrails, observability, and channel integrations. In practice, a user runs the engine (`idun agent serve`) with YAML or manager-fetched config, and gets a FastAPI service exposing `/agent/run` streaming endpoints plus optional webhooks for Slack/Discord/WhatsApp/Google Chat. The manager service stores agent/resource configs in PostgreSQL and materializes a ready-to-run `engine_config` JSON for the engine (`services/idun_agent_manager/src/app/services/engine_config.py:26-114`). The repo is less a “new agent algorithm” project and more an operations/runtime wrapper around externally defined agents.

## 2. Agent Framework & Architecture

Frameworks actually used in code:

- **LangGraph** (primary): `langgraph.graph.StateGraph`, `CompiledStateGraph`, `astream_events` in `libs/idun_agent_engine/src/idun_agent_engine/agent/langgraph/langgraph.py:28-33,504-506`.
- **Google ADK**: `google.adk.*` classes in `libs/idun_agent_engine/src/idun_agent_engine/agent/adk/adk.py:17-29`.
- **Haystack** adapter is present (wired via `ConfigBuilder`), though less central (`libs/idun_agent_engine/src/idun_agent_engine/core/config_builder.py:401-412`).
- **LangChain ecosystem** is used for model/tool glue (e.g., `init_chat_model` in templates and `langchain_mcp_adapters` in MCP registry).
- **DeepAgents template** exists via `create_deep_agent` in `libs/idun_agent_engine/src/idun_agent_engine/templates/deep_research.py:5,41`.

Architecture is adapter-based: `ConfigBuilder.initialize_agent_from_config()` picks exactly one agent backend from config, instantiates one adapter, and initializes it (`.../core/config_builder.py:279-430`). The server lifecycle then stores that single initialized agent in `app.state.agent` and serves it via `/agent/run` (`.../server/lifespan.py:65-75`, `.../server/routers/agent.py:78-137`).

The “intelligence” mostly lives outside this repo in user-supplied graph/agent definitions (`graph_definition` / `agent` imports), while Idun contributes runtime concerns: guardrail checks, AG-UI event encoding, persistence/checkpoint wiring, observability, MCP tool registry, and webhook channels (`.../agent/langgraph/langgraph.py:238-260`, `.../server/routers/agent.py:93-137`, `.../mcp/registry.py:109-209`).

## 3. Orchestration Pattern

Closest match: **other** (single-agent service wrapper with pluggable internal orchestration).  
Why: the platform itself orchestrates request -> guardrails -> one agent adapter -> stream response, not multiple coordinated peer/manager agents.

Control-flow excerpt (single runtime agent selection):
`libs/idun_agent_engine/src/idun_agent_engine/core/config_builder.py:300-316`
```python
if agent_type == AgentFramework.LANGGRAPH:
    from idun_agent_engine.agent.langgraph.langgraph import LanggraphAgent
    validated_config = LangGraphAgentConfig.model_validate(agent_config_obj)
    agent_instance = LanggraphAgent()
...
await agent_instance.initialize(validated_config, observability_config)
return agent_instance
```

Control-flow excerpt (HTTP run pipeline):
`libs/idun_agent_engine/src/idun_agent_engine/server/routers/agent.py:93-106`
```python
guardrails = getattr(request.app.state, "guardrails", [])
if guardrails:
    guardrail_input = _guardrail_input_from(input_data)
    if guardrail_input is not None:
        _run_guardrails(guardrails, text=guardrail_input, position="input")

async for event in agent.run(input_data):
    yield encoder.encode(event)
```

Note: user-provided LangGraph graphs can internally be graph-style workflows (e.g., looping tool node in `libs/idun_agent_engine/examples/09_langgraph_mcp/agent.py:75-83`), but that orchestration is authored by the user graph, not by Idun’s core runtime.

## 4. Tools & External Integrations

- **MCP servers / tool calling**: `MultiServerMCPClient` registry and tool loading in `libs/idun_agent_engine/src/idun_agent_engine/mcp/registry.py:109-209`; helper resolution from file/env/manager API in `.../mcp/helpers.py:116-196`.
- **Manager API config fetch**: engine pulls `GET /api/v1/agents/config` via `requests` in `.../core/config_builder.py:99-133` and `.../mcp/helpers.py:68-90`.
- **Persistence stores for agent memory/checkpoints**:
  - LangGraph checkpoints: in-memory, SQLite, Postgres (`.../agent/langgraph/langgraph.py:294-317`).
  - ADK session/memory services: in-memory, Vertex AI, DB (`.../agent/adk/adk.py:255-299`).
- **Messaging/webhook integrations**:
  - WhatsApp Graph API client (`.../integrations/whatsapp/client.py:12-44`)
  - Discord interactions API (`.../integrations/discord/client.py:12-50`)
  - Slack Events API (`.../integrations/slack/handler.py:39-82`)
  - Google Chat API + token verification (`.../integrations/google_chat/client.py:13-33`, `.../verify.py:18-48`)
  - Wiring factory in `.../integrations/base.py:31-72`.
- **Observability providers**: Langfuse/Phoenix/LangSmith/GCP hooks are initialized in adapters and observability modules (`.../agent/langgraph/langgraph.py:172-237`, `.../agent/adk/adk.py:139-230`).
- **Guardrails AI Hub**: guardrail parsing/validation in runtime flow (`.../server/lifespan.py:22-31`, `.../server/routers/agent.py:58-67`).

## 5. Notable Code Walkthrough

- `libs/idun_agent_engine/src/idun_agent_engine/core/config_builder.py:279-430`  
  Central dispatcher that validates config, picks framework adapter (LangGraph/ADK/Haystack/templates), and initializes one runtime agent. This is the key “assembly point” of the platform.

- `libs/idun_agent_engine/src/idun_agent_engine/agent/langgraph/langgraph.py:159-260,504-627`  
  Loads a user graph dynamically, compiles with configured checkpointer, and translates LangGraph event stream into AG-UI events for clients. This is the primary execution adapter.

- `libs/idun_agent_engine/src/idun_agent_engine/server/routers/agent.py:78-137`  
  Canonical `/agent/run` endpoint: optional guardrail validation, then SSE streaming of normalized AG-UI events. This is the API surface most users hit.

- `libs/idun_agent_engine/src/idun_agent_engine/mcp/registry.py:109-307`  
  MCP server abstraction for LangChain and ADK toolsets, including per-server fault tolerance and schema sanitation. It is the tool-integration bridge.

- `services/idun_agent_manager/src/app/services/engine_config.py:26-114,149-225`  
  Rebuilds materialized `engine_config` from relational resources (guardrails, MCP, observability, integrations, memory/SSO), enabling manager-driven workflow automation at scale.

## 6. Use-Case Mapping

The assigned label **Workflow Automation** is accurate. This repo automates the operational workflow around agents: configure resources in manager -> materialize runnable config -> engine starts agent with guardrails/telemetry/MCP/tools/channels -> serve unified streaming API. It is not mainly “multi-agent research code,” nor code generation/RAG-specific logic. The core value is production workflow orchestration and governance for agent services.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong separation between control plane (manager) and runtime plane (engine), with materialized config handoff.
  - Framework-agnostic adapter design (LangGraph, ADK, Haystack) with shared AG-UI interface.
  - Practical production features: guardrails, SSO, observability, webhook channels, checkpoint backends.
  - MCP integration is robust (multi-server loading with per-server failure isolation and schema patching).
  - Clear runtime lifecycle and dependency injection points in FastAPI.

- **Limitations:**
  - Core runtime is mostly single-agent-per-service; no native multi-agent coordinator in platform core.
  - Some code paths are still deprecated/shimmed (`/agent/invoke`, `/agent/stream`), adding maintenance complexity.
  - ADK streaming path is marked not implemented in adapter (`.../agent/adk/adk.py:410-418`) while `/run` relies on wrapper behavior.
  - Template logic (e.g., deep research) depends on external libs/services and env setup, with limited in-repo orchestration logic.
  - Heavy dynamic imports can make static analysis/debugging harder for large deployments.

- **Research relevance:**
  - Useful evidence for **agent operations/governance infrastructure** rather than novel multi-agent coordination algorithms.
  - Demonstrates a real-world pattern for standardizing heterogeneous agent frameworks behind one API protocol (AG-UI).
  - Shows how MCP/tooling, observability, and guardrails can be composed into deployable agent services.
  - Provides practical examples of stateful graph-agent serving with configurable persistence layers.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
