---
repo_name: openai/openai-agents-python
url: "https://github.com/openai/openai-agents-python"
stars: 24705
forks: 3777
contributors_count: 256
last_commit_date: "2026-04-23T02:19:40+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T10:38:11.895404+00:00"
model: auto
duration_s: 109.7
clone_size_kb: 21171
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`openai-agents-python` is an SDK for building LLM-driven workflows where one or more agents run in a turn loop, call tools, optionally hand off to other agents, and return structured or text outputs. In practice, users instantiate `Agent(...)` objects, attach tools/handoffs/guardrails, and execute with `Runner.run(...)` or `Runner.run_streamed(...)` (`src/agents/agent.py`, `src/agents/run.py`). The runtime handles model calls, tool execution, approvals, interruptions/resume state, and tracing, rather than forcing users to wire these manually. The result is a programmable automation framework: you give it a task and configured agent graph, and it executes until final output or an approval/error boundary.

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework** (the OpenAI Agents SDK itself), not LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex. I found no imports of those frameworks in source (`rg` over `src/**`). Core objects are first-party: `Agent`, `Handoff`, `Runner`, `RunState`, and tool classes in `src/agents/*`.

Architecture-wise, intelligence is distributed across (a) per-agent prompts/instructions and output schemas, (b) runtime orchestration logic, and (c) model-native tool/handoff selection. Agents are declarative dataclasses with `instructions`, `tools`, `handoffs`, `guardrails`, and `model_settings` (`src/agents/agent.py:223-323`). Handoffs are encoded as callable tool surfaces that transfer control to another agent (`src/agents/handoffs/__init__.py:94-122`, `:222-335`).

Execution lives in `AgentRunner.run` and `run_internal` modules: each turn calls the model, processes output items (messages, tool calls, handoff calls), executes side effects, then chooses next step (`run again` / `handoff` / `final output` / `interruption`) (`src/agents/run.py:434-1479`, `src/agents/run_internal/turn_resolution.py:547-717`).

## 3. Orchestration Pattern

Closest fit: **hierarchical workflow orchestration with evented turn-loop semantics** (manager-worker style via handoffs/tools), rather than graph-state DSL like LangGraph.

Control flow is explicit in the runner loop:

```193:220:src/agents/run.py
class Runner:
    async def run(...):
        """
        The agent will run in a loop until a final output is generated...
          1. The agent is invoked...
          2. If there is a final output ... terminate.
          3. If there's a handoff, we run the loop again, with the new agent.
          4. Else, we run tool calls (if any), and re-run the loop.
        """
```

Handoff resolution actively switches the current agent and returns `NextStepHandoff`:

```323:336:src/agents/run_internal/turn_resolution.py
async def execute_handoffs(...):
    ...
    new_agent: Agent[Any] = await handoff.on_invoke_handoff(...)
    ...
    return SingleStepResult(..., next_step=NextStepHandoff(new_agent), ...)
```

This is not peer-to-peer swarm messaging; one active agent controls each turn, and handoffs/tool calls route work to specialists.

## 4. Tools & External Integrations

- **OpenAI Responses API (primary model backend)**: request construction, tool serialization, streaming/non-streaming transport in `src/agents/models/openai_responses.py:377-506`, `:689-833`, `:1825-2046`.
- **Web search**: hosted `WebSearchTool` class and conversion to Responses payload in `src/agents/tool.py:559-583` and `src/agents/models/openai_responses.py:1963-1975`.
- **File/vector search (RAG primitive)**: `FileSearchTool` wraps vector store IDs (`src/agents/tool.py:533-556`), with example indexing/search flow in `examples/tools/file_search.py:13-48`.
- **MCP integrations**:
  - Remote hosted MCP tool (`HostedMCPTool`) in `src/agents/tool.py:825-843`.
  - Local/managed MCP servers (`MCPServerStdio`, `MCPServerSse`, `MCPServerStreamableHttp`) in `src/agents/mcp/server.py`.
  - MCP approvals handled in runtime planning/resolution (`src/agents/run_internal/turn_resolution.py:1642-1665`).
