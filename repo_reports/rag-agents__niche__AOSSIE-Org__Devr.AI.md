---
repo_name: AOSSIE-Org/Devr.AI
url: "https://github.com/AOSSIE-Org/Devr.AI"
stars: 87
forks: 140
contributors_count: 23
last_commit_date: "2026-02-11T19:14:34+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 4
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T15:51:52.384308+00:00"
model: auto
duration_s: 92.1
clone_size_kb: 8047
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

Devr.AI is a backend-first DevRel automation system that runs a Discord bot, triages incoming community messages, and routes qualifying requests to an LLM-driven workflow (`backend/main.py`, `backend/integrations/discord/bot.py`). A user interacts through Discord threads; the bot classifies whether the message needs DevRel help, enqueues it, and returns an AI-generated response in-thread. The system combines onboarding support, FAQ handling, web search, and GitHub-focused assistance, with session memory and summarization persisted to Supabase. It is not just a chatbot endpoint; it is an event/queue-based operational assistant for open-source community workflows.

## 2. Agent Framework & Architecture

The runtime is primarily **LangGraph + LangChain**, not CrewAI/AutoGen/LlamaIndex. This is explicit from imports like `StateGraph`, `END`, and LangChain chat models (`backend/app/agents/devrel/agent.py`, `backend/app/agents/base_agent.py`). The agent graph is stateful via `AgentState` and `InMemorySaver`, and LLM calls are done through `ChatGoogleGenerativeAI`.

Architecture-wise, there is one top-level DevRel graph agent with a **ReAct supervisor node** that chooses among tool-nodes (`web_search`, `faq_handler`, `onboarding`, `github_toolkit`) before response synthesis and optional summarization (`backend/app/agents/devrel/agent.py`). “Intelligence” is split across prompts (`react_prompt.py`, response/summarization prompts), router logic (`supervisor_decision_router`), and a nested GitHub toolkit that performs its own LLM intent classification (`backend/app/agents/devrel/github/github_toolkit.py`).

At system level, this graph is embedded in a queue-based orchestration loop: Discord -> LLM triage classifier -> RabbitMQ queue -> `AgentCoordinator` -> LangGraph execution -> platform response (`backend/integrations/discord/bot.py`, `backend/app/core/orchestration/queue_manager.py`, `backend/app/core/orchestration/agent_coordinator.py`).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker (with graph-internal tool loop)**.

- Outer layer: classifier + coordinator act as manager stages.
- Inner layer: LangGraph supervisor repeatedly decides which worker/tool node to run, then loops back until completion.

Representative control-flow excerpts:

```61:76:backend/app/agents/devrel/agent.py
workflow.add_conditional_edges(
    "react_supervisor",
    supervisor_decision_router,
    {
        "web_search": "web_search_tool",
        "faq_handler": "faq_handler_tool",
        "onboarding": "onboarding_tool",
        "github_toolkit": "github_toolkit_tool",
        "complete": "generate_response"
    }
)
for tool in ["web_search_tool", "faq_handler_tool", "onboarding_tool", "github_toolkit_tool"]:
    workflow.add_edge(tool, "react_supervisor")
```

```53:66:backend/integrations/discord/bot.py
triage_result = await self.classifier.should_process_message(...)
if triage_result.get("needs_devrel", False):
    await self._handle_devrel_message(message, triage_result)
...
agent_message = {
    "type": "devrel_request",
    ...
}
await self.queue_manager.enqueue(agent_message, priority)
```

## 4. Tools & External Integrations

- **LLM providers (Gemini via LangChain)**: used in triage, supervisor, response generation, summarization, and GitHub intent analysis (`classification_router.py`, `agent.py`, `nodes/react_supervisor.py`, `nodes/generate_response.py`, `github/github_toolkit.py`).
- **Web search tools**:
  - DuckDuckGo (`ddgs`) actively wired to agent web-search node (`tools/search_tool/ddg.py`, `nodes/handlers/web_search.py`).
  - Tavily class exists but is not the active default in current graph wiring (`tools/search_tool/tavilly.py`).
