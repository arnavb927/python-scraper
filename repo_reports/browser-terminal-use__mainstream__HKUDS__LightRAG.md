---
repo_name: HKUDS/LightRAG
url: "https://github.com/HKUDS/LightRAG"
stars: 34095
forks: 4825
contributors_count: 266
last_commit_date: "2026-04-19T10:18:15+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 8
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T06:44:55.316551+00:00"
model: auto
duration_s: 94.8
clone_size_kb: 21160
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`HKUDS/LightRAG` is primarily a graph-enhanced RAG framework: users instantiate `LightRAG`, initialize storages, insert documents, and query via modes like `local`, `global`, `hybrid`, `mix`, or `naive` (`lightrag/lightrag.py:210-240`, `lightrag/lightrag.py:2622-2935`). In practice, you can run it as a Python library or through its FastAPI server endpoints such as `/query` and `/documents/*` (`lightrag/api/routers/query_routes.py:16-143`, `lightrag/api/routers/document_routes.py:80-103`). The system builds/uses entity-relation graphs plus vector retrieval, then generates responses with configurable LLM backends (`lightrag/operate.py:3164-3317`). It also includes an explicit multi-agent demo where AG2 agents collaborate over LightRAG as a shared tool (`examples/lightrag_ag2_multiagent_demo.py:27-33`, `examples/lightrag_ag2_multiagent_demo.py:205-241`).

## 2. Agent Framework & Architecture

Frameworks actually present in code:
- **Core runtime:** custom LightRAG orchestration (not LangGraph/CrewAI/AutoGen).
- **Multi-agent example:** **AG2/AutoGen** (`from autogen import AssistantAgent, GroupChat, GroupChatManager...`) in `examples/lightrag_ag2_multiagent_demo.py:27-33`.
- **Other frameworks:** limited integration points only (e.g., `llama_index` adapter file and LangChain usage in evaluation scripts), not the main orchestration path (`lightrag/llm/llama_index_impl.py:2-15`, `lightrag/evaluation/eval_rag_quality.py:93`).

The core architecture centers on one orchestrator class, `LightRAG`, which routes indexing and query flows into retrieval functions (`kg_query`, `naive_query`) plus storage backends (`lightrag/lightrag.py:88-95`, `lightrag/lightrag.py:2813-2838`, `lightrag/lightrag.py:2911-2934`). Intelligence in the core mostly lives in prompt templates and retrieval logic: keyword extraction, entity/relation extraction, context building, reranking, and final generation (`lightrag/operate.py:2883-2970`, `lightrag/operate.py:3164-3250`).

The repo does implement coordinated multiple LLM agents at runtime in the AG2 demo: a `Researcher`, `Analyst`, and `Writer` are coordinated via a `GroupChatManager`, with explicit transition constraints and shared `lightrag_query` tool usage (`examples/lightrag_ag2_multiagent_demo.py:121-155`, `examples/lightrag_ag2_multiagent_demo.py:212-237`).

## 3. Orchestration Pattern

Closest match: **hierarchical / manager-worker** (in the multi-agent part), plus a **custom sequential/async pipeline** (core RAG engine).

In the AG2 example, the manager enforces staged handoff (`Researcher -> Analyst -> Writer`) rather than peer swarm behavior:

```287:295:examples/lightrag_ag2_multiagent_demo.py
allowed_transitions = {
    user_proxy: [researcher],
    researcher: [user_proxy, analyst],
    analyst: [user_proxy, writer],
    writer: [],
}
group_chat = GroupChat(..., speaker_transitions_type="allowed")
manager = GroupChatManager(groupchat=group_chat, ...)
```

In the core library, query orchestration is mode-routed and sequential: `aquery_llm` dispatches to `kg_query` or `naive_query`, then returns structured output + LLM response:

```2911:2929:lightrag/lightrag.py
if param.mode in ["local", "global", "hybrid", "mix"]:
    query_result = await kg_query(...)
elif param.mode == "naive":
    query_result = await naive_query(...)
elif param.mode == "bypass":
    use_llm_func = param.model_func or global_config["llm_model_func"]
```

## 4. Tools & External Integrations

