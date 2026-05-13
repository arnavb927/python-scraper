---
repo_name: langchain-ai/langchain
url: "https://github.com/langchain-ai/langchain"
stars: 134556
forks: 22238
contributors_count: 3672
last_commit_date: "2026-04-23T00:34:21+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 9
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents]
generated_at: "2026-05-05T06:20:18.285173+00:00"
model: auto
duration_s: 100.4
clone_size_kb: 50796
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`langchain-ai/langchain` is a Python framework for building LLM applications, with its current agent runtime centered in `libs/langchain_v1`. In practice, users run `create_agent(...)` with a chat model plus tools, then call `.invoke()`, `.stream()`, or async variants to execute an iterative tool-using agent loop (`libs/langchain_v1/langchain/agents/factory.py:691-835`). The repo also contains a legacy agent stack (`langchain_classic`) with `AgentExecutor`, but that path is explicitly older and maintained for compatibility (`libs/langchain/langchain_classic/agents/agent.py:1012-1623`). The result users get is a configurable agent workflow with middleware hooks, persistence options, and model/provider integrations rather than a single fixed chatbot.

## 2. Agent Framework & Architecture

The active framework is **LangChain agents built on LangGraph** (not CrewAI/AutoGen/LlamaIndex). This is confirmed directly in code imports: `StateGraph`, `ToolNode`, `Command`, `Send` from `langgraph` in the core factory (`libs/langchain_v1/langchain/agents/factory.py:22-27`), and the package entrypoint exporting `create_agent` from that module (`libs/langchain_v1/langchain/agents/__init__.py:3-9`).

High-level architecture: `create_agent` compiles a **state graph** with model node(s), optional tools node, and optional middleware nodes before/after agent/model calls (`libs/langchain_v1/langchain/agents/factory.py:1033-1668`). “Intelligence” is distributed across (a) the underlying LLM call, (b) tool-calling decisions inferred from model outputs, and (c) middleware that can rewrite requests/responses, inject prompts, or alter control flow (`libs/langchain_v1/langchain/agents/middleware/types.py:380-577`).

Multi-agent capability exists as **composable subgraphs**, not a mandatory built-in supervisor abstraction. The agent `name` is documented as useful when embedding one agent graph inside another for multi-agent systems (`libs/langchain_v1/langchain/agents/factory.py:796-801`), and tracing metadata distinguishes root/subagent roles (`libs/langchain_v1/langchain/agents/factory.py:1650-1656`, `libs/langchain_v1/tests/unit_tests/agents/test_injected_runtime_create_agent.py:917-950`).

## 3. Orchestration Pattern

Closest match: **graph (LangGraph-style state machine)** with iterative tool loop and conditional routing.

Control flow is explicit graph wiring:

```text
libs/langchain_v1/langchain/agents/factory.py:1490-1504
graph.add_edge(START, entry_node)
...
graph.add_conditional_edges(
    "tools",
    RunnableCallable(_make_tools_to_model_edge(...), trace=False),
    tools_to_model_destinations,
)
```

And routing logic checks tool calls / exit conditions:

```text
libs/langchain_v1/langchain/agents/factory.py:1732-1749
if len(last_ai_message.tool_calls) == 0:
    return end_destination
...
if pending_tool_calls:
    return [Send("tools", [tool_call]) for tool_call in pending_tool_calls]
```

So runtime is not peer-to-peer swarm; it is a directed graph with conditional transitions and loopbacks between `model` and `tools`, plus middleware jump points (`jump_to`) (`libs/langchain_v1/langchain/agents/factory.py:1713-1821`).

## 4. Tools & External Integrations

