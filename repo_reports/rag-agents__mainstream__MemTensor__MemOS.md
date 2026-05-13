---
repo_name: MemTensor/MemOS
url: "https://github.com/MemTensor/MemOS"
stars: 8504
forks: 753
contributors_count: 65
last_commit_date: "2026-04-22T13:42:07+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-05-05T08:06:27.353789+00:00"
model: auto
duration_s: 209.6
clone_size_kb: 25335
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`MemTensor/MemOS` is a Python memory middleware/platform that wraps LLM chat with persistent, searchable memory and background memory lifecycle processing. In practice, a user runs either the `MOS` Python API (e.g., create `MOS`, register a cube, call `add/search/chat`) or the FastAPI service endpoints under `/product/*` for chat/search/add/scheduler operations (`src/memos/mem_os/core.py:251-352`, `src/memos/api/routers/server_router.py:104-239`). The system stores and retrieves multi-type memory (textual, preference, activation), then injects retrieved context into prompts before response generation. It also includes asynchronous scheduler pipelines that process query/answer events into updated working memory and logs. The delivered outcome is a memory-augmented assistant stack rather than a standalone agent app.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph, CrewAI, AutoGen, or LlamaIndex as its primary runtime framework; orchestration is mostly **custom** Python classes and queues. The core LLM abstraction is an internal `LLMFactory` that dispatches to backends like OpenAI/Azure/Ollama/HuggingFace/VLLM (`src/memos/llms/factory.py:17-40`).

There are two “agentic” layers. First, `DeepSearchMemAgent` explicitly composes specialized sub-agents (`QueryRewriter`, `ReflectionAgent`) and runs an iterative retrieval/reflection loop before final generation (`src/memos/mem_agent/deepsearch_agent.py:53-223`). Second, the memory scheduler is a handler graph over task labels (`QUERY`, `MEM_UPDATE`, `ADD`, etc.) that routes and parallelizes processing with `SchedulerDispatcher` + `SchedulerHandlerRegistry` (`src/memos/mem_scheduler/task_schedule_modules/registry.py:33-55`, `src/memos/mem_scheduler/task_schedule_modules/dispatcher.py:646-684`).

The “intelligence” lives in prompt templates and task logic: query rewrite/reflection/final synthesis prompts for deep-search (`src/memos/templates/mem_agent_prompts.py`), CoT decomposition/synthesis prompts in `MOS` (`src/memos/mem_os/main.py:157-199`, `349-399`), and retrieval-trigger/working-memory update logic in scheduler handlers (`src/memos/mem_scheduler/task_schedule_modules/handlers/memory_update_handler.py:201-277`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) + event-driven workflow**.

- Manager-worker: `DeepSearchMemAgent` acts as manager; it calls `QueryRewriter`, performs retrieval, then asks `ReflectionAgent` whether to continue/stop/refine (`src/memos/mem_agent/deepsearch_agent.py:168-210`).
- Event-driven workflow: scheduler dispatches messages by label to handlers, and handlers enqueue follow-up messages (e.g., query -> memory update), forming a task pipeline (`src/memos/mem_scheduler/task_schedule_modules/dispatcher.py:657-684`, `src/memos/mem_scheduler/task_schedule_modules/handlers/query_handler.py:51-64`).

Example control flow 1 (agent loop):

```169:199:src/memos/mem_agent/deepsearch_agent.py
current_query = self.query_rewriter.run(query, history)
for iteration in range(self.max_iterations):
    search_results = self._perform_memory_search(current_query, ...)
    if search_results:
        context_batch = [self._extract_context_from_memory(mem) for mem in search_results]
        reflection_result = self.reflector.run(current_query, context_batch)
        status = reflection_result.get("status", "sufficient")
        if status == "sufficient":
            ...
        elif status == "missing_info":
            ...
```

Example control flow 2 (scheduler chaining):

```51:64:src/memos/mem_scheduler/task_schedule_modules/handlers/query_handler.py
update_msg = ScheduleMessageItem(
    user_id=msg.user_id,
    mem_cube_id=msg.mem_cube_id,
    label=MEM_UPDATE_TASK_LABEL,
    content=msg.content,
    ...
)
mem_update_messages.append(update_msg)

if mem_update_messages:
    self.scheduler_context.services.submit_messages(messages=mem_update_messages)
```

## 4. Tools & External Integrations

