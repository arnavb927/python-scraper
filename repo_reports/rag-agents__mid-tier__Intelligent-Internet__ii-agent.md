---
repo_name: Intelligent-Internet/ii-agent
url: "https://github.com/Intelligent-Internet/ii-agent"
stars: 3325
forks: 503
contributors_count: 9
last_commit_date: "2026-04-13T03:53:56+00:00"
primary_use_case: RAG + Agents
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T13:50:03.814833+00:00"
model: auto
duration_s: 104.4
clone_size_kb: 117953
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`ii-agent` is a full-stack FastAPI + Socket.IO platform for running tool-using LLM agents in persistent user sessions, with billing, sandboxes, and connector integrations. In practice, a user sends a `query`/`plan` command over realtime APIs, the backend spins up an `IIAgent`, and the run streams events (tool calls, outputs, status) back to the client (`src/ii_agent/realtime/handlers/query.py:36-160`). The system supports both general coding/workflow agents and chat/council modes, with optional file-grounded retrieval via OpenAI vector stores (`src/ii_agent/chat/application/file_processing_service.py:75-90`, `src/ii_agent/chat/tools/file_search.py:23-40`). So users get an interactive “agent runtime” that can reason, call tools, access uploaded docs, and execute multi-step automation tasks rather than a simple one-shot chatbot.

## 2. Agent Framework & Architecture

This is a **custom agent framework** (not LangGraph/CrewAI/AutoGen/LlamaIndex orchestration). The core runtime is `IIAgent` (`src/ii_agent/agents/agent.py:125-205`), and the file header explicitly says it is adapted from Agno (`src/ii_agent/agents/agent.py:18`). Repository search shows no substantive LangGraph/LangChain/CrewAI/AutoGen orchestration imports in `src` besides one mention in a comment (`src/ii_agent/agents/agent.py:1` from search result).

Architecture is split between:
- **Realtime command layer** (`query`, `plan`, `continue_run`, etc.) that claims tasks and streams events (`src/ii_agent/realtime/handlers/factory.py:61-95`).
- **Agent factory + tool resolver** that builds an `IIAgent` by `AgentType`, model provider, and feature flags (`src/ii_agent/agents/factory/agent.py:43-197`, `src/ii_agent/agents/factory/tool_manager.py:21-70`).
- **Prompt-centric intelligence** with large system prompts and specialized overlays per agent type (`src/ii_agent/agents/prompts/agent_prompts.py:1077-1150`).

The design includes optional multi-agent coordination: the main agent can include `sub_agents` and delegate via injected delegation functions (`src/ii_agent/agents/agent.py:278-431`), and chat has a parallel “council” mode that runs multiple models then synthesizes (`src/ii_agent/chat/application/council_service.py:79-247`).

## 3. Orchestration Pattern

Closest match: **event-driven manager-worker**, with optional **hierarchical delegation**.

- Event-driven: socket command handlers are registered and dispatched by command type (`src/ii_agent/realtime/handlers/factory.py:63-95`), then handlers launch agent runs and stream run events (`src/ii_agent/realtime/handlers/query.py:144-160`).
- Hierarchical: parent `IIAgent` can call `sub_agent_task`/`sub_agent_task_all` tools to delegate work to sub-agents (`src/ii_agent/agents/agent.py:412-431`).

Example control flow excerpt (handler -> agent run):
```python
92:103:src/ii_agent/realtime/handlers/query.py
agent = await agent_factory.create_agent(
    user_id=str(session_info.user_id),
    session_id=str(session_info.id),
    llm_config=llm_config,
    agent_type=AgentType(session_info.agent_type)
    if session_info.agent_type
    else AgentType.GENERAL,
    session_store=session_store,
    tool_args=query_command.tool_args,
)
```

Example delegation excerpt (parent -> sub-agent tool):
```python
422:429:src/ii_agent/agents/agent.py
delegate_func = Function.from_callable(
    adelegate_task_to_member,
    name="sub_agent_task",
)
delegate_func.description = f"Delegate a task to a specific sub-agent. Available sub-agents:\n{sub_agents_description}"
delegate_func.stop_after_tool_call = False
delegate_func.show_result = True
```

## 4. Tools & External Integrations

