---
repo_name: tarun7r/deep-research-agent
url: "https://github.com/tarun7r/deep-research-agent"
stars: 155
forks: 29
contributors_count: 3
last_commit_date: "2026-04-04T15:28:32+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 4
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, Code Generation]
generated_at: "2026-04-27T15:47:43.232362+00:00"
model: auto
duration_s: 61.2
clone_size_kb: 20385
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`deep-research-agent` is a multi-agent research automation system that takes a user topic, runs web research, evaluates source credibility, synthesizes findings, and outputs a citation-backed markdown report. A user can run it from CLI (`main.py`) or via a Chainlit app (`app.py`) and receive a saved report under `outputs/`. The runtime flow is not just prompt-chaining: it maintains explicit workflow state (`ResearchState`) and moves through planning, searching, synthesis, and report writing stages. The project is designed for autonomous information gathering and report generation rather than conversational QA.

## 2. Agent Framework & Architecture

The code **actually uses LangGraph + LangChain** (not CrewAI/AutoGen/LlamaIndex). Evidence includes `StateGraph` imports and graph compilation in `src/graph.py:14-167`, plus LangChain model/prompt/tool primitives in `src/agents.py:10-17` and `src/agents.py:124-133`. Dependencies also explicitly include both frameworks in `pyproject.toml:7-9`.

Architecture is a role-based pipeline with four agent classes: `ResearchPlanner`, `ResearchSearcher`, `ResearchSynthesizer`, and `ReportWriter` (`src/agents.py:103-839`). These are attached as LangGraph nodes in `create_research_graph()` (`src/graph.py:74-85`) and operate over shared typed state (`src/state.py:40-90`). The “intelligence” is split between: (a) long role-specific system prompts in `src/prompts/*.py`, (b) tool-enabled LangChain agents created at runtime for search/synthesis (`create_agent(...)`), and (c) graph routing guards that stop/continue based on state validity.

It also includes operational infrastructure: checkpointing with `MemorySaver`/`SqliteSaver` for resumability (`src/graph.py:40-57`, `src/graph.py:268-317`), caching (`src/graph.py:194-200`), and token/call accounting stored in state updates (`src/agents.py:177-185`, `src/agents.py:653-662`).

## 3. Orchestration Pattern

Closest match: **graph (LangGraph-style state machine)** with a mostly sequential path and conditional exits.

Control flow is explicitly encoded as graph edges:

```81:99:src/graph.py
workflow.add_node("plan", planner.plan)
workflow.add_node("search", searcher.search)
workflow.add_node("synthesize", synthesizer.synthesize)
workflow.add_node("write_report", writer.write_report)

workflow.add_edge(START, "plan")
...
if not state.plan or not state.plan.search_queries:
    return END
return "search"
```

Each phase routes via conditional validators, not just fixed chaining:

```142:163:src/graph.py
workflow.add_conditional_edges("plan", should_continue_after_plan, {"search": "search", END: END})
workflow.add_conditional_edges("search", should_continue_after_search, {"synthesize": "synthesize", END: END})
workflow.add_conditional_edges("synthesize", should_continue_after_synthesize, {"write_report": "write_report", END: END})
workflow.add_conditional_edges("write_report", should_continue_after_report, {END: END})
```

Inside nodes, some roles are themselves tool-using LangChain agents (`create_agent`) that autonomously decide tool calls (`src/agents.py:248-275`, `src/agents.py:423-451`), so orchestration is graph-level plus intra-node agent autonomy.

## 4. Tools & External Integrations

- **LLM providers (Gemini/OpenAI/Ollama/llama.cpp)**: model selection and client construction in `get_llm()` (`src/agents.py:48-97`), configuration in `src/config.py:17-70`.
- **Web search APIs**:
  - DuckDuckGo via `ddgs` (`src/utils/web_utils.py:16`, provider in `src/utils/web_utils.py:189-280`).
  - Tavily via `AsyncTavilyClient` (`src/utils/web_utils.py:17`, provider in `src/utils/web_utils.py:282-342`).
  - Provider wiring selected from config in `src/utils/tools.py:23-35`.
