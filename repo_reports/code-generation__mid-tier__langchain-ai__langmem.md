---
repo_name: langchain-ai/langmem
url: "https://github.com/langchain-ai/langmem"
stars: 1412
forks: 159
contributors_count: 12
last_commit_date: "2026-04-21T06:29:00+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 6
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Code Generation, RAG + Agents]
generated_at: "2026-04-27T12:49:59.371491+00:00"
model: auto
duration_s: 87.1
clone_size_kb: 3493
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`langmem` is a Python library for adding long-term and short-term memory capabilities to LLM applications, especially LangGraph-based agents. A developer typically imports factory functions like `create_manage_memory_tool`, `create_search_memory_tool`, `create_memory_store_manager`, or `SummarizationNode`, then plugs them into an existing agent/workflow. The runtime behavior is: search prior memories, extract/update/delete memories from new conversations, and optionally do this in the background via a reflection executor. Users get persistence and adaptation across sessions, not a standalone chatbot app (`src/langmem/knowledge/tools.py:25-356`, `src/langmem/knowledge/extraction.py:1006-1137`, `src/langmem/reflection.py:110-199`).

## 2. Agent Framework & Architecture

The codebase is primarily **LangGraph + LangChain Core**, with structured extraction via **trustcall**; there is no runtime CrewAI/AutoGen framework in `src` (dependency/import evidence: `pyproject.toml:8-17`, `src/langmem/knowledge/extraction.py:6-30`, `src/langmem/short_term/summarization.py:16-18`).  

Architecture-wise, this is a **memory subsystem for agents**, not a multi-agent team framework. The main “intelligence” sits in prompt templates and extractor loops that call LLM tools/schemas to decide memory operations (`src/langmem/knowledge/extraction.py:185-206`, `src/langmem/knowledge/extraction.py:253-339`). `MemoryStoreManager` orchestrates retrieval from `BaseStore`, runs a memory manager to reconcile existing/new memories, then writes deltas back to storage (`src/langmem/knowledge/extraction.py:1006-1137`).

A second axis is prompt optimization: gradient/metaprompt strategies run iterative “think/critique/recommend” loops and then rewrite prompts (`src/langmem/prompts/gradient.py:150-205`, `src/langmem/prompts/metaprompt.py:168-205`, `src/langmem/prompts/optimization.py:260-269`). These are still single workflow pipelines, not independent collaborating agents with separate goals.

## 3. Orchestration Pattern

Closest pattern: **Workflow Automation (sequential pipeline with optional graph nodes), plus iterative self-reflection loops**.  
Not a swarm/peer network; not manager-worker multi-agent runtime.

Control flow examples:

```1006:1037:src/langmem/knowledge/extraction.py
if self.query_gen:
    query_req = await self.query_gen.ainvoke(query_text, config=config)
    search_results_lists = await asyncio.gather(
        *[
            store.asearch(
                namespace, **({**tc["args"], "limit": self.query_limit})
            )
            for tc in query_req.tool_calls
        ]
    )
```

```1072:1135:src/langmem/knowledge/extraction.py
enriched = await self.memory_manager.ainvoke({...}, config=config)
store_based, ephemeral, removed = self._apply_manager_output(...)
...
await asyncio.gather(
    *(store.aput(**put) for put in final_puts),
    *(store.adelete(ns, key) for (ns, key) in final_deletes),
)
```

There are also LangGraph `StateGraph` wrappers for specific workflows (prompt optimization graph and summarization node integration), but these are still single-graph pipelines (`src/langmem/graphs/prompts.py:61-67`, `src/langmem/short_term/summarization.py:660-845`).

## 4. Tools & External Integrations

