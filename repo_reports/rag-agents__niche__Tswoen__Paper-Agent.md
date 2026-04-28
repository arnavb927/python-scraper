---
repo_name: Tswoen/Paper-Agent
url: "https://github.com/Tswoen/Paper-Agent"
stars: 156
forks: 15
contributors_count: 5
last_commit_date: "2026-03-04T02:22:05+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 3
architecture_labels: [LangGraph, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T16:51:38.453840+00:00"
model: auto
duration_s: 93.6
clone_size_kb: 723
uses_mas: yes
final_use_case: RAG + Agents
---
## 1. Overview

`Tswoen/Paper-Agent` is an API-first academic research assistant that turns a user query into a full literature report through a staged multi-agent pipeline. In practice, users run the FastAPI app (`main.py`) and call `/api/research?query=...`, then receive streamed progress/events while the system searches arXiv, extracts structured findings from papers, analyzes clusters/themes, drafts section content, and assembles a final Markdown report (`main.py:32-56`, `src/agents/orchestrator.py:95-109`). It is designed for “paper survey automation” rather than chat-only Q&A. The workflow also supports a human approval checkpoint for generated search conditions before retrieval executes (`src/agents/search_agent.py:72-79`, `src/agents/userproxy_agent.py:14-25`).

## 2. Agent Framework & Architecture

This repo **actually uses LangGraph + AutoGen** at runtime (not CrewAI). LangGraph is used to orchestrate stage-level workflow graphs (`src/agents/orchestrator.py:10-17`, `src/agents/writing_agent.py:7-15`), while AutoGen (`autogen_agentchat`, `autogen_core`, `autogen_ext`) defines individual LLM agents and group chats (`src/agents/search_agent.py:1-4`, `src/agents/sub_writing_agent/writing_chatGroup.py:2-5`). I did not find runtime CrewAI imports; LangChain appears only for KB ingestion/splitting utilities, not agent orchestration (`src/knowledge/knowledge/indexing.py`, `src/knowledge/knowledge/utils/kb_utils.py`).

High-level architecture is a **two-layer system**. Layer 1 is a LangGraph pipeline with nodes: search -> reading -> analysis -> writing -> report, plus error handling (`src/agents/orchestrator.py:68-91`). Layer 2 contains AutoGen sub-agents inside nodes: e.g., analysis composes clustering + deep-analysis + global-analysis agents (`src/agents/analyse_agent.py:41-47`, `:88-103`), and writing uses a selector-driven group (`writing_agent`, `retrieval_agent`, `review_agent`) (`src/agents/sub_writing_agent/writing_chatGroup.py:18-24`).

Most “intelligence” lives in prompt templates and role decomposition (`src/core/prompts.py`), plus structured outputs (Pydantic schemas in search/reading) and tool-enabled retrieval during writing (`src/agents/sub_writing_agent/retrieval_agent.py:10-19`).

## 3. Orchestration Pattern

Closest match: **graph (LangGraph-style state machine) with hierarchical sub-workflows**.

Top-level control flow is explicit conditional graph routing:

```10:17:src/agents/orchestrator.py
from langgraph.graph import StateGraph, END, START
from src.agents.search_agent import search_node
from src.agents.reading_agent import reading_node
from src.agents.analyse_agent import analyse_node
from src.agents.writing_agent import writing_node
from src.agents.report_agent import report_node
```

```83:89:src/agents/orchestrator.py
builder.add_edge(START, "search_node")
builder.add_conditional_edges("search_node", self.condition_handler)
builder.add_conditional_edges("reading_node", self.condition_handler)
builder.add_conditional_edges("analyse_node", self.condition_handler)
builder.add_conditional_edges("writing_node", self.condition_handler)
builder.add_conditional_edges("report_node", self.condition_handler)
builder.add_edge("handle_error_node", END)
```

Inside the writing stage, there is a nested manager-team pattern: a director generates section tasks, then parallel subtask execution runs a selector group chat among writer/retriever/reviewer until termination token (`APPROVE`) is reached (`src/agents/sub_writing_agent/writing_director_agent.py:56-90`, `src/agents/sub_writing_agent/writing_chatGroup.py:12-24`, `src/agents/sub_writing_agent/parallel_writing_node.py:30-65`).

## 4. Tools & External Integrations

- **LLM provider APIs (OpenAI-compatible endpoints via AutoGen model client)**: all agents instantiate `OpenAIChatCompletionClient` through config-driven provider/model selection (`src/core/model_client.py:1-4`, `:105-123`, `:165-199`).
- **arXiv API**: paper retrieval uses `arxiv` Python package in `PaperSearcher.search_papers()` (`src/tasks/paper_search.py:17-24`, `:58-64`, `:72-75`).
- **Vector knowledge base (ChromaDB)**: ingestion/query through KB manager and Chroma implementation (`src/knowledge/knowledge/implementations/chroma.py:56-63`, `:331-413`, `:499-555`; manager routing in `src/knowledge/knowledge/manager.py:233-239`).
- **RAG retrieval tool exposed to agent**: `retrieval_tool()` queries temporary + user-selected KB and is wrapped as AutoGen `FunctionTool` for `retrieval_agent` (`src/services/retrieval_tool.py:11-40`, `src/agents/sub_writing_agent/retrieval_agent.py:10-19`).
- **FastAPI + SSE streaming**: user-facing execution API and progress streaming (`main.py:32-56`), plus KB CRUD/upload/query endpoints (`src/knowledge/knowledge_router.py:25-63`, `:121-177`, `:241-252`, `:262-310`).
- **Human-in-the-loop input channel**: `UserProxyAgent` waits on async future populated by `/send_input` endpoint (`src/agents/userproxy_agent.py:14-25`, `main.py:32-36`).

## 5. Notable Code Walkthrough

- `src/agents/orchestrator.py:36-109` - Core LangGraph workflow engine; defines stage nodes, conditional transitions, and top-level state invocation.
- `src/agents/search_agent.py:30-94` - Search agent generates structured query constraints, requests human review, then runs arXiv retrieval.
- `src/agents/reading_agent.py:58-63,135-219` - Parallel per-paper extraction via AutoGen; validates/normalizes outputs and writes extracted content into a temporary vector KB.
- `src/agents/analyse_agent.py:35-47,88-119,124-155` - Composite analysis orchestrator that chains clustering, per-cluster deep analysis, and global synthesis with streamed updates.
- `src/agents/sub_writing_agent/parallel_writing_node.py:10-97` - Parallel section writer executor; each section uses a selector-driven multi-agent chat (write/retrieve/review) and writes section outputs into shared writing state.

## 6. Use-Case Mapping

This repo strongly matches **RAG + Agents**. The RAG side is explicit: extracted paper metadata/content is embedded into a temporary KB, queried via `retrieval_tool`, and used during writing (`src/agents/reading_agent.py:80-97`, `:213-216`; `src/services/retrieval_tool.py:21-35`). The agent side is also explicit and multi-level: stage agents (search/reading/analysis/writing/report), analysis sub-agents, and writing-team group chat (`src/agents/orchestrator.py`, `src/agents/analyse_agent.py`, `src/agents/sub_writing_agent/writing_chatGroup.py`).  
It also performs workflow automation, but the distinguishing runtime mechanism is retrieval-augmented multi-agent report generation, so `RAG + Agents` is the better primary category.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear hybrid design: LangGraph for deterministic control + AutoGen for agent interactions.
  - End-to-end pipeline from search to final report, with SSE progress visibility (`main.py`, `orchestrator.py`).
  - Real human-in-the-loop checkpoint before expensive downstream processing (`search_agent.py`, `userproxy_agent.py`).
  - Hierarchical multi-agent composition (top-level graph + nested writing and analysis agent teams).
  - Practical RAG integration with temporary/session KB and optional user KB fusion.

- **Limitations:**
  - Error propagation and type consistency are fragile in places (e.g., mixed dict/list return assumptions in retrieval paths).
  - Some code appears partially unfinished or inconsistent (e.g., stubs/comments in Chroma/image paths; minor API mismatches in test/demo paths).
  - Prompt-heavy control may be brittle; limited explicit guardrails for hallucination beyond reviewer role.
  - No strong evidence of robust evaluation harness for output quality/reproducibility in production path.
  - Security/ops hardening appears minimal for open upload/query endpoints in default API setup.

- **Research relevance:**
  - Good case study of **hybrid symbolic/LLM orchestration** (graph state machine + conversational agents).
  - Demonstrates **hierarchical MAS decomposition** (macro pipeline and micro teams per stage).
  - Illustrates **human-in-the-loop gating** inside autonomous agent workflows.
  - Useful evidence for applied **academic-survey agent systems** combining retrieval, synthesis, and report generation.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: RAG + Agents
