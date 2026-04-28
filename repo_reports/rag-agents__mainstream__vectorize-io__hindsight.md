---
repo_name: vectorize-io/hindsight
url: "https://github.com/vectorize-io/hindsight"
stars: 10242
forks: 613
contributors_count: 72
last_commit_date: "2026-04-22T21:28:31+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T09:45:56.865578+00:00"
model: auto
duration_s: 115.7
clone_size_kb: 149852
uses_mas: no
final_use_case: RAG + Agents
---
## 1. Overview

`vectorize-io/hindsight` is primarily a **memory backend for LLM apps/agents**, not an end-user chatbot by itself. A user typically runs the FastAPI service (`hindsight-api-slim`) and then calls `retain`, `recall`, and `reflect` via HTTP/MCP/SDK to store interactions, retrieve relevant memories, and synthesize answers. Under the hood it combines extraction, embeddings, graph links, and reranking over PostgreSQL/pgvector so memory remains queryable and structured over time. The repo also ships many framework adapters (LangGraph, CrewAI, AutoGen, etc.) so external agents can plug into the same memory engine. The output users get is persistent, queryable long-term memory and optional agentic “reflection” responses grounded in that memory.

## 2. Agent Framework & Architecture

Core runtime is **custom agent infrastructure**, not LangGraph/CrewAI/AutoGen as the main engine. The central class is `MemoryEngine` (`hindsight-api-slim/hindsight_api/engine/memory_engine.py:346+`), which implements retain/recall/reflect pipelines directly. The only true “agent loop” in core is reflect: `reflect_async()` calls `run_reflect_agent()` with tool callbacks (`memory_engine.py:5694-5963`).

The reflect agent itself is a custom iterative tool-calling loop (`hindsight-api-slim/hindsight_api/engine/reflect/agent.py:309-984`) with forced early tool order, evidence validation, and a `done` tool for final answer. It is not a graph framework node state machine; it is a manual loop over iterations with tool execution and message history management.

Frameworks like LangGraph and CrewAI are present as **integration packages**, not as orchestration backbone of Hindsight core, e.g. LangGraph helper nodes in `hindsight-integrations/langgraph/hindsight_langgraph/nodes.py:41-247` and CrewAI `BaseTool` wrappers in `hindsight-integrations/crewai/hindsight_crewai/tools.py:30-125`.

## 3. Orchestration Pattern

Closest match: **Other (single-agent tool loop + parallel retrieval pipeline)**.

- Reflect uses a single LLM agent that iterates tool calls, not multiple cooperating agents:
  - `reflect/agent.py:443-569` shows per-iteration loop and forced tool sequence.
  - `reflect/agent.py:870-883` executes tool calls in parallel per iteration.
- Recall is a parallel retrieval workflow (semantic/BM25/graph/temporal) rather than agent-to-agent coordination:
  - `search/retrieval.py:564-690` runs batched retrieval and `asyncio.gather` for graph retrieval across fact types.

Short excerpt (`hindsight-api-slim/hindsight_api/engine/reflect/agent.py:557-568`):
```python
forced_sequence = []
if has_mental_models:
    forced_sequence.append("search_mental_models")
if include_observations:
    forced_sequence.append("search_observations")
if include_recall:
    forced_sequence.append("recall")

if iteration < len(forced_sequence):
    iter_tool_choice = {"type": "function", "function": {"name": forced_sequence[iteration]}}
```

Short excerpt (`hindsight-api-slim/hindsight_api/engine/search/retrieval.py:689-691`):
```python
graph_tasks = [run_graph_for_fact_type(ft) for ft in fact_types]
graph_results_list = await asyncio.gather(*graph_tasks)
```

## 4. Tools & External Integrations

