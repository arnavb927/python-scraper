---
repo_name: MemMachine/MemMachine
url: "https://github.com/MemMachine/MemMachine"
stars: 3519
forks: 172
contributors_count: 37
last_commit_date: "2026-04-22T21:45:36+00:00"
primary_use_case: RAG + Agents
user_tier: Mid-Tier
total_score: 8
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-05-05T07:09:31.084312+00:00"
model: auto
duration_s: 91.0
clone_size_kb: 101589
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

MemMachine is a memory infrastructure server for AI applications, not a full end-user chatbot: you run the FastAPI/MCP server (`memmachine_server.server.app`) and then call its REST or MCP endpoints to store and retrieve episodic + semantic memory for projects/users. In code, client SDKs send `add/search/list/delete` requests to `/api/v2/*`, and the server fans those out to configured memory backends (episodic, semantic, vector/graph stores) with optional retrieval-agent logic. When `agent_mode` is enabled on search, MemMachine applies an internal multi-agent retrieval pipeline (tool routing + query splitting/rewriting) before returning memories. The concrete output is structured memory results (episodes, semantic features, summaries), which upstream agents/frameworks can use as long-term context.

## 2. Agent Framework & Architecture

The core runtime is **custom agent orchestration**, not LangGraph/LangChain/CrewAI as the main engine. The server-side retrieval agents are handwritten classes (`ToolSelectAgent`, `ChainOfQueryAgent`, `SplitQueryAgent`, `MemMachineAgent`) in `packages/server/src/memmachine_server/retrieval_agent/agents/*`, all inheriting from a common `AgentToolBase` (`.../retrieval_agent/common/agent_api.py:57-175`). Framework-branded code exists mostly as optional integrations/client helpers (e.g., LangGraph helper tools in `packages/client/src/memmachine_client/langgraph.py:17-435`), not as the internal orchestrator.

Architecture-wise, one top-level router agent selects among specialist retrieval agents. `create_retrieval_agent()` wires this tree: `ToolSelectAgent` owns three child agents (split, chain-of-query, direct memory) and defaults to chain-of-query on uncertainty (`.../retrieval_agent/service_locator.py:17-57`). The “intelligence” is prompt-driven: a tool-selection prompt classifies query structure; a split prompt decomposes independent multi-entity questions; a sufficiency+rewrite prompt iteratively rewrites multi-hop queries (`tool_select_agent.py:21-81`, `split_query_agent.py:21-121`, `coq_agent.py:25-125`).

At runtime this orchestration is invoked from core search only when `agent_mode=True`: `query_search()` resolves a retrieval agent and routes long-term episodic retrieval through it (`.../main/memmachine.py:916-986`, `:769-863`), otherwise it performs direct memory queries.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with conditional routing**, plus some **parallel subquery execution** inside workers.

Top-level manager-worker routing is explicit in `ToolSelectAgent.do_query()`:

```188:197:packages/server/src/memmachine_server/retrieval_agent/agents/tool_select_agent.py
if tool is None:
    if self._default_tool is not None:
        tool = self._default_tool
    else:
        raise RuntimeError("No tool selected")
chunks, perf_metrics = await tool.do_query(policy, query)
perf_metrics["selected_tool"] = tool.agent_name
```

Control enters this tree from `query_search()` when agent mode is enabled:

```951:963:packages/server/src/memmachine_server/main/memmachine.py
property_filter = parse_filter(search_filter) if search_filter else None
if MemoryType.Episodic in target_memories:
    retrieval_agent = await self._get_retrieval_agent() if agent_mode else None
    episodic_task = asyncio.create_task(
        self._search_episodic_memory(
            ...
            retrieval_agent=retrieval_agent,
```

Within a selected worker, `SplitQueryAgent` executes sub-queries concurrently (`asyncio.gather`) before reranking (`split_query_agent.py:185-213`), while `ChainOfQueryAgent` runs iterative rewrite/check loops (`coq_agent.py:312-357`).

## 4. Tools & External Integrations