- **Shell + filesystem tools in sandbox**: `ShellRunCommand`, `FileReadTool`, `ApplyPatchTool`, etc., wired in agent tool configs (`src/ii_agent/agents/factory/tools.py:64-107`, `src/ii_agent/agents/tools/shell/shell_run_command.py:45-94`).
- **Web search/browse**: `WebSearchTool`, `WebVisitTool`, `ImageSearchTool`, and batch/compressed visit tools (`src/ii_agent/agents/factory/tools.py:77-82`, `src/ii_agent/agents/tools/web/web_search_tool.py:39-78`).
- **RAG via vector store + file search**: uploaded large docs are pushed to OpenAI vector stores (`src/ii_agent/chat/application/file_processing_service.py:75-90`, `src/ii_agent/chat/vectorstore/openai.py:31-106`), queried with `FileSearchTool` (`src/ii_agent/chat/tools/file_search.py:23-179`).
- **MCP servers**: user-configured MCP tools are wrapped and executed through sandbox-exposed MCP endpoints (`src/ii_agent/agents/factory/mcp/user_mcp_tool.py:21-113`).
- **External connector ecosystem (Composio + GitHub)**: Composio toolkit discovery/auth metadata (`src/ii_agent/integrations/connectors/composio/toolkit_service.py:94-125`), plus dynamic GitHub tool loading in chat (`src/ii_agent/chat/application/tool_service.py:128-163`).
- **LLM providers**: Anthropic/OpenAI/Google/Vertex/Cerebras are provider-configured via model layer and settings (`src/ii_agent/agents/factory/agent.py:99-103`, `pyproject.toml:11-17`).

## 5. Notable Code Walkthrough

- `src/ii_agent/realtime/handlers/query.py:36-160` - Main runtime entrypoint for user agent execution: validates session, claims run task, creates agent, prepares files/sandbox, and streams events.
- `src/ii_agent/agents/factory/agent.py:43-197` - Central constructor that selects model, resolves tools, composes prompts, and optionally attaches sub-agents (e.g., task agent).
- `src/ii_agent/agents/agent.py:278-431` - Core multi-agent mechanism: injects `sub_agent_task` delegation functions so the LLM can route work to child agents.
- `src/ii_agent/chat/application/file_processing_service.py:29-110` - Bridges uploaded files into immediate message parts vs. vector-store indexing for later retrieval.
- `src/ii_agent/chat/application/council_service.py:159-247` - Parallel multi-model “council” execution with timeout/error handling, then synthesis model aggregation.

## 6. Use-Case Mapping

The assigned label **RAG + Agents** is partially correct, but the stronger primary behavior in code is **Workflow Automation** with agentic tooling. The project clearly supports RAG (vector store ingestion + `file_search`) (`src/ii_agent/chat/application/file_processing_service.py:75-90`, `src/ii_agent/chat/tools/file_search.py:163-170`), yet the dominant architecture is a tool-executing automation agent platform (shell, file edits, web, connectors, MCP, deployments) controlled by realtime command handlers and long-running tasks (`src/ii_agent/agents/factory/tools.py:193-240`, `src/ii_agent/realtime/handlers/factory.py:63-95`). So this is best categorized as a workflow automation agent framework that includes RAG as one subsystem.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong production-oriented orchestration: task claiming, run status transitions, event streaming, cancellation (`src/ii_agent/realtime/handlers/query.py:62-87`, `171-186`).
  - Broad tool abstraction across shell/files/web/MCP/connectors with typed schemas (`src/ii_agent/agents/factory/tools.py:64-107`).
  - Real multi-agent capabilities: explicit sub-agent delegation in core runtime (`src/ii_agent/agents/agent.py:278-431`).
  - Parallel multi-model council with synthesis, giving a practical ensemble pattern (`src/ii_agent/chat/application/council_service.py:159-247`).
  - Built-in retrieval pipeline for uploaded docs tied to session/user metadata (`src/ii_agent/chat/tools/file_search.py:115-149`).

- **Limitations:**
  - Multi-agent delegation appears feature-flag/option dependent (`task_agent`), not the default path for every run (`src/ii_agent/agents/factory/agent.py:165-174`).
  - No explicit graph/state-machine DSL (e.g., LangGraph-style nodes/edges); orchestration is mostly imperative handlers.
  - Heavy prompt logic in giant prompt files may be harder to maintain/verify formally (`src/ii_agent/agents/prompts/agent_prompts.py` large monolithic content).
  - Tight coupling to OpenAI vector-store APIs for retrieval path in chat (`src/ii_agent/chat/vectorstore/openai.py:341-360`).
  - Some legacy/sub-agent imports (`ii_agent.sub_agent.*`) suggest transitional architecture boundaries (`src/ii_agent/agents/factory/agent.py:326`, `382`, `463`).

- **Research relevance:**
  - Evidence of an industry-grade **event-driven agent runtime** with persistent task lifecycle and realtime telemetry.
  - Useful example of **hybrid orchestration**: single-agent tool loop + optional hierarchical delegation + parallel council synthesis.
  - Concrete case of integrating **RAG, tools, and connectors** under one agent control plane.
  - Good reference for studying practical tradeoffs between custom orchestration and framework-based graph orchestration.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
