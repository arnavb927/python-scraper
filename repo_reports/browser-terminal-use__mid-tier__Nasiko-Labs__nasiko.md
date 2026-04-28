---
repo_name: Nasiko-Labs/nasiko
url: "https://github.com/Nasiko-Labs/nasiko"
stars: 1557
forks: 104
contributors_count: 9
last_commit_date: "2026-04-13T14:11:31+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 7
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T11:39:34.927629+00:00"
model: auto
duration_s: 80.2
clone_size_kb: 4386
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

Nasiko is a control-plane platform for deploying and operating many AI agent services, then routing user requests to the best one at runtime. In practice, users run a multi-service stack (`docker compose ... up`) that includes a FastAPI backend, a router service, gateway, registry, and sample agents; then they query through a single router endpoint or gateway URL. The platform fetches registered `AgentCard` metadata, ranks candidate agents, selects one with an LLM-based router, and forwards the request to that agent. Users get centralized lifecycle management (upload/deploy/update), intelligent dispatch, and observability for a heterogeneous agent fleet rather than a single monolithic assistant.

## 2. Agent Framework & Architecture

The repo uses **LangChain** (not LangGraph/CrewAI/AutoGen/LlamaIndex in the inspected runtime code) for routing: `ChatOpenAI`, prompt templates, embeddings, and FAISS-based retrieval (`agent-gateway/router/src/core/routing_engine.py:11-16`, `:34-65`, `:183-263`). The agent services themselves use **A2A SDK** + OpenAI Chat Completions loops for tool-calling executors (`agents/a2a-github-agent/src/openai_agent_executor.py:6-17`, `:67-153`; similar in translator/compliance agents).

Architecture is split into:  
1) a **router orchestrator** service that fetches agent cards, builds vector search context, reads session history, chooses an agent, and forwards the request (`agent-gateway/router/src/services/router_orchestrator.py:25-176`);  
2) multiple **independent agent microservices** (GitHub/compliance/translator) with their own prompts/tools and A2A servers (`agents/a2a-github-agent/src/__main__.py:48-96`, `agents/a2a-translator/src/openai_agent.py:4-40`);  
3) control-plane backend/orchestrator services for deployment and registry updates via Redis streams (`app/service/orchestration_service.py:13-113`).

The “intelligence” is concentrated in two places: routing prompt + semantic shortlist in `routing_engine.py` (`:290-325`, `:183-263`), and each agent’s local system prompt/tool loop (`agents/*/src/openai_agent.py`, `agents/*/src/openai_agent_executor.py`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)** with retrieval-augmented routing. A central router “manager” selects one worker agent per request, then delegates execution.

Control flow in router pipeline (registry -> vector store -> history -> LLM selection -> dispatch):  
```python
# agent-gateway/router/src/services/router_orchestrator.py
agent_cards = await self.agent_registry.fetch_agent_cards(token)
vectorstore = self.vector_store.create_vector_store(agent_cards)
response = await self.session_history_service.fetch_session_history(token, request.session_id)
_, _, _, router_output = router(request.query, conversation_history, truncated_agent_cards, vectorstore)
agent_url = await self._get_agent_url(agent_cards, agent_name)
agent_data = await self.agent_client.send_request(agent_url, request, files, token)
```
(`router_orchestrator.py:77-78`, `:111-112`, `:122-128`, `:140-142`, `:164-174`, `:198-203`)

LLM-based final selection over shortlisted agents:  
```python
# agent-gateway/router/src/core/routing_engine.py
prompt_template = ChatPromptTemplate.from_messages(
    [SystemMessage(content=system_prompt), ("human", user_prompt)]
)
response = self.llm.invoke(prompt)
```
(`routing_engine.py:302-304`, `:318-324`)

## 4. Tools & External Integrations