- **LLM providers (OpenAI, Anthropic, Google, Groq, Ollama, etc.)** via unified model init registry in `init_chat_model` (`libs/langchain_v1/langchain/chat_models/base.py:38-77`, `:210-220`).
- **User-defined tools / callables / tool dicts** wired into LangGraph `ToolNode` during agent creation (`libs/langchain_v1/langchain/agents/factory.py:927-946`).
- **Provider-side built-in tools** (dict-style tool specs passed through to model binding) handled alongside client-side tools (`libs/langchain_v1/langchain/agents/factory.py:929-955`, `:1266-1274`).
- **Shell/terminal execution** through `ShellToolMiddleware`, including persistent sessions and security policies (`HostExecutionPolicy`, `CodexSandboxExecutionPolicy`, `DockerExecutionPolicy`) (`libs/langchain_v1/langchain/agents/middleware/shell_tool.py:489-592`, `libs/langchain_v1/langchain/agents/middleware/_execution.py:91-385`).
- **Human approval interrupts (HITL)** using LangGraph `interrupt(...)` after model tool-call generation (`libs/langchain_v1/langchain/agents/middleware/human_in_the_loop.py:313-399`).
- **State persistence / memory infrastructure** through LangGraph `checkpointer`, `store`, and `cache` parameters in `create_agent` (`libs/langchain_v1/langchain/agents/factory.py:700-707`, `:1660-1668`).
- **Legacy agent integrations** (classic stack) still support tool ecosystems via `AgentExecutor` but are compatibility-oriented (`libs/langchain/langchain_classic/agents/agent.py:1012-1110`).

## 5. Notable Code Walkthrough

- `libs/langchain_v1/langchain/agents/factory.py:691-1668`  
  Core modern runtime. Builds and compiles the LangGraph state machine, binds tools and model strategies, wires conditional edges, and defines loop/exit behavior.

- `libs/langchain_v1/langchain/agents/middleware/types.py:350-577`  
  Defines `AgentState`, `AgentMiddleware`, and model/tool interception APIs (`wrap_model_call`, `wrap_tool_call`) where most customization of agent behavior is designed to happen.

- `libs/langchain_v1/langchain/agents/middleware/shell_tool.py:489-883`  
  Shows concrete “agentic action” integration: a persistent shell tool with startup/shutdown lifecycle, output truncation, timeout handling, and optional PII redaction.

- `libs/langchain_v1/langchain/agents/middleware/human_in_the_loop.py:182-413`  
  Implements human-governed tool execution by interrupting after model planning, collecting human decisions (`approve/edit/reject/respond`), then rewriting tool calls/messages.

- `libs/langchain/langchain_classic/agents/agent.py:1012-1695`  
  Legacy but instructive baseline: explicit while-loop agent executor with plan-act-observe iterations, tool dispatch, stopping rules, and async parallel tool execution.

## 6. Use-Case Mapping

The assigned primary use case **Code Generation** is not the best fit for this repository as a whole. The repo implements a **general agent orchestration framework**: tool-calling loops, middleware policies, graph routing, persistence, HITL, and execution controls. While code generation can be one downstream application (especially with shell/code tools), the core code is broader and infrastructure-like.

A better category is **Workflow Automation**: the code is primarily about orchestrating multi-step, tool-augmented workflows with conditional control flow (`factory.py` graph edges), middleware governance (`types.py`, `human_in_the_loop.py`), and runtime execution policies (`shell_tool.py`, `_execution.py`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong, explicit graph orchestration model with inspectable conditional transitions (`factory.py`).
  - Middleware architecture is unusually extensible (before/after hooks + wrapper interception for model and tools).
  - Production-oriented controls: persistence (`checkpointer`/`store`), caching, interrupts, and tracing metadata.
  - Security-aware terminal tooling with selectable isolation modes (host/sandbox/docker) and redaction hooks.
  - Backward compatibility preserved via `langchain_classic`, easing migration while evolving architecture.

- **Limitations:**
  - No single canonical built-in “multi-agent manager” primitive in this repo segment; multi-agent is compositional rather than turnkey.
  - Complexity is high: many extension points increase cognitive load and risk of misconfiguration.
  - Some multi-agent-oriented tests/examples are commented out in current test files (`test_react_agent.py`), reducing executable exemplars.
  - Provider/tool behavior can vary across integrations, so runtime semantics are not fully uniform.
  - Legacy and modern stacks coexist, which may fragment best-practice discovery for new users.

- **Research relevance:**
  - Evidence of **graph-based agent orchestration** as a practical alternative to linear planner-executor loops.
  - Demonstrates **policy-layered agency** (middleware) where control logic is separable from base LLM policy.
  - Useful case for studying **human-in-the-loop intervention points** in agent execution pipelines.
  - Shows how modern agent systems mix **LLM planning + deterministic control + external tool actions** in one runtime.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