- **GitHub API integration**:
  - Direct REST via `requests` in `GitHubMCPService` (`github/services/github_mcp_service.py`).
  - Exposed through a local FastAPI “MCP server” process (`github/services/github_mcp_server.py`, `start_github_mcp_server.py`).
  - Called by GitHub support/repo tools (`github/tools/github_support.py`).
- **Vector store / retrieval infrastructure (RAG components)**:
  - Weaviate vector/BM25/hybrid contributor search (`app/database/weaviate/operations.py`).
  - Embeddings via SentenceTransformers (`services/embedding_service/service.py`).
- **Operational data stores**:
  - Supabase for users, interactions, and conversation summaries (`nodes/gather_context.py`, `nodes/generate_response.py`, `nodes/summarization.py`).
- **Message/event infrastructure**:
  - RabbitMQ via `aio_pika` for async orchestration (`core/orchestration/queue_manager.py`).
  - Discord bot integration (`integrations/discord/bot.py`).
  - GitHub webhook/event routes exist (`routes.py`).

## 5. Notable Code Walkthrough

- `backend/app/agents/devrel/agent.py:20-94`  
  Defines the LangGraph state machine: context gathering, supervisor routing, tool loop, response generation, and summarization checkpointing. This is the core agent runtime.

- `backend/app/agents/devrel/nodes/react_supervisor.py:10-113`  
  Implements ReAct-style decisioning and safe routing (`max iterations` guard). It is the central “planner/manager” deciding which capability to invoke next.

- `backend/app/agents/devrel/tool_wrappers.py:11-78`  
  Adapts handler outputs into standardized tool-results and feeds them back into supervisor context; also supports forced handoff patterns (e.g., onboarding -> GitHub toolkit).

- `backend/app/agents/devrel/github/github_toolkit.py:28-132`  
  A nested GitHub-specialized agent-like module: classifies GitHub intent with an LLM, then dispatches to sub-tools like contributor recommendation or GitHub support.

- `backend/app/core/orchestration/agent_coordinator.py:12-59`  
  Bridges queue messages to agent execution and platform response delivery, making the system operationally event-driven around the agent core.

## 6. Use-Case Mapping

The repository partially realizes **RAG + Agents** through contributor recommendation: user requests are query-aligned by LLM, embedded, and used for hybrid retrieval against Weaviate (`github/tools/contributor_recommendation.py:90-106`, `database/weaviate/operations.py:216-275`). However, the dominant production flow is broader **Workflow Automation**: Discord ingestion, triage, queue-based processing, multi-tool routing, and automated response/summary persistence (`integrations/discord/bot.py`, `core/orchestration/*`, `agents/devrel/*`). So the upstream “RAG + Agents” label captures an important subsystem, but the better top-level category for the whole repo is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear LangGraph state-machine implementation with explicit routing and loop-back control.
  - Practical multi-stage operational pipeline (triage -> queue -> agent -> channel response).
  - Good integration breadth (Discord, GitHub APIs, Supabase, Weaviate, RabbitMQ).
  - Session memory + summarization lifecycle is built into runtime rather than bolted on.
  - Nested specialization (`GitHubToolkit`) separates domain reasoning from top-level supervisor.

- **Limitations:**
  - “Multi-agent” is mostly hierarchical modularity; no rich peer-to-peer agent collaboration/swarm.
  - FAQ handling is largely static dictionary matching, not true knowledge-grounded retrieval.
  - Some capabilities are declared but not implemented (`issue_creation`, `documentation_generation` in toolkit).
  - Tavily exists but active search path appears DDG-centric; tool selection is not strongly adaptive by source quality.
  - Limited robustness patterns for malformed LLM output beyond simple JSON extraction/fallback.

- **Research relevance:**
  - Useful example of **graph-orchestrated LLM tool use** in a real ops setting (community management).
  - Demonstrates coupling of agent reasoning with asynchronous queue/event systems.
  - Illustrates hybrid retrieval integration (vector + keyword) within an agent toolchain.
  - Shows practical memory management via summarization thresholds and thread timeout policies.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