- **LLM providers (OpenAI/OpenRouter/MiniMax)**: router LLM instantiation and provider switching in `agent-gateway/router/src/core/routing_engine.py:34-65`.
- **Embeddings + vector search (OpenAI or Jina embeddings, FAISS)**: `agent-gateway/router/src/core/vector_store.py:8-10`, `:30-49`, `:83-85`; semantic reranking in `routing_engine.py:183-263`.
- **Agent registry API (backend HTTP)**: fetches available agent cards from backend endpoint in `agent-gateway/router/src/core/agent_registry.py:48-73`.
- **Session/chat history API**: conversation context retrieval in `agent-gateway/router/src/core/session_history.py:43-64`.
- **Agent-to-agent HTTP forwarding**: router posts request payloads to selected agent URLs via `httpx` in `agent-gateway/router/src/core/agent_client.py:45-97`.
- **A2A protocol server runtime for agents**: agent app bootstrap with `A2AStarletteApplication` in `agents/a2a-github-agent/src/__main__.py:7-10`, `:88-93`.
- **GitHub API integration (tooling inside GitHub agent)**: PyGitHub-based tools in `agents/a2a-github-agent/src/github_toolset.py:6-7`, `:84-281`.
- **Web fetching/translation stack (translator agent)**: requests + BeautifulSoup + Google Translate endpoint in `agents/a2a-translator/src/translator_toolset.py:1`, `:149-171`, `:93-127`.
- **Redis Streams for deployment orchestration (control plane)**: publish orchestration commands in `app/service/orchestration_service.py:19-20`, `:98-103`.

## 5. Notable Code Walkthrough

- `agent-gateway/router/src/services/router_orchestrator.py:25-176` - Core runtime coordinator for request handling; this is where the end-to-end routing sequence is executed and where delegation to a selected agent actually happens.
- `agent-gateway/router/src/core/routing_engine.py:27-357` - Implements semantic shortlist + LLM decision logic, including provider abstraction and structured output (`RouterOutput`) for agent selection.
- `agent-gateway/router/src/core/agent_client.py:21-213` - Handles network dispatch to chosen agents, auth header forwarding, URL translation for container networking, and response normalization.
- `agents/a2a-github-agent/src/openai_agent_executor.py:23-253` - Representative single-agent execution loop: repeated OpenAI calls with function/tool invocation until final answer or max iterations.
- `agents/a2a-github-agent/src/__main__.py:48-96` - Shows how an agent is declared (AgentCard/skills/capabilities), wrapped in A2A server handlers, and exposed as an addressable worker service.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is not the best fit for the core system behavior. This repo primarily implements **workflow automation for agent operations**: uploading agents, orchestrating deployments, registry management, and runtime routing of user tasks to specialized agent services. Although individual sample agents may fetch web pages or call APIs, the platform itself is not a browser/terminal automation agent in the sense of controlling a browser session or shell directly. A better category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear separation of concerns between control plane, router, and agent runtimes (`router_orchestrator.py`, `orchestration_service.py`, `agents/*`).
  - Practical hybrid routing strategy (embedding shortlist + LLM final choice) rather than naive prompt-only routing (`routing_engine.py:183-263`, `:270-325`).
  - Provider-flexible routing stack (OpenAI/OpenRouter/MiniMax) with structured output enforcement (`routing_engine.py:45-65`).
  - Concrete, runnable multi-agent deployment pattern via A2A-compatible microservices and registry-discovered endpoints (`__main__.py`, `agent_registry.py`).
  - Real production-oriented plumbing (Redis streams, gateway integration, auth forwarding, health checks).

- **Limitations:**
  - Router selects a **single** agent per request; no multi-step inter-agent collaboration, debate, or parallel worker composition (`router_orchestrator.py:140-176`).
  - Heavy dependence on agent card metadata quality; weak cards can degrade routing quality (vectorization uses descriptions directly, `vector_store.py:113-126`).
  - Tool schemas in sample executors are inferred from signatures/docstrings and may be shallow for robust function-calling (`openai_agent_executor.py:175-227`).
  - Several production concerns are placeholders/minimal (e.g., static `/metrics` response in `main.py:124-133`).
  - Limited explicit evaluation harness for routing accuracy in runtime code path.

- **Research relevance:**
  - Evidence of a real-world **agent control-plane** architecture combining lifecycle management with LLM routing.
  - Example of **hierarchical agent dispatch** (router as manager, specialized agents as workers) in microservice form.
  - Useful case study for **hybrid retrieval+LLM routing** over dynamic agent registries.
  - Demonstrates A2A-style interoperability patterns for heterogeneous agent services.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
