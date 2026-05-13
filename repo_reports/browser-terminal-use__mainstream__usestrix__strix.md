---
repo_name: usestrix/strix
url: "https://github.com/usestrix/strix"
stars: 24399
forks: 2704
contributors_count: 28
last_commit_date: "2026-04-22T20:37:22+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:36:18.038597+00:00"
model: auto
duration_s: 100.5
clone_size_kb: 8001
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`usestrix/strix` is a Python CLI for autonomous application security testing that launches LLM-driven agents to scan repositories, local code, URLs, and IP targets. A user runs `strix --target ...` (interactive TUI or headless CLI), and the system spins up a Docker sandbox, executes browser/terminal/python security workflows, and produces structured vulnerability findings with PoC details and remediation guidance (`strix/interface/main.py:547-645`, `strix/interface/cli.py:23-206`). The project is not a generic chat assistant: it is an orchestration runtime for coordinated security agents with delegated sub-tasks and reporting. In practice, users get real-time scan progress plus final persisted scan artifacts in `strix_runs/<run-name>` (`README.md:87-93`, `README.md:185-189`).

## 2. Agent Framework & Architecture

This repo uses a **custom multi-agent framework** (not LangGraph/CrewAI/AutoGen/LlamaIndex). Evidence: agent lifecycle/orchestration is implemented in-house in `strix/agents`, `strix/tools/agents_graph`, and `strix/tools/executor`, while model calls are handled via LiteLLM (`litellm`) rather than an agent framework abstraction (`strix/llm/llm.py:7-23`, `pyproject.toml:35-49`).

Architecture-wise, there is a root `StrixAgent` subclass over `BaseAgent` that runs an iterative LLM→tool loop (`strix/agents/StrixAgent/strix_agent.py:7-19`, `strix/agents/base_agent.py:152-229`). The “intelligence” is distributed across: (1) a large Jinja system prompt with explicit multi-agent policy and delegation rules (`strix/agents/StrixAgent/system_prompt.jinja:231-362`), (2) skill files dynamically injected into prompt context (`strix/llm/llm.py:112-142`), and (3) runtime tool observations fed back into conversation state (`strix/tools/executor.py:313-343`).

Sub-agents are created at runtime through a tool (`create_agent`) that instantiates new `StrixAgent`s, starts them on separate threads, links parent-child edges, and supports inter-agent messaging (`strix/tools/agents_graph/agents_graph_actions.py:383-493`, `:495-564`). This is a real coordinated MAS design, not just role-playing in a single prompt.

## 3. Orchestration Pattern

Closest pattern: **hierarchical manager-worker (tree of agents) with asynchronous message passing**.

- Parent-child delegation is explicit (`type: "delegation"` edges) and children report back via `agent_finish` to parent inboxes (`strix/tools/agents_graph/agents_graph_actions.py:141-144`, `:566-679`).
- Control flow is still loop-based per agent (each agent executes a local LLM/tool cycle), but system-level coordination is hierarchical rather than a graph state machine like LangGraph.

Example 1 (agent loop and tool dispatch):

```152:174:strix/agents/base_agent.py
    async def agent_loop(self, task: str) -> dict[str, Any]:
        ...
        while True:
            ...
            if self.state.should_stop():
                if not self.interactive:
                    return self.state.final_result or {}
                ...
```

```405:425:strix/agents/base_agent.py
        actions = (
            final_response.tool_invocations
            if hasattr(final_response, "tool_invocations") and final_response.tool_invocations
            else []
        )
        if actions:
            return await self._execute_actions(actions, tracer)
```

Example 2 (manager spawning worker agents):

```470:477:strix/tools/agents_graph/agents_graph_actions.py
        thread = threading.Thread(
            target=_run_agent_in_thread,
            args=(agent, state, inherited_messages),
            daemon=True,
            name=f"Agent-{name}-{state.agent_id}",
        )
        thread.start()
        _running_agents[state.agent_id] = thread
```

## 4. Tools & External Integrations

