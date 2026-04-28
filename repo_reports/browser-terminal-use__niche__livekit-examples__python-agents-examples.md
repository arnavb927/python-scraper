---
repo_name: livekit-examples/python-agents-examples
url: "https://github.com/livekit-examples/python-agents-examples"
stars: 266
forks: 123
contributors_count: 13
last_commit_date: "2026-04-16T20:12:54+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 5
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T14:39:02.192039+00:00"
model: auto
duration_s: 87.3
clone_size_kb: 221128
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a large collection of runnable Python examples for building LiveKit-based voice/video/telephony agents, from minimal single-agent demos to complex multi-agent applications. A user typically runs a script like `python .../agent.py dev` (or `console`) to start a real-time conversational agent session connected to a LiveKit room. The runtime pattern is usually STT -> LLM -> TTS with optional tool calling, handoffs, and event hooks. In advanced examples (e.g., triage, booking, shopping, research), users get specialized role-based agents that can transfer control, call external APIs, and maintain shared session state across a workflow.

## 2. Agent Framework & Architecture

The primary framework is **LiveKit Agents (custom LiveKit agent runtime)**, not LangGraph/CrewAI as the core architecture. This is evident from pervasive imports such as `from livekit.agents ...`, `livekit.agents.voice.AgentSession`, and `@function_tool` (e.g., `docs/examples/agent_transfer/agent_transfer.py:17-18`, `complex-agents/medical_office_triage/triage.py:23-27`, `complex-agents/doheny-surf-desk/agent.py:22-24`).  

LangChain/LangGraph appear only as **integration examples**, not the repository’s main orchestration engine. For instance, `docs/examples/langchain_langgraph/langchain_langraph.py:21-22` builds a `StateGraph` and then adapts it via `langchain.LLMAdapter` into a LiveKit session (`...:81-84`).

Architecturally, most “multi-agent” apps define several specialized `Agent` subclasses (triage/support/billing; frontdesk/intake/scheduler/gear/billing), store them in shared `userdata.personas`, and route between them using function tools that return/swap the next agent (`complex-agents/personal_shopper/personal_shopper.py:403-407`, `...:134-141`; `complex-agents/medical_office_triage/triage.py:181-185`, `...:101-109`). The “intelligence” lives in role-specific prompt files plus tool schemas and handoff logic; a few apps add supervisory LLM loops (e.g., EXA researcher iterative supervisor in `complex-agents/exa-deep-researcher/orchestrator.py:159-177`).

## 3. Orchestration Pattern

Closest match: **hierarchical / manager-worker workflow with event-driven elements**.

- In many examples, a primary role routes to specialist agents via tool-triggered handoffs (manager-worker flavor). Example: `FrontDeskAgent.start_booking()` returns `IntakeAgent`, effectively transferring control (`complex-agents/doheny-surf-desk/agents/frontdesk_agent.py:25-45`).
- Session-level event listeners add event-driven behavior, especially observer/guardrail logic. The observer listens for `conversation_item_added`, periodically evaluates safety via a separate LLM call, and injects system hints into the active agent context (`complex-agents/doheny-surf-desk/agents/observer_agent.py:58-83`, `...:278-302`).

Control flow is therefore not a LangGraph state machine at the core; it is LiveKit session orchestration with function-tool handoffs plus asynchronous event callbacks.

## 4. Tools & External Integrations

- **LLM/STT/TTS providers via LiveKit plugins**: OpenAI, Deepgram, Cartesia, Silero VAD, etc., wired directly in `AgentSession(...)` (e.g., `docs/examples/agent_transfer/agent_transfer.py:74-80`, `complex-agents/doheny-surf-desk/agent.py:79-86`).
- **MCP servers (remote HTTP + local stdio)**:  
  - HTTP MCP: `mcp.MCPServerHTTP(url="https://shayne.app/mcp")` in `docs/examples/http_mcp_client/http_mcp_client.py:56-57`.  
  - Stdio MCP: `mcp.MCPServerStdio(command="codex", args=["mcp"])` in `docs/examples/stdio_mcp_client/stdio_mcp_client.py:61`.