- **LLM APIs/providers** (OpenAI, Azure OpenAI, Gemini, Anthropic, Bedrock, Ollama, etc.) are wired in provider modules under `lightrag/llm/` (`lightrag/llm/openai.py:14-18`, `lightrag/llm/openai.py:111-137` and sibling files like `anthropic.py`, `gemini.py`, `bedrock.py`, `ollama.py`).
- **Vector/graph/document stores** are pluggable across JSON/NetworkX, Neo4j, PostgreSQL, Redis, MongoDB, OpenSearch, Milvus, Qdrant, Faiss, Memgraph (`lightrag/kg/__init__.py:1-45`, `lightrag/kg/__init__.py:113-140`).
- **Knowledge extraction pipeline** as callable “tooling” inside the framework: entity/relation extraction and KG retrieval (`lightrag/operate.py:2883-2970`, `lightrag/operate.py:3164-3250`, `lightrag/operate.py:4953-5003`).
- **HTTP API integration** via FastAPI (`lightrag/api/lightrag_server.py:5-57`) and route modules (`lightrag/api/routers/query_routes.py:193-200`).
- **Document parsing adjuncts** (e.g., optional `docling`) for ingestion (`lightrag/api/routers/document_routes.py:37-53`).
- **Notably absent for “Browser/Terminal use”**: no first-class Playwright/Selenium/browser automation or shell-execution agent loop in core runtime.

## 5. Notable Code Walkthrough

- `lightrag/lightrag.py:1740-1889` — Main async ingestion pipeline (`apipeline_process_enqueue_documents`) controlling queueing, locking, cancellation, and bounded concurrency.
- `lightrag/operate.py:2883-2970` — Entity/relation extraction from chunks using prompt-driven LLM calls with caching and gleaning passes.
- `lightrag/operate.py:3164-3317` — KG query path: keyword extraction, context construction, prompt assembly, cache lookup, and model invocation.
- `lightrag/kg/__init__.py:1-45` — Central registry of supported storage classes and required method contracts; this defines LightRAG’s backend portability.
- `examples/lightrag_ag2_multiagent_demo.py:111-241` — Representative multi-agent orchestration using AG2 agents plus LightRAG as a shared tool, with explicit transition policy.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** appears mostly inaccurate for core LightRAG. The primary codebase is a **RAG + workflow orchestration system** for document ingestion, graph/vector retrieval, and API-serving, not browser automation or terminal control (`lightrag/lightrag.py:1740-1850`, `lightrag/api/routers/query_routes.py:16-25`).  

However, because the project has explicit queue/pipeline control, background processing, and an AG2 multi-role collaboration demo, a better taxonomy is **Workflow Automation** (with strong secondary fit as RAG + Agents).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Pluggable storage architecture across many production backends (`lightrag/kg/__init__.py:1-45`).
  - Rich retrieval modes (`local/global/hybrid/mix/naive/bypass`) with shared query API (`lightrag/base.py:85-95`, `lightrag/lightrag.py:2813-2849`).
  - End-to-end async pipeline with cancellation, status tracking, and concurrency controls (`lightrag/lightrag.py:1765-1819`, `lightrag/lightrag.py:1870-1883`).
  - Built-in extraction + graph merge mechanics rather than pure vector RAG (`lightrag/operate.py:2883-2984`, `lightrag/lightrag.py:2318-2330`).
  - Demonstrated multi-agent coordination via AG2 with explicit role separation (`examples/lightrag_ag2_multiagent_demo.py:121-155`, `examples/lightrag_ag2_multiagent_demo.py:205-237`).

- **Limitations:**
  - Multi-agent orchestration is mostly example-level; core engine is single orchestrator + functions, not native MAS framework.
  - “Agent” behaviors depend heavily on prompt conventions and external model reliability; limited formal guarantees.
  - Large monolithic modules (`lightrag.py`, `operate.py`) make reasoning and extension harder.
  - Runtime dependency installation (`pipmaster`) in provider/storage modules can complicate reproducibility (`lightrag/llm/openai.py:7-13`, `lightrag/kg/neo4j_impl.py:20-24`).
  - Browser/terminal action tooling is not a first-class capability despite upstream use-case tag.

- **Research relevance:**
  - Evidence of **hybrid graph+vector RAG orchestration** in a widely used OSS system.
  - Example of **manager-constrained multi-agent collaboration** over a shared retrieval tool (`GroupChatManager` + transitions).
  - Useful case for studying tradeoffs between **single-orchestrator pipelines** and **explicit multi-agent wrappers**.
  - Practical artifact for evaluating storage-backend effects on agentic retrieval systems.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