- **Web content extraction**: async HTTP fetch via `httpx` + HTML parsing via BeautifulSoup in `ContentExtractor` (`src/utils/web_utils.py:390-505`), exposed as tool `extract_webpage_content` (`src/utils/tools.py:131-219`).
- **LangChain tool interfaces for agents**: tools decorated with `@tool` and grouped per role (`src/utils/tools.py:40-643`), then injected via `get_research_tools(...)` into search/synthesis/writing agents (`src/agents.py:219`, `src/agents.py:407`, `src/agents.py:574`).
- **Checkpoint persistence**: LangGraph checkpointers with in-memory and SQLite backends (`src/graph.py:40-57`, `src/graph.py:268-307`).
- **Chainlit UI integration**: interactive frontend wiring in `app.py:240-774`.
- **Local filesystem outputs/history**: report write/export/history logic in `main.py:71-83` and `app.py:605-633`.

No browser automation (Playwright), terminal-shell tools, vector DB, or RAG index backend are implemented in this codebase.

## 5. Notable Code Walkthrough

- `src/graph.py:64-167` - Defines the LangGraph state machine, registers agent-node callables, and adds conditional routing guards for failure/quality gating. This is the orchestration core.
- `src/agents.py:103-202` - `ResearchPlanner` generates structured JSON plans (objectives, search queries, outline) and normalizes them into typed `ResearchPlan`; this determines downstream behavior.
- `src/agents.py:209-396` - `ResearchSearcher` runs a tool-using LangChain agent, parses tool messages into `SearchResult`s, and applies credibility filtering before passing results forward.
- `src/agents.py:402-557` - `ResearchSynthesizer` performs finding extraction over collected results (with fallback parsing), producing key findings that feed report composition.
- `src/utils/tools.py:40-643` + `src/utils/web_utils.py:189-505` - Concrete tool layer for web search/extraction, including provider abstraction, rate-limit handling, and circuit breakers; this is where external-world interaction happens.

## 6. Use-Case Mapping

The assigned primary use case (**Code Generation**) does **not** match the implementation. This repo automates a research workflow: plan topic -> gather web sources -> score credibility -> synthesize findings -> generate a cited report (`src/graph.py:81-85`, `src/agents.py:579-839`). There is no code synthesis loop, repository editing, compiler/test feedback cycle, or software artifact generation pipeline typical of code-generation agents.  
**Better category: Workflow Automation** (with research-report generation specialization).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent role decomposition with typed shared state (`src/state.py:40-90`).
  - Explicit LangGraph orchestration and conditional routing gives inspectable control flow (`src/graph.py:86-164`).
  - Practical reliability features: retries, caching, checkpoint persistence/resume (`src/agents.py:129-198`, `src/graph.py:289-339`).
  - Tooling is modular with provider abstraction and fallback-capable search stack (`src/utils/web_utils.py:344-383`).
  - Credibility-aware filtering is built into the search-to-synthesis handoff (`src/agents.py:302-313`).

- **Limitations:**
  - Workflow is mostly linear; no branching subteams, debate, or dynamic planner re-entry after poor synthesis.
  - Search result extraction relies on parsing tool message structure heuristically (`src/agents.py:358-395`), which may be brittle across model/tool output changes.
  - Prompts are extensive but not externally versioned/evaluated; behavior quality is prompt-sensitive.
  - No formal test suite for multi-agent correctness/failure modes despite complex async + external I/O.
  - “Multi-agent” is role-based in one process; no distributed agent communication or independent memory modules.

- **Research relevance:**
  - Good example of **graph-orchestrated multi-role LLM workflow** in production-style Python.
  - Shows integration of **tool-using agents + credibility scoring** in a single pipeline.
  - Useful for studying **stateful checkpoint/resume** in agent workflows (LangGraph checkpointers).
  - Illustrates tradeoffs between deterministic orchestration (graph) and stochastic intra-node autonomy (`create_agent`).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
