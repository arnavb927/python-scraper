---
repo_name: assafelovic/gpt-researcher
url: "https://github.com/assafelovic/gpt-researcher"
stars: 26623
forks: 3558
contributors_count: 241
last_commit_date: "2026-04-16T17:41:04+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 11
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T06:15:52.254674+00:00"
model: auto
duration_s: 105.3
clone_size_kb: 33655
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`assafelovic/gpt-researcher` is an LLM-driven research automation system that takes a user query, performs iterative web/document retrieval, synthesizes findings, and produces a structured report (optionally with citations, images, and export formats). A typical user runs `GPTResearcher` (Python API or backend entrypoints), calls `conduct_research()`, then `write_report()`, and receives generated report text and collected source URLs (`gpt_researcher/agent.py:331-401`, `gpt_researcher/agent.py:451-493`). The repo also contains a multi-agent mode where a chief editor orchestrates planner/researcher/reviewer/reviser/writer/publisher roles over a graph workflow (`multi_agents/agents/orchestrator.py:52-81`). In practice, it solves “deep research report generation” by combining search, scraping, context compression, and LLM writing into one automated pipeline.

## 2. Agent Framework & Architecture

This repo uses **multiple frameworks plus custom orchestration**:

- **LangGraph** is directly used in the `multi_agents` path via `StateGraph` (`multi_agents/agents/orchestrator.py:4`, `multi_agents/agents/editor.py:5`).
- **LangChain** is used for LLM/output-parser chains and vector/document abstractions (`gpt_researcher/utils/llm.py:13-15`, `gpt_researcher/vector_store/vector_store.py:6-8`).
- **AG2/AutoGen** is present in an alternate multi-agent implementation (`multi_agents_ag2/agents/orchestrator.py:7`).
- The core `gpt_researcher` runtime is largely **custom agentic orchestration** around `GPTResearcher`, `ResearchConductor`, and “skills” classes (`gpt_researcher/agent.py:36-193`, `gpt_researcher/skills/researcher.py:21-47`).

High-level architecture has two major tracks.  
(1) **Core GPTResearcher track**: one top-level agent object composes sub-skills (research conductor, context manager, browser manager, report generator, optional deep-research skill), with LLM calls used for agent-role selection, subquery planning, synthesis, and writing (`gpt_researcher/agent.py:185-193`, `gpt_researcher/actions/agent_creator.py:18-59`).  
(2) **Multi-agent team track**: explicit role agents coordinated by a chief editor over a LangGraph state machine, including human-in-the-loop branching and reviewer/reviser loop (`multi_agents/agents/orchestrator.py:56-81`, `multi_agents/agents/editor.py:131-142`).

The “intelligence” is distributed across prompt templates, LLM routing/planning calls, and graph transitions—not in static rules alone (`gpt_researcher/actions/query_processing.py:63-110`, `multi_agents/agents/editor.py:79-117`).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker + graph state machine (hybrid)**.

- In `multi_agents`, a **chief editor** constructs a LangGraph with role-nodes and explicit transitions (manager-worker pattern implemented as graph):
```python
workflow.add_node("browser", agents["research"].run_initial_research)
workflow.add_node("planner", agents["editor"].plan_research)
workflow.add_node("researcher", agents["editor"].run_parallel_research)
workflow.add_node("writer", agents["writer"].run)
workflow.add_node("publisher", agents["publisher"].run)
workflow.add_node("human", agents["human"].review_plan)
```
`multi_agents/agents/orchestrator.py:56-62`

- Control includes conditional loopback from human/reviewer feedback:
```python
workflow.add_conditional_edges(
    'human',
    lambda review: "accept" if review['human_feedback'] is None else "revise",
    {"accept": "researcher", "revise": "planner"}
)
```
`multi_agents/agents/orchestrator.py:77-81`

Inside each section draft, there is a second reviewer/reviser feedback loop:
`multi_agents/agents/editor.py:136-142`.  
So this is not swarm/peer-to-peer; it is centrally orchestrated with staged execution and conditional revision loops.

## 4. Tools & External Integrations

