---
repo_name: 666ghj/BettaFish
url: "https://github.com/666ghj/BettaFish"
stars: 40593
forks: 7527
contributors_count: 41
last_commit_date: "2026-03-13T16:22:39+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T10:24:05.370030+00:00"
model: auto
duration_s: 90.7
clone_size_kb: 345183
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`BettaFish` is an end-to-end public-opinion analysis platform that orchestrates data crawling, three analysis engines, a forum-like multi-agent synthesis layer, and a final report generator. In practice, users run the Flask app (`app.py`) and trigger analysis from the UI; this launches `Insight`, `Media`, and `Query` Streamlit engines plus `ForumEngine`, then compiles outputs into a structured HTML/Markdown/PDF report (`app.py:268-340`, `app.py:506-510`, `ReportEngine/flask_interface.py:604-695`). The system is designed to turn heterogeneous data (news/web search + local social data + sentiment signals) into chaptered strategic reports rather than simple chat responses. It targets automated multi-source workflow execution for decision support.

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework**, not LangChain/LangGraph/CrewAI/AutoGen. I found no framework imports (`rg` search for `langchain|langgraph|crewai|autogen|llama_index` returned none), and the agent logic is implemented via custom `DeepSearchAgent`/`ReportAgent`, custom `Node` classes, custom `State`, and an OpenAI-compatible client wrapper (`QueryEngine/agent.py:26-74`, `InsightEngine/agent.py:41-94`, `QueryEngine/llms/base.py:30-80`, `ReportEngine/agent.py:174-221`).

Architecture is modular and role-based:
- **Three analysis agents** (`Query`, `Media`, `Insight`) each run a similar loop: generate report structure, per-paragraph search, reflection search, summarize, and format report (`QueryEngine/agent.py:141-216`, `InsightEngine/agent.py:512-585`).
- **Forum layer** monitors all three engines’ logs, extracts summary outputs, and writes cross-agent dialogue into `forum.log`; every 5 agent utterances it triggers an LLM “host” to synthesize/dispute/direct discussion (`ForumEngine/monitor.py:33-67`, `ForumEngine/monitor.py:631-648`, `ForumEngine/llm_host.py:57-89`).
- **Report agent** consumes the three engine reports + forum logs and runs a staged generation pipeline (template selection, layout, word budget, chapter generation with repair/retry, IR composition, rendering) (`ReportEngine/agent.py:405-417`, `ReportEngine/agent.py:455-513`, `ReportEngine/agent.py:569-770`).

“Intelligence” lives mostly in node prompts + LLM calls, while orchestration logic is deterministic Python control flow.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker pipeline with event-driven coordination**.

- Manager-worker: `ReportAgent` acts as top-level orchestrator over multiple specialized nodes and per-chapter generation workers (`ReportEngine/agent.py:384-403`, `ReportEngine/agent.py:569-744`).
- Event-driven multi-agent coupling: `ForumEngine` watches engine logs and triggers host interventions based on buffered agent utterances (`ForumEngine/monitor.py:584-649`).

Short flow excerpts:
- Multi-engine launcher in main app: start `insight/media/query` processes, then forum monitor (`app.py:289-312`).
- Forum-triggered host speech after threshold:
  - buffer speeches (`ForumEngine/monitor.py:640-644`)
  - trigger host at threshold (`ForumEngine/monitor.py:646-648`)
  - generate host speech via LLM (`ForumEngine/monitor.py:542-547`, `ForumEngine/llm_host.py:221-229`).

## 4. Tools & External Integrations

