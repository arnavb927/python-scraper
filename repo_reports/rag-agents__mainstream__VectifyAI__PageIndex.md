---
repo_name: VectifyAI/PageIndex
url: "https://github.com/VectifyAI/PageIndex"
stars: 25653
forks: 2179
contributors_count: 11
last_commit_date: "2026-04-08T10:19:25+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T09:32:30.965669+00:00"
model: auto
duration_s: 67.2
clone_size_kb: 50108
uses_mas: no
final_use_case: RAG + Agents
---
## 1. Overview

`VectifyAI/PageIndex` is primarily a document indexing and retrieval library that builds a hierarchical structure from PDFs/Markdown without embeddings, then uses LLM calls to infer section boundaries, page indices, summaries, and document descriptions. A user typically runs `run_pageindex.py` or `PageIndexClient.index()` to process a document and persist a structured tree (with optional summaries/text) in JSON. They can then query metadata, structure, and page ranges via retrieval functions (`get_document`, `get_document_structure`, `get_page_content`). The “agentic” part in this repo is mostly shown in the example QA script, where a tool-using LLM reasons over that structure to fetch narrow page spans and answer questions.

## 2. Agent Framework & Architecture

The core package does **not** use CrewAI/LangGraph/AutoGen. The indexing pipeline is custom Python orchestration with direct `litellm` calls (`pageindex/utils.py:32-83`) and many prompt-driven transformation/verification steps in `pageindex/page_index.py`.  

Actual “agent framework” usage appears in the demo script, which imports the **OpenAI Agents SDK** (`from agents import Agent, Runner, function_tool`) and wraps PageIndex retrieval functions as tools (`examples/agentic_vectorless_rag_demo.py:30-85`). That demo constructs a **single** agent named `PageIndex`, not a multi-agent team.

Architecture-wise, there are two layers:  
1) **Indexing layer** (custom): PDF/MD parsing, TOC detection, iterative LLM extraction, verification, correction, and recursive subdivision into tree nodes (`pageindex/page_index.py:959-1111`, `pageindex/page_index_md.py:243-300`).  
2) **Retrieval/QA layer**: `PageIndexClient` persists docs and exposes retrieval endpoints (`pageindex/client.py:55-130`, `pageindex/retrieve.py:81-137`); demo agent calls these tools during QA (`examples/agentic_vectorless_rag_demo.py:62-90`).

## 3. Orchestration Pattern

Closest match: **sequential pipeline with recursive refinement** (custom orchestration), plus optional **single-agent tool-use loop** in the demo. It is not a multi-agent graph/swarm/manager-worker runtime.

Control flow in indexing is staged (`check_toc -> meta_processor -> verify/fix -> tree parsing -> recursive large-node processing`), with retries/fallback between modes:

```959:997:pageindex/page_index.py
async def meta_processor(page_list, mode=None, ...):
    if mode == 'process_toc_with_page_numbers':
        toc_with_page_number = process_toc_with_page_numbers(...)
    elif mode == 'process_toc_no_page_numbers':
        toc_with_page_number = process_toc_no_page_numbers(...)
    else:
        toc_with_page_number = process_no_toc(...)
    ...
    if accuracy > 0.6 and len(incorrect_results) > 0:
        toc_with_page_number, incorrect_results = await fix_incorrect_toc_with_retries(...)
```

The demo’s control loop is one agent repeatedly deciding when to call tools:

```81:90:examples/agentic_vectorless_rag_demo.py
agent = Agent(
    name="PageIndex",
    instructions=AGENT_SYSTEM_PROMPT,
    tools=[get_document, get_document_structure, get_page_content],
    model=client.retrieve_model,
)
async def _run():
    streamed_run = Runner.run_streamed(agent, prompt)
```

## 4. Tools & External Integrations

- **LLM API abstraction via LiteLLM**: all core inference (`llm_completion`, `llm_acompletion`) routes through `litellm.completion/acompletion` in `pageindex/utils.py:32-83`.  
- **OpenAI Agents SDK (optional demo only)**: tool-calling agent runtime in `examples/agentic_vectorless_rag_demo.py:30-33` and `:62-90`.  
- **PDF parsing**: `PyPDF2` for page extraction and counts (`pageindex/utils.py:387-429`, `pageindex/retrieve.py:46-53`), plus `pymupdf` fallback option (`pageindex/utils.py:397-410`).  
- **Filesystem-backed document store**: workspace JSON persistence (`_meta.json` + per-doc files) in `pageindex/client.py:157-219`.  
- **Environment/config loading**: `.env` via `python-dotenv` and YAML config via `ConfigLoader` (`pageindex/utils.py:13-14`, `:654-685`, `pageindex/config.yaml`).  
- **No vector DB / external search / browser automation / MCP** in core code; retrieval is from stored tree metadata and selected page content.

## 5. Notable Code Walkthrough

- `pageindex/page_index.py:959-1111` - Main PDF indexing engine. It orchestrates TOC detection/extraction, LLM-based page-index inference, validation, retries, and recursive node splitting to produce the final tree structure.
- `pageindex/utils.py:32-83` - Central LLM I/O wrapper. All prompt-based reasoning in the pipeline depends on these retrying sync/async LiteLLM calls, making this file the practical inference backbone.
- `pageindex/client.py:55-130` - High-level API users call (`index`). It chooses PDF vs Markdown indexing paths, stores resulting structure/pages, and exposes a persistent workspace abstraction.
- `pageindex/retrieve.py:81-137` - Retrieval tool functions used by the QA layer. These provide compact metadata/structure/page-range access that downstream agents can call.
- `examples/agentic_vectorless_rag_demo.py:62-90` - Canonical “agentic RAG” usage. It wraps retrieval functions as `@function_tool` tools and lets one SDK agent plan calls over the indexed structure.

## 6. Use-Case Mapping

This repo clearly implements a **RAG + Agents-style retrieval workflow**, but with an important nuance: the core package is mostly an **LLM-driven indexing/retrieval pipeline**, while explicit agent runtime appears in the example script. The retrieval strategy is “vectorless”: it builds a hierarchical index, then a QA agent uses tool calls to inspect structure and fetch precise page windows instead of doing embedding similarity search.

The assigned category `RAG + Agents` is mostly correct for overall usage. However, strict “multi-agent systems” classification is weak here because runtime coordination is primarily single-agent (in demos) plus deterministic pipeline orchestration.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong end-to-end document structuring pipeline with verification/correction loops, not just one-shot extraction.
  - Recursive handling of large sections (`process_large_node_recursively`) gives scalable decomposition behavior.
  - Clear retrieval surface (`get_document*`, `get_page_content`) that is agent-tool friendly.
  - Works for both PDF and Markdown with shared output schema.
  - Practical persistence model (workspace JSON) supports reuse and low-friction demos.

- **Limitations:**
  - Not a true multi-agent runtime in core; agent orchestration is mostly single-agent demo usage.
  - Heavy reliance on prompt formatting + JSON extraction may be brittle under model variance.
  - No embedding/vector-store fallback, so retrieval quality depends on structure extraction quality.
  - Limited guardrails/testing around hallucinated section mapping beyond heuristic verification thresholds.
  - External integrations are relatively narrow (no web/tool ecosystems beyond document IO + LLM).

- **Research relevance:**
  - Good evidence for **LLM-orchestrated document parsing pipelines** as an alternative to embedding-first indexing.
  - Useful case study of **verification-and-repair loops** in structured extraction.
  - Demonstrates how lightweight tool APIs can support agentic QA over structured corpora.
  - Less suitable as evidence for emergent multi-agent coordination or decentralized agent systems.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: RAG + Agents