- **LLM providers via LiteLLM** (OpenAI/Anthropic/etc. through provider-agnostic config): `strix/llm/llm.py:196-293`, `pyproject.toml:36`.
- **Docker sandbox runtime** for tool isolation and shared workspace: `strix/runtime/docker_runtime.py:28-42`, `:250-290`.
- **FastAPI tool server** inside sandbox with bearer-token auth and `/execute`: `strix/runtime/tool_server.py:16-35`, `:86-124`.
- **Browser automation via Playwright** (headless Chromium, screenshots, tab/session ops, JS eval): `strix/tools/browser/browser_instance.py:9-19`, `:191-214`.
- **Terminal execution subsystem** (per-agent terminal sessions): `strix/tools/terminal/terminal_actions.py:6-25`, `strix/tools/terminal/terminal_manager.py:11-50`.
- **Python execution tooling** (custom scripts and automation) via python tool modules: `strix/tools/python/python_actions.py` (wired through `strix/tools/__init__.py:17`).
- **Web search integration** via Perplexity API (`api.perplexity.ai`): `strix/tools/web_search/web_search_actions.py:34-57`.
- **Proxy integration** (Caido ports exposed in sandbox runtime): `strix/runtime/docker_runtime.py:25`, `:140-143`, plus proxy tool modules in `strix/tools/proxy`.
- **Reporting pipeline** with CVSS scoring and dedupe checks before persisting vulnerabilities: `strix/tools/reporting/reporting_actions.py:201-339`.

## 5. Notable Code Walkthrough

- `strix/agents/base_agent.py:49-447` - Core autonomous loop: initializes agent state, streams LLM output, parses tool calls, executes tools, and updates conversation/telemetry. This is the execution kernel for every agent.
- `strix/tools/agents_graph/agents_graph_actions.py:383-493` - Creates and starts sub-agents asynchronously, inheriting context/LLM config from parent and enforcing parent-child graph semantics.
- `strix/llm/llm.py:100-237` - Builds system prompt (with skills/tool XML), handles streaming completion, normalizes/parses tool invocations, and returns structured `LLMResponse`.
- `strix/tools/executor.py:29-116` - Tool execution router deciding local vs sandbox execution, argument conversion/validation, and result shaping for the next LLM turn.
- `strix/runtime/docker_runtime.py:111-173` - Provisioning and lifecycle of sandbox containers, including tool server bootstrap and port/token management.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is partially true at tool level (Playwright browser control and terminal command execution are first-class tools: `strix/tools/browser/browser_actions.py:183-241`, `strix/tools/terminal/terminal_actions.py:6-35`). However, the repository’s primary behavior is broader: coordinated agent workflows for end-to-end security assessment, validation, reporting, and remediation orchestration.

A better top-level category is **Workflow Automation**: the core value is orchestrating specialized agents and toolchains across a security-testing workflow, with explicit delegation, messaging, and completion gates (`system_prompt.jinja:263-280`, `finish_actions.py:86-149`), not just interactive browser/terminal operation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - True runtime multi-agent coordination with explicit parent-child graph and messaging (`agents_graph_actions.py`).
  - Tight tool-grounded loop (LLM outputs must become tool invocations), reducing “chat-only” drift (`base_agent.py:405-447`, `system_prompt.jinja:370-387`).
  - Strong practical integration stack: Docker sandbox, browser automation, terminal, proxy, and reporting.
  - Built-in vulnerability reporting rigor (CVSS parsing, schema checks, deduplication) (`reporting_actions.py:21-339`).
  - Configurable for interactive and CI/headless modes with diff-scoped code review support (`interface/main.py:575-606`).

- **Limitations:**
  - Heavy behavior encoded in very large prompts/skills; policy correctness depends on prompt compliance rather than hard runtime guarantees.
  - Thread + global mutable registries (`_agent_graph`, `_agent_messages`) may be brittle under high concurrency/load.
  - Limited formal planning abstraction (no explicit typed state graph/planner comparable to LangGraph workflows).
  - Security scan domain assumptions are deeply baked into prompt/tool ecosystem, reducing transferability to non-security MAS tasks.
  - Tool invocation format relies on XML-like parsing and normalization, which can be fragile to malformed model outputs (`llm.py:229-236`).

- **Research relevance:**
  - Evidence of **hierarchical LLM MAS orchestration** with delegated workers and feedback loops in production-style code.
  - Useful case study for **tool-mediated agent reliability** (sandboxed tool execution + structured observations).
  - Demonstrates **prompt-governed role specialization** and agent identity isolation in multi-agent systems.
  - Illustrates pragmatic MAS engineering trade-offs between flexibility (prompt policies) and strict control (runtime checks).

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