- **LLM APIs (OpenAI Responses / Chat Completions)**: used for routing, splitting, and query rewriting prompts via `LanguageModel.generate_response_with_token_usage` (`.../retrieval_agent/agents/*.py`); concrete provider wrappers in `.../common/language_model/openai_responses_language_model.py:79-340` and built by `language_model_manager.py:178-220`.
- **Amazon Bedrock LLMs**: alternate provider with tool-call support through Bedrock Converse (`.../common/language_model/amazon_bedrock_language_model.py:153-449`), instantiated in `language_model_manager.py:222-261`.
- **MCP server integration**: MemMachine exposes MCP tools (`add_memory`, `search_memory`, `delete_memory`) via FastMCP (`.../server/api_v2/mcp.py:414-581`) and mounts MCP on `/mcp` (`.../server/app.py:71-73`).
- **Vector stores / databases**: Qdrant, SQLite/SQLite-vec, Neo4j, NebulaGraph are managed in `database_manager.py:46-746`; Qdrant implementation in `.../common/vector_store/qdrant_vector_store.py`.
- **Reranker component**: retrieval agents rerank merged results via `_do_rerank` (`.../retrieval_agent/common/agent_api.py:97-137`) using configured reranker resources.
- **External agent-framework adapters (optional)**: LangGraph convenience tools (`packages/client/src/memmachine_client/langgraph.py:17-435`) and additional integration directories for LangChain/CrewAI/LlamaIndex/OpenAI Agents SDK under `integrations/`.

## 5. Notable Code Walkthrough

- `packages/server/src/memmachine_server/main/memmachine.py:274-307,769-863,916-986`  
  Lazily builds the retrieval-agent stack, toggles it with `agent_mode`, and injects agent-driven long-term memory search into the main `query_search` path.
- `packages/server/src/memmachine_server/retrieval_agent/service_locator.py:17-57`  
  Defines the agent hierarchy: direct memory retriever + split-query + chain-of-query, wrapped by tool-selection router.
- `packages/server/src/memmachine_server/retrieval_agent/agents/tool_select_agent.py:21-81,144-197`  
  Contains the classification prompt and deterministic dispatch from query type to specialized agent.
- `packages/server/src/memmachine_server/retrieval_agent/agents/coq_agent.py:197-261,292-357`  
  Implements iterative sufficiency checking + query rewriting loop for multi-hop retrieval, including evidence tracking and confidence gating.
- `packages/server/src/memmachine_server/server/api_v2/mcp.py:414-581`  
  Exposes MemMachine as MCP tools so other LLM agents can call memory operations through standardized tool interfaces.

## 6. Use-Case Mapping

This repo materially implements **RAG + Agents** behavior: retrieval is performed over stored episodic/semantic memory, and when `agent_mode` is on, a coordinated multi-agent retrieval controller decomposes/rewrites/reroutes queries before returning context (`main/memmachine.py:916-986`, `retrieval_agent/*`). So the upstream assignment is mostly correct for core capability.

That said, MemMachine is also strongly **workflow infrastructure**: it is a memory platform/API used by other agents rather than an end-user autonomous agent app. If forced to pick one dominant runtime category for this codebase alone, I would still classify it as **RAG + Agents** with an infrastructure-first flavor.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear modular multi-agent retrieval stack with explicit router/specialist roles (`service_locator.py`, `tool_select_agent.py`).
  - Practical hybrid memory architecture (episodic + semantic + multiple storage backends) in production-style API.
  - Agent-mode is optional and composable; baseline retrieval still works without orchestration (`main/memmachine.py`).
  - Strong integration surface (REST + MCP + Python/TS SDKs + adapters for major agent frameworks).
  - Prompted decomposition (split vs chain-of-query) plus reranking and confidence thresholds is explicit and inspectable.

- **Limitations:**
  - Agent coordination is prompt-heavy and heuristic; little learned policy or formal planner beyond LLM prompting.
  - No explicit graph-state engine for orchestration (not LangGraph-style state machine internally).
  - Tool selection robustness depends on one-shot text matching in model output (`tool_select_agent.py:167-177`).
  - Evaluation/guardrails for retrieval-agent correctness are present in tests, but runtime self-verification remains limited.
  - Much of “multi-agent” is confined to retrieval-time query handling, not broader autonomous task execution.

- **Research relevance:**
  - Good evidence of **manager-worker query orchestration** in real memory-RAG systems.
  - Illustrates design tradeoffs between direct retrieval and iterative query-rewrite loops.
  - Useful case study of MCP-enabled memory tooling for external agents.
  - Demonstrates engineering patterns for pluggable memory backends in agent ecosystems.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