- **Shell/terminal execution**: `ShellTool` and `LocalShellTool` abstractions in `src/agents/tool.py:885-899`, `:1081-1127`; execution planned/resolved in `run_internal` (`src/agents/run_internal/turn_resolution.py`).
- **Computer-use automation**: `ComputerTool` with safety checks (`src/agents/tool.py:586-610`, `:711-724`), serialized as Responses computer tool (`src/agents/models/openai_responses.py:1928-1997`).
- **Code execution and generation tools**: `CodeInterpreterTool`, `ImageGenerationTool`, `ApplyPatchTool`, `CustomTool` in `src/agents/tool.py:846-867`, `:1129-1189`.
- **Session/conversation persistence**: OpenAI conversation IDs and local sessions integrated in `src/agents/run.py:504-576`, `:541-560`.

## 5. Notable Code Walkthrough

- `src/agents/agent.py:223-323`  
  Defines the core `Agent` abstraction (instructions, tools, handoffs, guardrails, output schema, tool-use behavior). This is the fundamental configuration surface users program against.

- `src/agents/run.py:434-1479`  
  Main non-streaming runtime loop (`AgentRunner.run`) that manages turns, guardrails, tool setup, handoffs, interruptions, session persistence, and finalization.

- `src/agents/run_internal/turn_resolution.py:1420-1912`  
  Converts raw model outputs into executable actions, dispatches tool/handoff execution, and determines next step (`NextStepRunAgain`, `NextStepHandoff`, `NextStepFinalOutput`, `NextStepInterruption`).

- `src/agents/models/openai_responses.py:1825-2046`  
  Bridges SDK-level tools/handoffs to OpenAI Responses API tool schemas and request payloads; this is where backend capabilities are concretely wired.

- `examples/research_bot/manager.py:52-131`  
  Representative orchestration example: planner agent creates search plan, multiple search agents run in parallel, writer agent synthesizes final report. Shows real multi-agent workflow composition.

## 6. Use-Case Mapping

The repo **can implement RAG + Agents**, but that is one slice of a broader automation SDK. RAG appears through `FileSearchTool` and vector-store-backed retrieval (`src/agents/tool.py:533-556`; `examples/tools/file_search.py:32-48`). Multi-agent coordination appears via handoffs and multi-role compositions (`src/agents/handoffs/__init__.py`, `examples/sandbox/handoffs.py:79-94`).

After reading runtime code, the stronger primary category is **Workflow Automation**: the core engine is a generalized turn-based orchestrator for tool calling, approvals, routing/handoffs, and resumable execution across many task types (research, code tasks, shell/computer ops, MCP, etc.), not just retrieval-centric pipelines.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Unified runtime supports multi-agent handoffs, tool execution, approvals, and resume state in one loop (`src/agents/run.py`, `run_internal/*`).
  - Strong tool surface breadth (web/file search, MCP, shell, computer use, code interpreter, apply_patch).
  - Explicit interruption/approval model and resumability (`RunState`) is robust for real-world human-in-the-loop systems.
  - Streaming and non-streaming paths are both first-class and kept behaviorally aligned.
  - Clear typed abstractions (Pydantic/dataclasses) for structured outputs and tool schemas.

- **Limitations:**
  - No declarative graph DSL/planner language; orchestration is imperative runtime behavior, which can be harder to visualize than graph frameworks.
  - Tight coupling to OpenAI Responses API semantics for many advanced features (tool search namespaces, hosted tools).
  - Complexity of runtime internals is high; debugging deep turn-resolution edge cases likely requires intimate code knowledge.
  - Tool-search and deferred-loading behavior includes backend-specific constraints that may surprise users.
  - Multi-agent collaboration is largely handoff-based (single active agent per turn), not richer decentralized swarm protocols.

- **Research relevance:**
  - Good evidence of production-grade **manager-worker/handoff** orchestration patterns for LLM agents.
  - Useful case study in integrating approvals, safety guardrails, and resumable execution into agent loops.
  - Demonstrates practical coupling between model-native tool APIs and SDK-level orchestration abstractions.
  - Relevant for studies on reliability tradeoffs in multi-step agent systems with external tools.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