- **LLM providers/APIs**: OpenAI-compatible, Anthropic, Gemini/Vertex, LiteLLM, Bedrock, local/mock/none (`hindsight-api-slim/hindsight_api/engine/llm_wrapper.py:142-260`).
- **Vector + relational store**: PostgreSQL + pgvector queries/index-aware retrieval (`hindsight-api-slim/hindsight_api/engine/search/retrieval.py:104-203`, `344-390`).
- **Embedding backends**: local SentenceTransformers, remote TEI, OpenAI/Cohere/Gemini/LiteLLM embeddings (`hindsight-api-slim/hindsight_api/engine/embeddings.py:48-240`).
- **Reranking backends**: local cross-encoder, TEI, other providers via configurable reranker abstraction (`hindsight-api-slim/hindsight_api/engine/cross_encoder.py:61-220`).
- **MCP server/tool surface**: FastMCP server exposing `retain`, `recall`, `reflect`, bank/document ops (`hindsight-api-slim/hindsight_api/api/mcp.py:80-157`; tool registration in `hindsight-api-slim/hindsight_api/mcp_tools.py:195-249`, `529-884`).
- **Framework adapters**: LangGraph nodes (`hindsight-integrations/langgraph/hindsight_langgraph/nodes.py:41-247`), CrewAI tools (`hindsight-integrations/crewai/hindsight_crewai/tools.py:30-125`), plus additional integration packages in repo (AutoGen/OpenAI-agents/LlamaIndex/etc).

## 5. Notable Code Walkthrough

- `hindsight-api-slim/hindsight_api/engine/memory_engine.py:2522-3009` - Core `recall_async` path: query embedding, parallel retrieval, merge/rerank/token filtering orchestration; this is the heart of memory retrieval quality/latency.
- `hindsight-api-slim/hindsight_api/engine/reflect/agent.py:309-984` - Custom reflect agent loop with tool-calling, guardrails, context-budget handling, and final synthesis.
- `hindsight-api-slim/hindsight_api/engine/retain/orchestrator.py:383-427, 821-1433` - Retain ingestion pipeline: fact extraction + embeddings + transactional writes + streaming mini-batches + final ANN link pass.
- `hindsight-api-slim/hindsight_api/engine/search/retrieval.py:91-275, 564-744` - Multi-strategy retrieval and parallelization across fact types; defines semantic/BM25/graph/temporal retrieval composition.
- `hindsight-api-slim/hindsight_api/api/mcp.py:80-156, 280-453` - MCP transport/auth/multi-bank routing and tool registration, showing how agents from external clients access memory operations.

## 6. Use-Case Mapping

This repo strongly fits **RAG + Agents** as a memory-centric retrieval-and-reasoning subsystem: retain builds a structured memory graph; recall performs multi-strategy retrieval/reranking; reflect runs an agentic tool loop over recalled evidence (`memory_engine.py:2549-2557`, `5718-5728`). It is not a standalone multi-agent society; rather it enables agent applications to maintain long-term memory and do grounded reasoning. The upstream “Workflow Automation” label is partially true for some integrations, but the core product behavior is best categorized as **RAG + Agents**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong retrieval stack combining semantic, BM25, graph, and temporal methods in parallel (`search/retrieval.py:564-744`).
  - Production-oriented retain pipeline with streaming batching, recovery, and concurrency safeguards (`retain/orchestrator.py:821-1433`).
  - Clear memory abstractions (facts/entities/links/mental models) with explicit APIs (`memory_engine.py`, `api/http.py`).
  - Rich integration surface (MCP + multiple agent frameworks), making it broadly usable in real agent ecosystems.
  - Reflect loop includes practical guardrails (tool hallucination rejection, evidence checks, context-overflow handling) (`reflect/agent.py:831-866`, `776-804`, `495-540`).

- **Limitations:**
  - Core runtime is mostly **single-agent** during reasoning; no native multi-agent coordination protocol.
  - Very large, dense orchestrator/engine modules raise complexity and maintenance risk (`memory_engine.py`, `retain/orchestrator.py`).
  - Heavy dependence on DB/embedding/index tuning for quality and performance; harder to run optimally without infra expertise.
  - Reflect quality depends on tool-calling reliability and provider behavior; substantial normalization/defensive code suggests model variance.
  - Some framework “agentic” capabilities live in adapters, not in a unified first-class multi-agent runtime in core.

- **Research relevance:**
  - Good evidence for **agent memory architecture engineering** (long-term memory storage, retrieval fusion, consolidation primitives).
  - Useful case study in **tool-augmented single-agent orchestration** with practical safety/robustness patterns.
  - Demonstrates real-world **memory-augmented RAG** design beyond simple vector search.
  - Valuable for studying **interoperability layer design** across MCP and agent frameworks.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: RAG + Agents
