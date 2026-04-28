---
repo_name: vstorm-co/memv
url: "https://github.com/vstorm-co/memv"
stars: 72
forks: 11
contributors_count: 3
last_commit_date: "2026-04-07T21:37:52+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 4
architecture_labels: [LangGraph, AutoGen, CrewAI]
use_case_labels: [RAG + Agents]
generated_at: "2026-04-27T15:55:29.596688+00:00"
model: auto
duration_s: 100.1
clone_size_kb: 2249
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`memv` is a Python library that gives AI applications a structured long-term memory layer: it ingests chat messages, segments them into episodes, extracts durable user facts, and retrieves relevant facts later for prompt injection. A developer runs it as an async `Memory` service in their app (`add_exchange`, `process`, `retrieve`), or via example CLIs and a Textual dashboard. The core problem it solves is turning noisy conversation logs into high-value, temporally-aware knowledge (including fact updates/contradictions). In practice, users get per-user hybrid retrieval (vector + text), temporal filtering, and automatic memory maintenance across sessions.

## 2. Agent Framework & Architecture

The core runtime is **custom orchestration**, not LangGraph/AutoGen/CrewAI. In source, the LLM abstraction is a protocol plus a `PydanticAIAdapter` that wraps `pydantic_ai.Agent` calls for text/structured outputs (`src/memv/llm/pydantic_ai.py:10-41`). The main system is wired in `LifecycleManager` + `Pipeline` (`src/memv/memory/_lifecycle.py:169-220`, `src/memv/memory/_pipeline.py:34-219`), not a framework graph.

Architecture is a staged async memory pipeline:
1) messages stored,  
2) segmented into episodes (`BatchSegmenter`),  
3) episode narrative generated (`EpisodeGenerator`),  
4) existing knowledge retrieved (`Retriever`),  
5) novel facts extracted via predict-calibrate (`PredictCalibrateExtractor`),  
6) dedup/supersede handling + index writes.

The “intelligence” primarily lives in prompt templates (`src/memv/processing/prompts.py:16-513`) and in the predict-calibrate logic (`src/memv/processing/extraction.py:34-137`), not in multiple interacting runtime agents.

## 3. Orchestration Pattern

Closest match: **sequential pipeline with asynchronous batching/concurrency** (“other” rather than MAS). Control flow is deterministic stage-by-stage in `Pipeline.process()` and `_process_episode()`.

Example control flow (episode processing loop):
- `src/memv/memory/_pipeline.py:155-167`
```python
existing = await self._lc.retriever.retrieve(
    query=f"{episode.title} {episode.content}",
    user_id=user_id,
    top_k=self._lc.max_statements_for_prediction,
)
extracted = await self._lc.extractor.extract(
    episode=episode,
    existing_knowledge=existing.retrieved_knowledge,
)
```

Example orchestration setup (components assembled once):
- `src/memv/memory/_lifecycle.py:207-219`
```python
self.segmenter = BatchSegmenter(llm_client=self.llm, ...)
self.episode_generator = EpisodeGenerator(self.llm)
if self.enable_episode_merging:
    self.episode_merger = EpisodeMerger(...)
self.extractor = PredictCalibrateExtractor(self.llm)
```

This is not planner-worker/swarm behavior; it is one pipeline over memory objects.

## 4. Tools & External Integrations

- **LLM provider abstraction via PydanticAI**: `pydantic_ai.Agent` used for `generate` and `generate_structured` (`src/memv/llm/pydantic_ai.py:5-41`).
- **Embedding APIs**:
  - OpenAI embeddings (`src/memv/embeddings/openai.py:1-22`)
  - Cohere embeddings (`src/memv/embeddings/cohere.py:1-26`)
  - Voyage embeddings (`src/memv/embeddings/voyage.py:1-26`)
  - Local FastEmbed model (`src/memv/embeddings/fastembed.py:1-27`)
- **Vector stores / ANN**:
  - SQLite path: `sqlite-vec` virtual table (`src/memv/storage/sqlite/_vector_index.py:1-189`)
  - Postgres path: `pgvector` with HNSW index (`src/memv/storage/postgres/_vector_index.py:84-98`)
