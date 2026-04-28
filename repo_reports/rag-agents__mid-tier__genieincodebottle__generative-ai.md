---
repo_name: genieincodebottle/generative-ai
url: "https://github.com/genieincodebottle/generative-ai"
stars: 2232
forks: 548
contributors_count: 6
last_commit_date: "2026-04-17T16:21:07+00:00"
primary_use_case: RAG + Agents
user_tier: Mid-Tier
total_score: 6
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T12:42:06.322092+00:00"
model: auto
duration_s: 89.8
clone_size_kb: 285787
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a broad GenAI learning monorepo, but the executable agentic core lives in subprojects like `genai-usecases/agentic-ai` and `genai-usecases/advance-rag/agentic-rag`. A user typically runs Streamlit apps (for example `agentic_ai_platform.py` or `multi_agent_orchestration.py`) to launch interactive workflows where multiple LLM-driven roles coordinate on tasks such as market strategy, code review, research, customer support, and planning. The outputs are generated analyses, recommendations, workflow traces, and downloadable reports/metrics. So while the repo includes many tutorials, it also contains runnable multi-agent orchestration demos with real control flow and tool calls.

## 2. Agent Framework & Architecture

Framework use is explicit in code imports: **CrewAI** (`from crewai import Agent, Task, Crew...`) and **LangGraph** (`from langgraph.graph import StateGraph, START, END`) are both implemented in production-style examples (`genai-usecases/agentic-ai/multi_agent_orchestration/multi_agent_orchestration.py:41-46`). The code also uses **LangChain model/tool abstractions** (`langchain_core.messages`, `@tool`, provider-specific chat classes) as the LLM/tool layer under LangGraph (`.../multi_agent_orchestration.py:49-56`, `706-716`).

Architecture is split by pattern. In CrewAI paths, agents are role-specialized (market analyst, risk analyst, reviewer, etc.), tasks are composed with context dependencies, and execution is managed by a hierarchical crew manager (`.../multi_agent_orchestration.py:789-938`; `.../code_review_crew/code_review_crew.py:552-588`). In LangGraph paths, state is represented via typed dicts and flows across nodes for classifier/analyst/synthesizer stages (`.../customer_support_agent.py:49-60`, `671-697`; `.../task_planning_system.py:42-53`, `1036-1057`).

There is also a **hybrid cross-framework orchestration** layer where a CrewAI phase runs first and its output is passed into a LangGraph phase (`.../multi_agent_orchestration.py:1305-1323`). This places “intelligence” in a combination of role prompts, graph topology, and task routing logic rather than a single monolithic agent.

## 3. Orchestration Pattern

Closest match: **other (hybrid showcase combining hierarchical manager-worker and graph state-machine orchestration)**.

- **Hierarchical manager-worker (CrewAI):** `process=Process.hierarchical` and `manager_llm=self.llm` in crew construction (`.../multi_agent_orchestration.py:929-934`), with task context fan-in for synthesis (`...:913-926`).
- **Graph/state-machine (LangGraph):** explicit node/edge graph from `START` to `END` (`.../multi_agent_orchestration.py:1190-1205`) and conditional routing in support workflow (`.../customer_support_agent.py:652-693`).

Short excerpts:

`genai-usecases/agentic-ai/multi_agent_orchestration/multi_agent_orchestration.py:929-934`
```python
crew = Crew(
    agents=[market_researcher, competitive_analyst, financial_analyst, risk_analyst, strategy_manager],
    tasks=[market_analysis_task, competitive_analysis_task, financial_modeling_task, risk_assessment_task, strategy_synthesis_task],
    process=Process.hierarchical,
    manager_llm=self.llm,
```

`genai-usecases/agentic-ai/multi_agent_orchestration/multi_agent_orchestration.py:1200-1205`
```python
workflow.add_edge(START, "research_coordinator")
workflow.add_edge("research_coordinator", "market_analyst")
workflow.add_edge("market_analyst", "financial_analyst")
workflow.add_edge("financial_analyst", "risk_analyst")
workflow.add_edge("risk_analyst", "strategy_synthesizer")
workflow.add_edge("strategy_synthesizer", END)
```

## 4. Tools & External Integrations

