---
repo_name: Bessouat40/RAGLight
url: "https://github.com/Bessouat40/RAGLight"
stars: 659
forks: 100
contributors_count: 5
last_commit_date: "2026-03-24T15:46:25+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 6
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T13:05:33.086466+00:00"
model: auto
duration_s: 65.5
clone_size_kb: 7560
uses_mas: no
final_use_case: RAG + Agents
---
## 1. Overview

RAGLight is a Python framework for building retrieval-augmented assistants over local folders or cloned GitHub repositories, exposed via CLI (`raglight chat`, `raglight agentic-chat`) and a FastAPI service (`raglight serve`). Users configure an embeddings model, vector store, and LLM, ingest documents/code, then ask questions that are answered from retrieved context. The codebase supports both a classic RAG pipeline and an “agentic” mode that lets an LLM call retrieval tools (and optional MCP tools) during reasoning. In practice, the main output is a context-grounded answer stream or chat response, with optional ingestion APIs for files/repos.

## 2. Agent Framework & Architecture

The repo uses **LangGraph** (for the non-agent RAG state machine) and **LangChain agents** (for the tool-calling “agentic” mode), not CrewAI/AutoGen. Evidence: `StateGraph` import in `src/raglight/rag/rag.py:9` and `create_agent` import in `src/raglight/rag/agentic_rag.py:4`; MCP is integrated via `MultiServerMCPClient` in `src/raglight/rag/agentic_rag.py:9`.

Architecture is split in two runtimes.  
1) **Standard RAG path**: `RAGPipeline` builds embeddings/vector store/LLM with `Builder`, then executes a LangGraph sequence (`reformulate? -> retrieve -> rerank? -> generate`) in `src/raglight/rag/rag.py:195-214`.  
2) **Agentic path**: `AgenticRAG` creates one tool-calling agent with local retrieval tools and optional MCP tools per call in `src/raglight/rag/agentic_rag.py:45-69` and `176-184`.

The “intelligence” mainly lives in: (a) the LangGraph node functions (`_reformulate`, `_retrieve`, `_rerank`, `_generate_graph`), and (b) a long agent system prompt (`Settings.DEFAULT_AGENT_PROMPT`) that instructs when to call tools (`src/raglight/config/settings.py:72-178`).

## 3. Orchestration Pattern

Closest match is **graph orchestration** for core RAG, plus **single-agent tool orchestration** for agentic mode (not hierarchical multi-agent).

In the standard pipeline, control flow is explicitly a compiled state graph:

```195:214:src/raglight/rag/rag.py
def _createGraph(self) -> Any:
    if self.cross_encoder:
        steps = [self._retrieve, self._rerank, self._generate_graph]
        self.k = 4 * self.k
    else:
        steps = [self._retrieve, self._generate_graph]
    if self.reformulation:
        steps = [self._reformulate] + steps
    graph_builder = StateGraph(State).add_sequence(steps)
    graph_builder.add_edge(START, first_step)
    return graph_builder.compile()
```

In agentic mode, a **single** LangChain agent executes with tools; there is no planner/worker split:

```174:189:src/raglight/rag/agentic_rag.py
self.conversation_history.append(HumanMessage(content=query))
if self.config.mcp_config:
    mcp_client = MultiServerMCPClient(self.config.mcp_config)
    mcp_tools = await mcp_client.get_tools()
    all_tools = self.local_tools + mcp_tools
    agent = create_agent(self.model, tools=all_tools, system_prompt=self.config.system_prompt)
else:
    agent = self._local_agent
result = await self._invoke_agent(agent, query)
```

## 4. Tools & External Integrations