- **OpenAI-compatible chat APIs** for all agents and host (`QueryEngine/llms/base.py:11-12`, `QueryEngine/llms/base.py:75-80`, `ForumEngine/llm_host.py:48-53`, `ReportEngine/agent.py:338-342`).
- **Tavily web/news search API** used by Query agent tools (`QueryEngine/tools/search.py:40-43`, `QueryEngine/tools/search.py:77-95`, `QueryEngine/agent.py:44-45`).
- **Local SQL databases (MySQL/Postgres dialect handling)** via `MediaCrawlerDB` for Insight/Media-style retrieval (`InsightEngine/tools/search.py:32-35`, `InsightEngine/tools/search.py:78-95`, `InsightEngine/tools/search.py:193-235`).
- **Sentiment model integration** in Insight flow (`InsightEngine/agent.py:30-33`, `InsightEngine/agent.py:389-430`).
- **Embedding + clustering stack** (`sentence-transformers`, `sklearn KMeans`) for result sampling (`InsightEngine/agent.py:14-16`, `InsightEngine/agent.py:129-188`).
- **Playwright-based crawling dependency and subprocess workflow** in MindSpider pipeline (`MindSpider/main.py:190-203`, `MindSpider/main.py:302-355`, `MindSpider/main.py:357-387`).
- **Flask + SSE + SocketIO** for orchestration and streaming task state (`app.py:18-19`, `ReportEngine/flask_interface.py:749-867`).
- **Report export/render services** (HTML/Markdown/PDF) inside ReportEngine API (`ReportEngine/flask_interface.py:1222-1279`, `ReportEngine/flask_interface.py:1289-1368`).

## 5. Notable Code Walkthrough

- `app.py:268-340, 1152-1198` - System supervisor that boots all sub-apps, runs forum monitor, and fans a single query to running engines via local HTTP.
- `ForumEngine/monitor.py:584-703` - Core runtime glue: tails engine logs, captures summary outputs, writes unified forum transcript, and orchestrates host injections.
- `ForumEngine/llm_host.py:133-163, 210-237` - Defines host persona/system prompt and makes synthesis calls that transform agent utterances into guided discussion.
- `QueryEngine/agent.py:217-306, 307-397` - Representative single-engine “plan-search-reflect-summarize” loop showing custom node-based iterative reasoning.
- `ReportEngine/agent.py:455-513, 569-770` - Final-stage orchestrator that converts multi-agent artifacts into validated chapter JSON, document IR, and rendered report.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** looks inaccurate for the core runtime. The system does not implement an autonomous browser-control or terminal-control agent loop; instead, it automates a multi-stage analysis pipeline (crawl/search/analyze/synthesize/report). There is browser crawling dependency (Playwright) in data collection (`MindSpider/main.py:190-203`), but that is a backend ingestion component, not interactive browser-agent operation. A better category is **Workflow Automation** (with strong secondary flavor of RAG + Agents due to multi-source retrieval and synthesis).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent role separation (Query/Media/Insight/Host/Report) with explicit handoff artifacts (`app.py`, `ForumEngine/monitor.py`, `ReportEngine/agent.py`).
  - Robust production-style orchestration: retries, validation, SSE streaming, task lifecycle, and file baselining (`ReportEngine/flask_interface.py`, `ReportEngine/agent.py`).
  - Strong output hardening: chapter JSON repair, fallback LLM rescue chain, schema validation, and graceful degradation (`ReportEngine/nodes/chapter_generation_node.py:475-535`, `:623-689`).
  - Hybrid retrieval stack (web API + local DB + sentiment + clustering), enabling broader evidence coverage (`QueryEngine/tools/search.py`, `InsightEngine/tools/search.py`, `InsightEngine/agent.py:129-188`).

- **Limitations:**
  - Inter-agent communication is indirect (log parsing) rather than structured message bus/state graph; brittle to log-format drift (`ForumEngine/monitor.py:58-67`, `:138-170`).
  - Heavy prompt/output parsing reliance; significant defensive code indicates unstable model-output contracts (`QueryEngine/nodes/search_node.py:91-121`, `ReportEngine/nodes/chapter_generation_node.py:742-927`).
  - Tight coupling to filesystem/process orchestration and local ports may complicate cloud-native scaling (`app.py:498-510`, `ReportEngine/agent.py:96-171`).
  - No explicit formal planner optimizing cross-agent task allocation; most routing is procedural and template-driven.

- **Research relevance:**
  - Practical example of **artifact-mediated multi-agent coordination** (logs/files as blackboard-like substrate).
  - Evidence for **engineering patterns in resilient LLM pipelines** (repair/retry/validation loops around structured outputs).
  - Useful case for studying **role-specialized heterogeneous agents** combining retrieval modalities and synthesis.
  - Demonstrates real-world tradeoff between orchestration simplicity and communication robustness in MAS systems.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
