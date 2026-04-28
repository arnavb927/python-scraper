---
repo_name: jamwithai/production-agentic-rag-course
url: "https://github.com/jamwithai/production-agentic-rag-course"
stars: 5716
forks: 1361
contributors_count: 5
last_commit_date: "2026-04-05T06:13:53+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 8
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents]
generated_at: "2026-04-27T09:54:54.904194+00:00"
model: auto
duration_s: 85.2
clone_size_kb: 20844
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a production-style **arXiv paper curator** service that exposes a FastAPI backend (and optional Telegram bot) for RAG-based question answering over CS/AI/ML papers. A user typically runs the API app and calls endpoints like `/api/v1/ask-agentic`, which triggers an “agentic RAG” workflow rather than a single-shot retrieval+generate call (`src/main.py:106-122`, `src/routers/agentic_ask.py:8-58`). The system retrieves paper chunks from OpenSearch, uses an LLM to validate scope, grade relevance, potentially rewrite the query, and then generate an answer with sources (`src/services/agents/agentic_rag.py:75-160`, `src/services/agents/nodes/*.py`). In practice, the output is a structured response containing answer text, sources, reasoning steps, and retrieval-attempt metadata (`src/services/agents/agentic_rag.py:319-328`).

## 2. Agent Framework & Architecture

The code **actually uses LangGraph + LangChain Core**, not CrewAI/AutoGen/LlamaIndex. Evidence: imports of `StateGraph`, `ToolNode`, `tools_condition`, `Runtime`, and LangChain message/tool primitives (`src/services/agents/agentic_rag.py:5-8`, `src/services/agents/state.py:3-4`, `src/services/agents/tools.py:3-4`).

Architecture-wise, this is a **graph-orchestrated agentic RAG pipeline** implemented in `AgenticRAGService`. The “intelligence” is distributed across role-specific node prompts and structured outputs: guardrail scoring, document grading, query rewriting, and final answer generation (`src/services/agents/prompts.py:1-117`, `src/services/agents/models.py:6-109`, `src/services/agents/nodes/*.py`). A retrieval tool (`retrieve_papers`) is injected into a LangGraph `ToolNode`, so the graph alternates between LLM decision nodes and tool execution (`src/services/agents/agentic_rag.py:88-105`, `src/services/agents/tools.py:27-85`).

It is not a manager coordinating independent long-lived “assistant personas”; instead, it is a multi-step control graph with specialized LLM tasks. So this is agentic orchestration with multiple coordinated decision stages, but implemented as one compiled workflow object (`src/services/agents/agentic_rag.py:71-73`, `src/services/agents/agentic_rag.py:282-286`).

## 3. Orchestration Pattern

Closest match: **graph (LangGraph-style state machine)** with conditional routing and loops.

Control flow is explicit in graph edges:
- `START -> guardrail`
- Guardrail routes to `retrieve` or `out_of_scope`
- Retrieval goes through `ToolNode`
- Grading routes to `generate_answer` or `rewrite_query`
- Rewrite loops back to retrieval (`src/services/agents/agentic_rag.py:110-153`).

Example excerpt (routing + loop):
`src/services/agents/agentic_rag.py:114-121`, `src/services/agents/agentic_rag.py:140-150`
```python
workflow.add_conditional_edges(
    "guardrail",
    continue_after_guardrail,
    {"continue": "retrieve", "out_of_scope": "out_of_scope"},
)
workflow.add_conditional_edges(
    "grade_documents",
    lambda state: state.get("routing_decision", "generate_answer"),
    {"generate_answer": "generate_answer", "rewrite_query": "rewrite_query"},
)
workflow.add_edge("rewrite_query", "retrieve")
```

Example excerpt (tool-call handoff):
`src/services/agents/nodes/retrieve_node.py:93-104`
```python
updates["messages"] = [
    AIMessage(
        content="",
        tool_calls=[{"id": f"retrieve_{new_attempt_count}",
                     "name": "retrieve_papers",
                     "args": {"query": question}}],
    )
]
```

## 4. Tools & External Integrations

