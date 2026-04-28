---
repo_name: agentscope-ai/agentscope
url: "https://github.com/agentscope-ai/agentscope"
stars: 24258
forks: 2609
contributors_count: 54
last_commit_date: "2026-04-20T12:44:54+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T09:33:55.257836+00:00"
model: auto
duration_s: 84.2
clone_size_kb: 28909
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`agentscope-ai/agentscope` is a Python framework for building, running, and observing LLM agents with tool use, memory, and multi-agent workflows. A user typically instantiates `ReActAgent` (or specialized agents), connects model backends (OpenAI/DashScope/Anthropic/Gemini/Ollama), optionally registers tools (including MCP tools), and runs async loops where agents reason, call tools, and respond. The framework also includes orchestration primitives (`MsgHub`, sequential/fanout pipelines) so multiple agents can collaborate in debate, conversation, or planner-worker style tasks. In practice, you run Python scripts (examples or your own app) and get interactive agent outputs plus structured metadata/tool traces. It is more of an “agent runtime SDK” than a single app.

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework** (AgentScope), not LangGraph/LangChain/CrewAI/AutoGen as core dependencies. Core abstractions are implemented in `src/agentscope/agent`, `pipeline`, `tool`, and `model` modules; no direct framework imports were found in these core paths.

Architecture-wise, the main intelligence loop is in `ReActAgent`: it stores input into memory, optionally retrieves from long-term memory and knowledge bases, then runs iterative reasoning/tool-action loops until completion (`src/agentscope/agent/_react_agent.py:375-537`). Model calls are routed through provider adapters (`src/agentscope/model/_openai_model.py:175-343` and peers), while tool execution is mediated by `Toolkit`, which exposes JSON schemas to the LLM and executes tool calls (`src/agentscope/tool/_toolkit.py:558-619`, `851-1033`).

Multi-agent behavior is composition-based, not a fixed built-in swarm engine: agents are coordinated using `MsgHub` broadcast subscriptions (`src/agentscope/pipeline/_msghub.py:14-139`), pipeline combinators (`src/agentscope/pipeline/_functional.py:10-105`), and optional plan tools (`PlanNotebook`) injected into agents (`src/agentscope/plan/_plan_notebook.py:821-843`; registration in `src/agentscope/agent/_react_agent.py:324-348`). So the “brains” live in prompts + ReAct loop + tool schemas, while orchestration lives in pipeline/message-hub utilities and user workflow code.

## 3. Orchestration Pattern

Closest fit: **hybrid orchestration (hierarchical + event-driven broadcast + sequential/fanout composition)**.

- **Event-driven broadcast among peers:** `MsgHub` auto-subscribes participants so each agent’s reply is observed by others (`src/agentscope/pipeline/_msghub.py:89-94` + broadcast path in `src/agentscope/agent/_agent_base.py:469-486`).

```90:94:src/agentscope/pipeline/_msghub.py
if self.enable_auto_broadcast:
    for agent in self.participants:
        agent.reset_subscribers(self.name, self.participants)
```

- **Hierarchical manager-worker appears in examples:** a planner agent with `PlanNotebook` and worker creation tool (`examples/agent/meta_planner_agent/main.py:24-48`), plus plan-state tools enforcing staged execution (`src/agentscope/plan/_plan_notebook.py:433-547`, `548-651`).

```432:441:src/agentscope/agent/_react_agent.py
for _ in range(self.max_iters):
    msg_reasoning = await self._reasoning(tool_choice)
    futures = [
        self._acting(tool_call)
        for tool_call in msg_reasoning.get_content_blocks("tool_use")
    ]
```

So control flow is typically: prompt -> reason -> tool call(s) -> tool result -> next reasoning iteration, with cross-agent coordination handled externally via MsgHub/pipelines.

## 4. Tools & External Integrations