- **Local retrieval tools (`retriever`, `class_retriever`)**: implemented as LangChain `BaseTool` wrappers over vector search in `src/raglight/rag/agentic_rag_utils/rag_tools.py:22-63`, wired into the agent in `src/raglight/rag/agentic_rag.py:45-48`.
- **MCP servers/tools**: optional remote tools fetched at runtime via `MultiServerMCPClient(...).get_tools()` in `src/raglight/rag/agentic_rag.py:176-179`; config schema includes `mcp_config` in `src/raglight/config/agentic_rag_config.py:17`.
- **Vector stores**: Chroma and Qdrant selectable in builder (`src/raglight/rag/builder.py:103-149`), used by both RAG and agentic pipelines.
- **LLM providers**: Ollama, OpenAI/vLLM, Mistral, Gemini, Bedrock via builder/model factories (`src/raglight/rag/builder.py:154-187`, `src/raglight/rag/agentic_rag.py:86-126`).
- **Data ingestion integrations**: local folder and GitHub clone ingestion via `GithubScrapper` in pipelines (`src/raglight/rag/simple_rag_api.py:101-114`, `src/raglight/rag/simple_agentic_rag_api.py:58-71`).
- **API/serving integration**: FastAPI endpoints for generate/stream/ingest (`src/raglight/api/router.py:62-249`) and app lifecycle pipeline setup (`src/raglight/api/app.py:50-68`).
- **Observability**: Langfuse callback integration in standard RAG path (`src/raglight/rag/rag.py:216-241`).

## 5. Notable Code Walkthrough

- `src/raglight/rag/agentic_rag.py:19-219` - Core agentic engine: builds one LangChain agent, attaches local retrieval tools, optionally augments with MCP tools per request, and executes async with bounded recursion (`max_steps`).
- `src/raglight/rag/rag.py:21-320` - Core non-agent RAG engine: defines typed graph state, retrieval/reformulation/reranking/generation nodes, compiles `StateGraph`, and maintains conversation history.
- `src/raglight/rag/agentic_rag_utils/rag_tools.py:22-63` - Tool definitions that expose semantic retrieval and class-level retrieval to the agent; these are the practical “action space” for agentic responses.
- `src/raglight/cli/main.py:449-683` - User-facing agentic CLI command (`agentic-chat`) that configures models/vector store, builds `AgenticRAGPipeline`, ingests sources, and runs interactive Q&A.
- `src/raglight/rag/builder.py:47-229` - Dependency composition layer that standardizes provider/backend selection and constructs either vector-store-only or full RAG objects.

## 6. Use-Case Mapping

The assigned category **Browser / Terminal Use** looks mostly incorrect for this repo’s actual core logic. The implemented behavior is primarily **RAG + Agents**: ingest corpora/code, retrieve relevant chunks/classes, and answer via either a graph RAG chain or a tool-calling LLM agent (`src/raglight/rag/rag.py`, `src/raglight/rag/agentic_rag.py`). The terminal appears mainly as a delivery interface (CLI wizard/chat), not as an autonomous browser/terminal-control agent. Better fit: **RAG + Agents**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clean separation between classic graph RAG and agentic tool-calling RAG (`rag.py` vs `agentic_rag.py`).
  - Pluggable backend design (LLMs, embeddings, vector DBs) through a consistent builder pattern.
  - Practical MCP extensibility path already wired at runtime (local + remote tool composition).
  - Multiple serving surfaces (CLI, REST, Streamlit) with shared pipeline primitives.
  - Includes conversation history handling and optional reformulation/reranking for retrieval quality.

- **Limitations:**
  - Not a true multi-agent system at runtime; agentic mode is single-agent tool use.
  - Agent prompt is very prescriptive and may mismatch actual output contract enforcement (no strict parser/validator layer).
  - MCP setup appears config-driven but lacks richer policy/permission controls in core runtime.
  - API app (`create_app`) currently wires only `RAGPipeline` (non-agentic), so agentic mode is CLI-centered.
  - Limited explicit tests around agentic orchestration behavior versus broader component tests.

- **Research relevance:**
  - Good example of hybrid architecture combining deterministic graph-RAG and ReAct-like tool calling in one library.
  - Useful evidence for “agentification” of RAG systems via retrieval tools + MCP without full MAS complexity.
  - Demonstrates practical modularity tradeoffs in applied LLM systems (provider abstraction, backend swapping).
  - Appropriate baseline for comparing single-agent tool use against true multi-agent coordination frameworks.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: RAG + Agents