- **LLM provider APIs** (OpenAI, Anthropic, Google Gemini, Groq, Ollama) wired in factory methods and UI selections (`.../multi_agent_orchestration.py:1038-1059`, `1466-1492`; `.../task_planning_system.py:785-819`).
- **CrewAI custom tools** for business analysis (market, competitive, finance, risk), used by specialized agents (`.../multi_agent_orchestration.py:124-233`, `236-370`, `373-537`, `540-703`, `792-837`).
- **LangChain `@tool` wrappers** used inside LangGraph nodes (`.../multi_agent_orchestration.py:706-716`, `1105-1108`, `1136-1138`).
- **Web/RSS and finance data** via `feedparser` and `yfinance` in analysis tools (`.../multi_agent_orchestration.py:36-38`, `130-146`, `172-179`, `550-557`).
- **RAG stack** in agentic RAG module: document loaders (`PyPDFLoader`, `TextLoader`, `CSVLoader`), chunking (`RecursiveCharacterTextSplitter`), vector store (`Chroma`), embeddings (`GoogleGenerativeAIEmbeddings`) (`genai-usecases/advance-rag/agentic-rag/agentic_rag_system.py:31-34`, `230-241`, `344-354`).
- **Web search augmentation** via Tavily client (`.../agentic_rag_system.py:39`, `98-147`, `248-253`, `509-512`).
- **Persistence/checkpointing in some LangGraph apps** with `MemorySaver` (`.../customer_support_agent.py:23`, `695-696`; `.../task_planning_system.py:25`, `1056-1057`).
- **File-system I/O** for logs/artifacts (`.../customer_support_agent.py:893-915`; `.../code_review_crew/code_review_crew.py:560-585`).

## 5. Notable Code Walkthrough

- `genai-usecases/agentic-ai/multi_agent_orchestration/multi_agent_orchestration.py:723-1014` - Defines a full CrewAI hierarchical orchestrator with five specialist agents, custom tools, task dependencies, and execution metrics; this is the clearest “true MAS” runtime implementation.
- `genai-usecases/agentic-ai/multi_agent_orchestration/multi_agent_orchestration.py:1021-1281` - Implements a LangGraph multi-node workflow with typed shared state and tool-augmented nodes, then executes it asynchronously with measured outputs.
- `genai-usecases/agentic-ai/agentic_frameworks/langgraph/customer_support_agent.py:483-697` - Shows conditional graph routing (`conversation_router`) plus operational support tools (KB search, sentiment, escalation, ticketing), demonstrating event-like branching.
- `genai-usecases/agentic-ai/agentic_frameworks/crewai/code_review_crew/code_review_crew.py:406-588` - Builds agents/tasks from YAML, maps toolsets by role, and runs configurable sequential/hierarchical review pipelines.
- `genai-usecases/advance-rag/agentic-rag/agentic_rag_system.py:283-307, 363-614` - Implements a planner/retriever/researcher/synthesizer/validator LangGraph pipeline over Chroma + Tavily, representing agentic RAG rather than only static retrieval.

## 6. Use-Case Mapping

The assigned label **RAG + Agents** is only partially accurate at repo level. There is a real agentic RAG implementation (`.../advance-rag/agentic-rag/agentic_rag_system.py`), including retrieval, web-augmented research, and synthesis. However, the dominant implemented multi-agent examples in the current codebase are broader **workflow orchestration** (business analysis, task planning, support routing, code review, research crews) with many non-RAG flows (`.../agentic-ai/...` modules).

So for the repository’s primary practical behavior, **Workflow Automation** is the better top category, with RAG+Agents as an important sub-area.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Implements multiple real orchestration paradigms (CrewAI hierarchical + LangGraph state graphs + hybrid handoff) in runnable code.
  - Uses explicit typed/shared state and conditional routing, making control flow inspectable (`SupportState`, `TaskPlanningState`, `MultiAgentState`).
  - Integrates external tools (finance APIs, RSS, Tavily, vector DB, document loaders) beyond toy chat loops.
  - Provides configurable LLM backends and local-first options (Ollama), useful for reproducible experiments.
  - Includes YAML-driven agent/task configuration in CrewAI examples, enabling rapid workflow reconfiguration.

- **Limitations:**
  - Much of the repo is educational breadth; quality and rigor vary across subprojects, with some “simulated” tools (e.g., placeholder search/fact-check behavior in research crew).
  - Limited automated testing coverage around agent orchestration correctness and failure recovery.
  - Some business/support logic relies on heuristic keyword routing rather than robust structured parsing.
  - Memory/checkpoint strategy is inconsistent across modules (some workflows use memory, others disable it).
  - Tight coupling to Streamlit UI in several modules can complicate headless reuse as library code.

- **Research relevance:**
  - Good evidence for comparative study of **manager-worker vs graph-based** LLM coordination in one codebase.
  - Demonstrates practical patterns for **tool-augmented multi-agent pipelines** with typed state passing.
  - Useful artifact for studying **hybrid orchestration across frameworks** (CrewAI output feeding LangGraph stage).
  - Provides concrete examples of **agentic workflow engineering** beyond chatbots, especially in operational domains.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