- **LangGraph BaseStore / vector-capable stores**: core persistence/search API (`search`, `put`, `delete`, async variants) wired across memory tools and manager (`src/langmem/knowledge/tools.py:489-497`, `src/langmem/knowledge/extraction.py:1363-1479`, `src/langmem/knowledge/extraction.py:1513-1659`).
- **LangGraph runtime config & entrypoints**: resolves namespace/store from graph context (`src/langmem/utils.py:73-91`, `src/langmem/knowledge/tools.py:25-39`).
- **LLM providers via LangChain model strings**: model init/invocation through `init_chat_model` and runnable tool binding (`src/langmem/knowledge/extraction.py:6`, `src/langmem/knowledge/extraction.py:778-785`).
- **trustcall structured extraction**: schema/tool-call based extraction for memories and prompt optimization (`src/langmem/knowledge/extraction.py:253-260`, `src/langmem/prompts/optimization.py:336-338`).
- **LangGraph SDK / remote runs**: `RemoteReflectionExecutor` submits background reflection jobs to LangGraph server (`src/langmem/reflection.py:19`, `src/langmem/reflection.py:182-195`).
- **LangSmith tracing/auth**: tracing in optimizers and auth hooks for graph API surface (`src/langmem/prompts/gradient.py:331-333`, `src/langmem/graphs/auth.py:20-45`).

No browser automation, shell execution, MCP client orchestration, or bespoke external HTTP tool suite is implemented in core agent runtime.

## 5. Notable Code Walkthrough

- `src/langmem/knowledge/extraction.py:217-445` - Defines `MemoryManager`, the core iterative extraction/upsert/delete logic over conversation messages and existing memories.
- `src/langmem/knowledge/extraction.py:832-1137` - `MemoryStoreManager` composes search + enrichment + persistence; this is the main production workflow wrapper.
- `src/langmem/knowledge/tools.py:25-356` - Builds callable memory-management tools (`manage_memory`, `search_memory`) intended for attaching to agents like `create_react_agent`.
- `src/langmem/reflection.py:110-199` and `src/langmem/reflection.py:254-329` - Factory and executors for local/remote background memory reflection jobs.
- `src/langmem/prompts/gradient.py:105-205` and `src/langmem/prompts/metaprompt.py:59-205` - Prompt optimization engines using iterative tool-mediated reflection loops.

## 6. Use-Case Mapping

The upstream label **Code Generation** does not match the core implementation. This repo does not primarily generate code artifacts; it manages memory and prompt adaptation around LLM applications. The dominant behavior is automating memory retrieval, consolidation, update, and persistence workflows around agent conversations (`src/langmem/knowledge/extraction.py:1725-1741`, `src/langmem/knowledge/tools.py:350-356`).  

Better category: **Workflow Automation** (with memory-centric augmentation for agents), not code generation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clean composable API surface for hot-path tools, background processing, and store-backed managers.
  - Strong LangGraph-native design (configurable namespaces, store integration, async/sync parity).
  - Practical memory lifecycle support: search, insert, update, delete, consolidation phases.
  - Iterative reflection patterns with bounded steps and schema-constrained tool outputs.
  - Good abstraction for local vs remote execution (`ReflectionExecutor`) without changing caller logic.

- **Limitations:**
  - Not a true multi-agent coordination system; mostly single workflow loops around one model pipeline.
  - `src/langmem/graph_rag.py` appears non-implemented/commented, so graph-RAG capability is not production code.
  - Heavy reliance on prompt quality/model behavior; few hard guarantees beyond schema/tool envelopes.
  - Most “multi-role” behavior (think/critique/recommend) is simulated via one model with tool-calling, not distinct agents.
  - Limited built-in evaluation/benchmarking harness in core package for memory quality/regression.

- **Research relevance:**
  - Useful evidence for **agent memory management architectures** in LangGraph ecosystems.
  - Demonstrates **LLM-in-the-loop state reconciliation** (retrieve → reflect → patch store).
  - Shows a practical pattern for **background reflective processing** decoupled from user-facing latency.
  - Illustrates schema/tool-constrained prompt optimization loops rather than free-form self-editing.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