- **Text search**:
  - SQLite FTS5 (`src/memv/storage/sqlite/_text_index.py:1-146`)
  - Postgres `tsvector` + GIN (`src/memv/storage/postgres/_text_index.py:61-71`)
- **Hybrid RAG retrieval**: RRF fusion of vector + BM25/FTS (`src/memv/retrieval/retriever.py:96-170`).
- **UI integration**: Textual dashboard for browsing and triggering processing (`src/memv/dashboard/app.py:74-476`).
- **No browser automation/MCP/shell-tool agent calls** in core runtime.

## 5. Notable Code Walkthrough

- `src/memv/memory/_pipeline.py:34-219` - Core orchestrator. Processes unprocessed messages, runs segmentation/generation/extraction, applies temporal backfill + confidence filter, deduplicates and indexes knowledge.
- `src/memv/processing/extraction.py:34-137` - Implements the predict-calibrate mechanism (predict expected facts from KB, then extract only missed/novel facts from raw messages).
- `src/memv/retrieval/retriever.py:37-170` - Retrieval engine with query embedding, vector+text search, reciprocal rank fusion, and temporal validity filtering.
- `src/memv/memory/_lifecycle.py:169-243` - Dependency wiring and backend initialization (sqlite/postgres stores, retriever, segmenter, extractor, episode merger).
- `src/memv/processing/prompts.py:240-441` - High-leverage prompt definitions encoding extraction quality rules, exclusions, and structured output schema; this strongly determines behavior quality.

## 6. Use-Case Mapping

The repository does implement a **RAG memory subsystem for agents**: it retrieves prior user knowledge and formats it for prompt context (`retrieve(...).to_prompt()`), and continuously updates memory from dialogue (`src/memv/memory/memory.py:189-245`). However, it does **not** implement multiple coordinated LLM agents at runtime; it is an infrastructure layer consumed by external agents/apps. The `examples/` folder shows integrations into LangGraph, AutoGen, CrewAI, and LlamaIndex (`examples/langgraph_agent.py:64-151`, `examples/autogen_agent.py:45-131`), but these are demos around `memv`, not the core architecture itself. So the upstream label “RAG + Agents” is directionally related, but the core repo is closer to a **workflow-oriented memory automation component**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Predict-calibrate extraction is explicit and well-implemented, reducing redundant memory writes (`src/memv/processing/extraction.py:67-137`).
  - Strong temporal modeling (valid/invalid time + expired/current) propagated into retrieval (`src/memv/retrieval/retriever.py:125-140`).
  - Practical hybrid retrieval with RRF over vector + text search (`src/memv/retrieval/retriever.py:142-170`).
  - Backend flexibility (SQLite + Postgres, FTS + vector index) with user-level isolation built in (`src/memv/storage/sqlite/_vector_index.py:33-45`).
  - Prompt rules are unusually detailed for extraction quality and source attribution (`src/memv/processing/prompts.py:65-131`).

- **Limitations:**
  - No true multi-agent coordination in core runtime (no planner-worker/swarm/agent graph in `src/memv`).
  - LLM outputs are parsed with fallback heuristics; malformed JSON can degrade segmentation/episode quality (`src/memv/processing/batch_segmenter.py:134-167`, `src/memv/processing/episodes.py:87-114`).
  - Quality gate is mostly confidence-threshold based in code (`src/memv/memory/_pipeline.py:221-227`), so behavior relies heavily on prompt adherence.
  - Intra-batch duplicate suppression is acknowledged as stale-KB risk; dedup is post-hoc (`src/memv/memory/_pipeline.py:61-63`).
  - Dashboard search path is simplistic substring matching, not full retriever parity (`src/memv/dashboard/app.py:277-301`).

- **Research relevance:**
  - Useful evidence for “memory as pipeline” designs for agent personalization rather than monolithic chat history.
  - Concrete implementation of bi-temporal memory retrieval in LLM systems.
  - Demonstrates prompt-governed knowledge extraction with explicit exclusion rules and structured outputs.
  - Good case study for hybrid retrieval + memory dedup/update handling in long-lived assistant systems.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