- **LLM providers**: OpenAI/Azure/Ollama/HuggingFace/VLLM/Qwen/DeepSeek/Minimax via `LLMFactory` (`src/memos/llms/factory.py:20-31`).
- **Vector stores**: Qdrant and Milvus through `VecDBFactory` (`src/memos/vec_dbs/factory.py:12-23`).
- **Graph databases**: Neo4j (enterprise/community), PolarDB, Postgres through `GraphStoreFactory` (`src/memos/graph_dbs/factory.py:14-27`).
- **Internet retrieval for RAG**: Google Custom Search, Tavily, Xinyu, Bocha retrievers (`src/memos/memories/textual/tree_text_memory/retrieve/internet_retriever_factory.py:20-95`).
- **FastAPI service layer**: REST/SSE APIs for chat/search/add/scheduler/memory ops (`src/memos/api/routers/server_router.py:63-453`).
- **Scheduler queue infra**: local/Redis-backed scheduling and threaded dispatch (`src/memos/mem_scheduler/task_schedule_modules/dispatcher.py`, `src/memos/mem_scheduler/task_schedule_modules/redis_queue.py`).
- **Filesystem/document ingestion**: recursive document loading (`.txt/.pdf/.json/.md/.ppt/.pptx`) in core add flow (`src/memos/mem_os/core.py:233-249`, `894-905`).

## 5. Notable Code Walkthrough

- `src/memos/mem_agent/deepsearch_agent.py:121-223` - Defines the explicit multi-agent deep-search pipeline (rewrite -> retrieve -> reflect -> iterate/finalize), the clearest MAS-style runtime in the repo.
- `src/memos/mem_os/core.py:251-352` - Main chat path: searches memory across cubes, builds memory-augmented system prompt, calls chat LLM, and pushes scheduler events.
- `src/memos/mem_scheduler/task_schedule_modules/dispatcher.py:646-684` - Central event dispatcher that groups messages and routes them to label-specific handlers; this is the backbone of async orchestration.
- `src/memos/mem_scheduler/task_schedule_modules/handlers/memory_update_handler.py:201-277` - Implements retrieval-trigger logic and working-memory replacement from query history; key to continuous memory adaptation.
- `src/memos/memories/textual/tree_text_memory/retrieve/internet_retriever_factory.py:20-95` - Shows how web retrieval backends are wired into memory retrieval, enabling external-knowledge augmentation.

## 6. Use-Case Mapping

The assigned label `RAG + Agents` is largely accurate, but this codebase leans heavily toward **workflow automation around memory operations**. RAG behavior is concrete: query-time retrieval from textual memory + optional internet retrievers + prompt injection (`src/memos/mem_os/core.py:292-333`, `src/memos/mem_scheduler/memory_manage_modules/search_pipeline.py:57-88`). Agentic behavior exists in `DeepSearchMemAgent` (multiple coordinated roles) and in CoT decomposition/sub-question answering pipelines (`src/memos/mem_agent/deepsearch_agent.py:53-223`, `src/memos/mem_os/main.py:349-513`). Overall, it fits `RAG + Agents`, but for strict downstream bucketing this repo can also be reasonably categorized as `Workflow Automation` because scheduler-driven task choreography is central.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear separation between memory OS core, scheduler, and agent modules (`core`, `main`, `mem_scheduler`, `mem_agent`).
  - Supports many production-facing backends (LLM, vector DB, graph DB, web retrieval).
  - Explicit multi-step deep-search loop with reflection-based stopping criteria.
  - Event-driven scheduler architecture is extensible through handler registry and labels.
  - Includes substantial tests across memory, scheduler, API, and backend adapters.

- **Limitations:**
  - Multi-agent runtime is narrow: primarily one deep-search agent composition, not a broad multi-agent ecosystem.
  - Some logic appears rough/duplicated (e.g., duplicate `_generate_final_answer` definitions in `deepsearch_agent.py`).
  - Heavy complexity in scheduler/handlers can increase debugging and operational burden.
  - Several integrations are partially implemented or TODO-backed (e.g., bing mapped to google retriever).
  - Agent decisions are prompt-driven without robust formal state guarantees (no typed graph/state-machine framework).

- **Research relevance:**
  - Evidence of practical hybrid architecture: LLM prompting + persistent memory + async event pipelines.
  - Useful case for studying memory lifecycle orchestration in agent systems (query, update, feedback, reorganize loops).
  - Demonstrates lightweight hierarchical multi-agent pattern (rewriter/reflector/orchestrator) without external frameworks.
  - Shows industry-style integration breadth (APIs, queues, DBs, retrieval) for deployable agent-memory systems.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
