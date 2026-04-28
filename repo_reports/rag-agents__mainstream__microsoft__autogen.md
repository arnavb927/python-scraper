---
repo_name: microsoft/autogen
url: "https://github.com/microsoft/autogen"
stars: 57344
forks: 8641
contributors_count: 533
last_commit_date: "2026-04-06T22:35:32+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 7
architecture_labels: [AutoGen, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T10:14:00.899746+00:00"
model: auto
duration_s: 82.5
clone_size_kb: 87355
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`microsoft/autogen` is a full agent framework (Python + .NET) for building, running, and composing LLM-driven agents into teams that can solve multi-step tasks. In Python, users typically instantiate `AssistantAgent`/other agent types and run them directly or inside team orchestrators like `RoundRobinGroupChat`, `SelectorGroupChat`, `Swarm`, or `MagenticOneGroupChat` (e.g., `python/packages/autogen-agentchat/src/autogen_agentchat/agents/_assistant_agent.py:90-1704`, `.../teams/_group_chat/_base_group_chat.py:40-565`). At runtime, the framework handles model calls, tool execution loops, handoffs, memory injection, and termination logic. The result is a reusable runtime where users can launch anything from single tool-using assistants to coordinated multi-agent workflows with planner/orchestrator behavior.

## 2. Agent Framework & Architecture

The repository is primarily **AutoGen’s own framework** (not LangGraph/CrewAI as primary runtime dependencies in core paths). The core Python architecture is split across:
- `autogen-agentchat` (agent abstractions + team orchestration),
- `autogen-core` (runtime/messaging primitives),
- `autogen-ext` (model providers, tools, memory, code executors, MCP integrations).

Framework evidence is explicit in imports such as `from autogen_core ...`, `from autogen_agentchat ...` and internal classes like `AssistantAgent`, `BaseGroupChat`, `MagenticOneOrchestrator` (`_assistant_agent.py:23-61`, `_base_group_chat.py:6-38`, `_magentic_one_orchestrator.py:7-44`).

Architecturally, intelligence lives in multiple layers: (1) per-agent prompts + tool-calling loops (`AssistantAgent`), (2) team managers that choose next speaker via fixed policy (round-robin), model-based routing (selector), handoff-based routing (swarm), or ledger-driven orchestration (Magentic-One), and (3) pluggable memory/tool/workbench adapters. The same runtime supports nested teams and message buses via `SingleThreadedAgentRuntime` and topic subscriptions (`_base_group_chat.py:134-243`).

## 3. Orchestration Pattern

Closest match: **other (multi-pattern orchestration framework)** with strong support for **hierarchical manager-worker** and **swarm** modes.

- **Manager-worker / hierarchical**: `MagenticOneOrchestrator` creates facts/plan ledgers, evaluates progress, selects a worker agent, and can re-plan when stalled (`_magentic_one_orchestrator.py:156-190`, `300-406`, `428-440`).
- **Swarm / peer handoff**: `SwarmGroupChatManager` routes control by reading latest `HandoffMessage.target` (`_swarm_group_chat.py:82-98`).

Control-flow excerpts:
- In Magentic-One orchestration:
  - `progress_ledger["next_speaker"]["answer"]` is validated, then `GroupChatRequestPublish()` is sent to that participant topic (`_magentic_one_orchestrator.py:429-440`).
- In Swarm:
  - manager scans reversed thread, sets `_current_speaker = message.target`, returns that speaker (`_swarm_group_chat.py:92-98`).

So this is not one fixed graph/state machine; it is a runtime supporting multiple coordination strategies.

## 4. Tools & External Integrations

- **LLM model backends**: OpenAI/Azure/Anthropic/Ollama/etc via `autogen-ext` model clients (`python/packages/autogen-ext/src/autogen_ext/models/...`, e.g., `_openai_client.py` discovered in package index and imports in `_assistant_agent.py:259-260` examples).
- **MCP servers (Model Context Protocol)**: `McpWorkbench` wraps MCP sessions, exposes `list_tools`/`call_tool`, resources/prompts/templates (`autogen_ext/tools/mcp/_workbench.py:47-505`).
- **Code execution / terminal-like execution**: `PythonCodeExecutionTool` runs Python through pluggable executors (local, Docker, Azure) (`autogen_ext/tools/code_execution/_code_execution.py:28-97`).
- **RAG via GraphRAG**: `GlobalSearchTool` loads GraphRAG indices/parquet and performs map-reduce global search (`autogen_ext/tools/graphrag/_global_search.py:37-183`).
- **Vector memory stores**: ChromaDB-backed memory with semantic retrieval and context injection (`autogen_ext/memory/chromadb/_chromadb.py:35-414`).
- **Web/file agents in composite team**: `MagenticOne` wires `MultimodalWebSurfer`, `FileSurfer`, coding agent, and code executor (`autogen_ext/teams/magentic_one.py:211-221`).

## 5. Notable Code Walkthrough

- `python/packages/autogen-agentchat/src/autogen_agentchat/agents/_assistant_agent.py:901-1325`  
  Core single-agent runtime loop: add context, query memory, call model, execute tool calls concurrently, optionally reflect with second model call, and emit final response/handoff.

- `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py:191-565`  
  Foundational team engine: registers participants/manager in runtime, wires topic subscriptions, starts execution with `GroupChatStart`, and streams messages until termination.

- `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_selector_group_chat.py:152-309`  
  Model-based router manager: can use custom selector/candidate functions, otherwise prompts an LLM to choose the next speaker with retry/validation logic.

- `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_magentic_one/_magentic_one_orchestrator.py:156-190,300-406,451-513`  
  Advanced orchestrator: creates task/facts/plan ledger, monitors progress via structured JSON fields, triggers replanning on stalls, and synthesizes final answer.

- `python/packages/autogen-ext/src/autogen_ext/tools/mcp/_workbench.py:274-363,460-505`  
  Integration layer turning external MCP server capabilities into callable tool schemas/results for agents.

## 6. Use-Case Mapping

The assigned primary use case `RAG + Agents` is **partially correct but too narrow**. This codebase clearly supports RAG components (GraphRAG search tools, vector memory integration) (`_global_search.py:37-183`, `_chromadb.py:310-333`), but the dominant implementation is a **general-purpose multi-agent workflow orchestration framework**: speaker selection policies, handoff/swarm routing, orchestrator-led planning loops, and tool execution pipelines (`_base_group_chat.py`, `_selector_group_chat.py`, `_swarm_group_chat.py`, `_magentic_one_orchestrator.py`).  

Best fit from the provided taxonomy: **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Multiple concrete MAS coordination modes in one framework (round-robin, selector, swarm, orchestrator-led) (`_round_robin_group_chat.py`, `_selector_group_chat.py`, `_swarm_group_chat.py`, `_magentic_one_orchestrator.py`).
  - Clean separation between agent logic, runtime messaging, and integrations (`autogen-agentchat` vs `autogen-core` vs `autogen-ext`).
  - Strong extensibility for tools/workbenches/memory via component configs and serialization (`_assistant_agent.py:1649-1703`, `_workbench.py:493-504`).
  - Built-in support for tool loops, handoffs, streaming, and state save/load across teams and agents.
  - Practical ecosystem breadth (MCP, code execution, web/file agents, RAG, multiple model providers).

- **Limitations:**
  - Considerable architectural complexity; many abstractions/events increase learning and debugging cost.
  - Some selection/orchestration flows rely on strict JSON parsing/retries and can fail hard (`_magentic_one_orchestrator.py:318-385`).
  - Safety is largely advisory in docs/warnings rather than hard guarantees (e.g., risky web/terminal actions in Magentic-One).
  - Framework breadth can make “default best practices” ambiguous for newcomers (many team types and configs).
  - Certain hooks/features are non-serializable or partial (`selector_func` note, formatter serialization caveats).

- **Research relevance:**
  - Strong evidence for real-world **multi-agent control policies** beyond toy chatbots (routing, handoff, orchestrator with replanning).
  - Useful reference for studying **LLM tool-use loops** with reflection and concurrent tool execution (`_assistant_agent.py:1144-1325`).
  - Demonstrates **hybrid symbolic/procedural orchestration** (message bus + policy managers + LLM-based decision points).
  - Suitable empirical base for comparing MAS paradigms (hierarchical vs swarm vs model-router) under one API.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