- **Web search APIs via pluggable retrievers** (Google, Tavily, Serper, Exa, Semantic Scholar, PubMed Central, DuckDuckGo, etc.) are selected in retriever factory: `gpt_researcher/actions/retriever.py:8-101`.
- **MCP servers / tool calling** via `MCPRetriever` + `MultiServerMCPClient` (langchain-mcp-adapters), with tool selection then execution pipeline: `gpt_researcher/retrievers/mcp/retriever.py:14-22`, `gpt_researcher/retrievers/mcp/retriever.py:137-156`, `gpt_researcher/mcp/client.py:40-103`.
- **Browser automation / scraping** through `BrowserManager` and `NoDriverScraper` (zendriver-based browser sessions): `gpt_researcher/skills/browser.py:55-60`, `gpt_researcher/scraper/browser/nodriver_scraper.py:141-153`, `gpt_researcher/scraper/browser/nodriver_scraper.py:208-225`.
- **LLM provider abstraction** (OpenAI/other configured providers) through `GenericLLMProvider` and unified completion helper: `gpt_researcher/utils/llm.py:27-39`, `gpt_researcher/utils/llm.py:41-107`.
- **Vector stores / RAG context** via LangChain vector-store wrapper and chunking: `gpt_researcher/vector_store/vector_store.py:10-24`, `gpt_researcher/vector_store/vector_store.py:30-43`.
- **LangSmith tracing hook** in multi-agent entrypoint when API key exists: `multi_agents/main.py:12-15`.
- **Output/export path** includes markdown-to-PDF utility in backend deep research runner: `backend/report_type/deep_research/main.py:2`, `backend/report_type/deep_research/main.py:27-29`.

## 5. Notable Code Walkthrough

- `gpt_researcher/agent.py:36-193`  
  Defines the main runtime object, wires skills/components, handles MCP strategy, and routes between normal vs deep research. This is the primary API surface most users interact with.

- `gpt_researcher/skills/researcher.py:89-211`  
  Core orchestration engine for search/scrape/context-building across report sources (web/local/hybrid/vectorstore), including subquery planning and MCP-aware branching.

- `gpt_researcher/skills/deep_research.py:199-361`  
  Implements recursive breadth/depth research with concurrency limits, spawning nested `GPTResearcher` runs and aggregating learnings/citations.

- `multi_agents/agents/orchestrator.py:52-119`  
  Builds and executes the LangGraph workflow for role-based coordination (browser/planner/human/researcher/writer/publisher), making the multi-agent pipeline explicit.

- `gpt_researcher/retrievers/mcp/retriever.py:116-189`  
  Shows MCP integration as a 3-stage flow (discover tools, select tools, conduct research), which is key to the agent-tool architecture.

## 6. Use-Case Mapping

For the assigned primary use case (**Browser / Terminal Use**): the repository strongly supports the **browser** half via web retrieval + automated browser scraping (`gpt_researcher/skills/browser.py:37-84`, `gpt_researcher/scraper/browser/nodriver_scraper.py:190-225`). However, it does **not** look like a terminal-control agent in the ReAct “shell tool use” sense. The dominant pattern is autonomous research/report generation with multi-step orchestration, retrieval, and synthesis.

So the assignment is only partially right: “Browser” is valid, “Terminal Use” is not central. A better category from the provided list is **Workflow Automation** (with strong RAG+Agents characteristics).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent orchestration variants (LangGraph and AG2) rather than only a single monolithic loop.
  - Rich retriever abstraction supporting many external search backends plus MCP tool ecosystems.
  - Deep-research mode includes recursive breadth/depth exploration with concurrency controls.
  - Practical hybrid data pipeline (web + local docs + vector store + MCP) for robust research context.
  - Human-in-the-loop checkpoints and reviewer/reviser loops are explicit in graph control flow.

- **Limitations:**
  - Architecture is split across several paradigms (custom, LangGraph, AG2), which increases operational complexity.
  - Multiple orchestration paths may create maintenance drift or behavioral inconsistency across modes.
  - Some control flow relies on fragile prompt-formatted outputs (e.g., manual parsing of “Query:” / “Goal:” patterns).
  - Browser scraping and third-party retrievers introduce runtime fragility (rate limits, content variability, dependency issues).
  - MCP sync/async bridging is complex and could be error-prone under high-load/event-loop edge cases.

- **Research relevance:**
  - Useful evidence of hybrid MAS design combining graph-based control, role specialization, and tool-augmented retrieval.
  - Demonstrates real-world integration of MCP tool selection and execution in an LLM research pipeline.
  - Provides a case study of human-feedback gates and iterative review/revision loops in production-style multi-agent workflows.
  - Shows practical tradeoffs between planner-generated subtasks and retrieval-grounded synthesis in autonomous report generation.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