- **MCP servers/tools (including browser automation):** toolkit can register MCP tools from clients (`src/agentscope/tool/_toolkit.py:1035-1173`); stateful MCP lifecycle in `src/agentscope/mcp/_stateful_client_base.py:46-117`; stdio MCP client in `src/agentscope/mcp/_stdio_stateful_client.py:11-77`. Browser example wires Playwright MCP via `npx @playwright/mcp` (`examples/agent/browser_agent/main.py:34-44`).
- **LLM APIs:** OpenAI/Azure-compatible client adapter (`src/agentscope/model/_openai_model.py:150-169`, invocation at `175-343`), plus model module exports DashScope/Anthropic/Gemini/Ollama/Trinity (`src/agentscope/model/__init__.py:4-22`).
- **Function/tool calling runtime:** JSON-schema tool exposure and tool invocation path (`src/agentscope/tool/_toolkit.py:558-619`, `851-1033`), including async background tool tasks (`685-850`, `1536-1680`).
- **RAG pipeline components:** knowledge retrieval plugged into agent loop (`src/agentscope/agent/_react_agent.py:399-403`, `908-1014`), basic KB implementation (`src/agentscope/rag/_simple_knowledge.py:13-52`), vector stores like Qdrant/Milvus/MongoDB (`src/agentscope/rag/_store/_qdrant_store.py:18-157`, `.../_milvuslite_store.py:19-220`, `.../_mongodb_store.py:24-339`).
- **Agent-to-agent over network (A2A protocol):** remote agent communication client wrapper (`src/agentscope/agent/_a2a_agent.py:29-260`).

## 5. Notable Code Walkthrough

- `src/agentscope/agent/_react_agent.py:375-537` - Core ReAct runtime: memory update, retrieval, iterative reasoning/acting loop, tool-call execution (parallel or sequential), and structured-output completion logic. This is the primary execution engine for most agents.
- `src/agentscope/tool/_toolkit.py:274-535` and `851-1033` - Central tool registry/executor: parses functions into JSON schemas, enforces active tool groups, executes tool calls in streaming mode, and handles errors/interruption. This is how LLM “actions” become real side effects.
- `src/agentscope/pipeline/_msghub.py:14-139` - Multi-agent message bus abstraction: auto-broadcast subscription model for conversation/debate-style coordination, with optional manual broadcast.
- `src/agentscope/plan/_plan_notebook.py:232-431` and `433-737` - Planning substrate exposing plan/subtask lifecycle as callable tools (`create_plan`, `update_subtask_state`, `finish_subtask`, `finish_plan`), enabling hierarchical workflows inside a single ReAct agent.
- `examples/agent/browser_agent/browser_agent.py:90-281` and `examples/agent/browser_agent/main.py:32-57` - Specialized browser-use agent: wraps ReAct with page snapshot/screenshot logic and task decomposition; integrates Playwright MCP tools through `Toolkit.register_mcp_client`.

## 6. Use-Case Mapping

The repository **can** realize Browser/Terminal-use tasks (notably via MCP + browser example), but that is not its dominant identity. The browser path is implemented by connecting Playwright MCP tools and then letting `BrowserAgent` reason over snapshot/screenshot/tool outputs (`examples/agent/browser_agent/main.py:34-44`, `examples/agent/browser_agent/browser_agent.py:165-281`, `676-691`, `746-775`).

However, the core codebase is broader and primarily an orchestration SDK for general agent workflows (planning, multi-agent debate/conversation, tool-enabled assistants, RAG, A2A). Given the actual architecture and examples, a better primary category is **Workflow Automation** rather than Browser/Terminal Use.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong modular runtime: clean separation of agent loop, model adapters, tool execution, and orchestration primitives.
  - Practical multi-agent coordination via `MsgHub` + pipelines with async-first design.
  - Rich tool ecosystem integration: native function tools, MCP tools, middleware, async task management.
  - Built-in planning workflow (`PlanNotebook`) that encodes subtask state transitions and constraints.
  - Broad backend support (OpenAI/DashScope/Anthropic/Gemini/Ollama + multiple vector stores + A2A).

- **Limitations:**
  - No unified declarative graph/state-machine compiler (LangGraph-style) for complex control flow; orchestration is mostly imperative Python.
  - Core `ReActAgent` and browser specialization are large/complex classes, raising maintainability and reasoning burden.
  - Multi-agent coordination semantics rely heavily on user-authored prompts/workflow scripts rather than formal coordination policies.
  - Browser/terminal capability is example-driven via MCP integration, not deeply standardized as a first-class cross-provider runtime contract.
  - Some advanced flows depend on model behavior for strict JSON/tool discipline, which can be brittle.

- **Research relevance:**
  - Useful evidence of **tool-augmented ReAct loops** in production-oriented async agent runtimes.
  - Demonstrates a practical **message-hub multi-agent communication pattern** (broadcast-observe) in LLM systems.
  - Shows how **planning can be externalized as tools/state** (`PlanNotebook`) rather than hardcoded planner architecture.
  - Relevant for studying **agent interoperability** via MCP and A2A in one framework.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