- **Vector/RAG stack**: Annoy index + OpenAI embeddings for retrieval in `docs/examples/rag/main.py:37`, `...:87-103`, `...:171-185`.
- **External HTTP APIs**: Open-Meteo weather fetch using `aiohttp` in `complex-agents/doheny-surf-desk/tools/tide_tools.py:12-30`.
- **EXA research integration**: Research orchestration uses an EXA client and iterative LLM supervision in `complex-agents/exa-deep-researcher/orchestrator.py:15-25`, `...:257-265`.
- **Frontend/browser control via RPC**: Shopify agent sends navigation RPC (`client.navigate`) to a frontend, effectively steering browser UI from agent tool calls (`complex-agents/shopify-voice-shopper/shopify.py:167-173`, `...:178-189`).

## 5. Notable Code Walkthrough

- `complex-agents/personal_shopper/personal_shopper.py:74-142,393-415`  
  Defines a reusable base handoff pattern (context truncation + transfer) and wires triage/sales/returns agents into one shared `AgentSession`, making it a canonical multi-agent implementation in this repo.

- `complex-agents/medical_office_triage/triage.py:47-71,101-129,174-193`  
  Shows clean department routing with context preservation (`prev_agent` + chat history merge), then starts with triage and transitions through tool-based transfers.

- `complex-agents/doheny-surf-desk/agent.py:43-53,88-105`  
  Demonstrates a fuller production-style setup: five task-focused agents plus a parallel observer, with shared userdata and LiveKit room/session configuration.

- `complex-agents/doheny-surf-desk/agents/observer_agent.py:58-83,84-123,278-302`  
  Implements background governance: event subscription, periodic LLM evaluation, JSON parsing, and guardrail hint injection into the currently active agent.

- `docs/examples/langchain_langgraph/langchain_langraph.py:48-63,81-84`  
  Important as a bridge example: LangGraph is used only as an optional LLM backend workflow, then adapted into LiveKit through `langchain.LLMAdapter`.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially accurate. There are browser-adjacent elements (e.g., Shopify example RPC navigation and MCP/Codex integrations: `complex-agents/shopify-voice-shopper/shopify.py:167-173`, `docs/examples/stdio_mcp_client/stdio_mcp_client.py:61`), but the repository’s dominant behavior is **voice-driven operational workflows**: triage, booking, customer support, research orchestration, and telephony routing.  

A better primary category is **Workflow Automation** because most representative multi-agent examples encode business process steps, specialized role handoffs, and tool-mediated task execution rather than generic browser/terminal operation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong breadth of real runnable patterns, from minimal to production-like multi-agent workflows.
  - Clear handoff primitives (`update_agent` / returning next `Agent`) with shared state patterns across examples.
  - Good demonstration of hybrid orchestration (role handoffs + event-driven observer/guardrails).
  - Rich integrations (MCP, EXA, RAG/vector retrieval, telephony, frontend RPC) in practical code.
  - Voice-first constraints are consistently encoded in prompts/tool outputs.

- **Limitations:**
  - Repository is example-centric; architecture is fragmented across many demos rather than one cohesive framework.
  - Many workflows rely heavily on prompt behavior and ad hoc heuristics (limited formal verification/safety guarantees).
  - Persistence/backends are often mock or lightweight (e.g., mock booking/weather paths), reducing production realism.
  - Limited standardized evaluation/benchmarking for multi-agent quality across examples.
  - Some advanced orchestration logic lives in imperative code, making formal state reasoning harder than explicit graphs.

- **Research relevance:**
  - Evidence of practical multi-agent coordination in real-time voice environments (handoffs, shared context, role specialization).
  - Useful case studies for event-driven guardrails and observer-agent oversight in conversational systems.
  - Demonstrates tool-augmented agent ecosystems (MCP + APIs + RAG) in applied workflow settings.
  - Illustrates how “agentic” behavior is often achieved via framework-native primitives instead of explicit MAS graph frameworks.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