- **LLM runtime (Ollama local API)**: LLM calls for guardrail, grading, rewriting, and answer generation are created via `OllamaClient.get_langchain_model(...)` and direct Ollama HTTP endpoints (`src/services/agents/nodes/guardrail_node.py:84-95`, `src/services/agents/nodes/generate_answer_node.py:83-91`, `src/services/ollama/client.py:81-141`).
- **Vector/semantic embeddings (Jina API)**: query embeddings generated through Jina for retrieval (`src/services/agents/tools.py:45-57`, `src/services/embeddings/jina_client.py:70-87`).
- **Vector + keyword retrieval store (OpenSearch)**: unified BM25/vector/hybrid retrieval, including RRF pipeline support (`src/services/agents/tools.py:50-57`, `src/services/opensearch/client.py:181-212`, `src/services/opensearch/client.py:249-291`).
- **LangGraph ToolNode integration**: `retrieve_papers` tool wrapped with `@tool` and executed via `ToolNode` (`src/services/agents/tools.py:27-85`, `src/services/agents/agentic_rag.py:102`).
- **Observability (Langfuse)**: trace/span instrumentation and callback integration for graph execution and node-level telemetry (`src/services/agents/agentic_rag.py:190-220`, `src/services/langfuse/client.py:11-79`).
- **Delivery channels**: FastAPI endpoint `/ask-agentic` and an optional Telegram bot interface (`src/routers/agentic_ask.py:8-58`, `src/services/telegram/bot.py:32-47`).
- **No browser/MCP/shell agents**: no Browserbase/Playwright/MCP orchestration found in source.

## 5. Notable Code Walkthrough

- `src/services/agents/agentic_rag.py:75-160` - Builds the full LangGraph workflow, defines nodes/edges, and compiles the graph; this is the core orchestration engine.
- `src/services/agents/nodes/guardrail_node.py:16-37` - Implements initial gating logic (`continue` vs `out_of_scope`) based on LLM-scored domain relevance and threshold.
- `src/services/agents/nodes/grade_documents_node.py:83-153` - Uses structured LLM grading to decide whether retrieved context is good enough or whether query rewriting should occur.
- `src/services/agents/tools.py:12-85` - Defines `retrieve_papers` as a LangChain tool that combines Jina embeddings + OpenSearch hybrid search and returns `Document` objects.
- `src/routers/agentic_ask.py:8-53` - Wires the compiled agentic service into a user-facing API endpoint with response schema including reasoning steps and retrieval attempts.

## 6. Use-Case Mapping

Despite the upstream “Code Generation” assignment, this repository is **primarily RAG-driven workflow automation for research Q&A**, not code synthesis. The runtime behavior is: classify scope -> retrieve -> evaluate -> optionally rewrite -> regenerate, all over arXiv paper chunks (`src/services/agents/agentic_rag.py:110-153`, `src/services/agents/nodes/*.py`). There is no substantial code-writing agent loop (no repo-editing tools, code-execution planning, or coding benchmarks).  
A better fit is **Workflow Automation** (with strong RAG + Agents characteristics), because the key innovation is adaptive control flow over retrieval quality, not code output generation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, inspectable graph-based control flow with explicit conditional routing and retry loop (`src/services/agents/agentic_rag.py:110-153`).
  - Strong typed state/context patterns for LangGraph runtime and dependency injection (`src/services/agents/state.py:9-72`, `src/services/agents/context.py:11-40`).
  - Practical production integration: OpenSearch hybrid retrieval + Jina embeddings + Ollama + Langfuse tracing (`src/services/agents/tools.py:12-85`, `src/services/langfuse/client.py:11-79`).
  - Graceful fallbacks when LLM grading/rewriting fails, preventing brittle runtime behavior (`src/services/agents/nodes/grade_documents_node.py:117-127`, `src/services/agents/nodes/rewrite_query_node.py:105-111`).

- **Limitations:**
  - “Multi-agent” is role-simulated via prompts/nodes, not independent autonomous agent entities with separate memories/goals.
  - Source extraction utilities appear partially stubbed (`extract_sources_from_tool_messages` currently `pass`) which may limit provenance fidelity (`src/services/agents/nodes/utils.py:19-27`).
  - Guardrail and grading both depend on same underlying model family, risking correlated failure modes on ambiguous queries (`src/services/agents/nodes/guardrail_node.py:84-95`, `src/services/agents/nodes/grade_documents_node.py:92-103`).
  - Domain is hard-scoped to CS/AI/ML arXiv; out-of-domain usefulness is intentionally constrained (`src/services/agents/prompts.py:78-97`, `src/services/agents/nodes/out_of_scope_node.py:32-41`).

- **Research relevance:**
  - Good example of **graph-based adaptive RAG orchestration** with controllable transitions and retries.
  - Useful evidence for studying **LLM-in-the-loop routing decisions** (guardrail + grading + rewrite) in production pipelines.
  - Demonstrates practical **observability integration** (Langfuse spans/callbacks) in agentic workflows.
  - Shows a middle-ground pattern between single-shot RAG and fully decentralized multi-agent swarms.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
