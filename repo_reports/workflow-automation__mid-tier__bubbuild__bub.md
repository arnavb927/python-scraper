---
repo_name: bubbuild/bub
url: "https://github.com/bubbuild/bub"
stars: 1273
forks: 121
contributors_count: 27
last_commit_date: "2026-04-22T21:06:22+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T15:25:44.576776+00:00"
model: auto
duration_s: 73.9
clone_size_kb: 1820
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`bub` is a hook-first agent runtime that lets users run an LLM worker from CLI (`bub chat`, `bub run`) or channel gateways (`bub gateway`) while wiring behavior through plugins and skills. At runtime, an inbound message is converted into a prompt, executed by the built-in `Agent`, and routed back to output channels through a unified framework pipeline (`src/bub/framework.py:105-140`). The core value is operational automation: one long-running assistant can call shell/filesystem/web/tape tools, discover skills, and keep session memory through tape storage (`src/bub/builtin/agent.py:87-108`, `src/bub/builtin/tools.py:70-283`). In practice, users get an extensible “agent operator” runtime rather than just a chat UI.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph, LangChain, AutoGen, CrewAI, or LlamaIndex in core code. The actual stack is a **custom framework** built on:
- `pluggy` for hook/plugin orchestration (`src/bub/framework.py:44-47`, `src/bub/hookspecs.py:16-24`)
- `republic` for LLM/tool execution and tape/memory (`src/bub/builtin/agent.py:19-31`, `pyproject.toml:22-31`)

High-level architecture: `BubFramework` runs a turn lifecycle (`resolve_session -> load_state -> build_prompt -> run_model -> save_state -> render_outbound -> dispatch_outbound`) via hook calls (`src/bub/framework.py:109-140`). Built-in hooks (`BuiltinImpl`) provide defaults for all major stages and delegate model execution to a single `Agent` object (`src/bub/builtin/hook_impl.py:159-166`). The “intelligence” lives primarily in `Agent._agent_loop()` and `Agent._run_once()` where model + tools + system prompt + skills prompt are assembled and iterated stepwise (`src/bub/builtin/agent.py:216-257`, `521-573`).

It is mostly a **single primary agent** runtime, but it includes an explicit `subagent` tool that can recursively launch another agent run with separate session/tool/skill constraints (`src/bub/builtin/tools.py:256-283`). So multi-agent behavior is optional but implemented in runtime code.

## 3. Orchestration Pattern

Closest match: **event-driven workflow automation with iterative tool-loop agent execution** (plus optional hierarchical subagent calls).

Control flow is event-driven from channels into framework tasks:

```149:153:src/bub/channels/manager.py
while True:
    message = await wait_until_stopped(self._messages.get(), stop_event)
    task = asyncio.create_task(self.framework.process_inbound(message, self._stream_output))
    task.add_done_callback(functools.partial(self._on_task_done, message.session_id))
    self._ongoing_tasks.setdefault(message.session_id, set()).add(task)
```

Inside each turn, the agent executes repeated model/tool steps until text completion, continue, or error:

```269:276:src/bub/builtin/agent.py
for step in range(1, self.settings.max_steps + 1):
    ...
    output = await self._run_once(
        tape=tape,
        prompt=next_prompt,
        model=model,
        allowed_skills=allowed_skills,
        allowed_tools=allowed_tools,
    )
```

Optional manager-worker flavor appears when the model invokes `subagent`, which starts another agent run under a derived session (`src/bub/builtin/tools.py:260-277`), but the base architecture is not a graph/state-machine framework like LangGraph.

## 4. Tools & External Integrations

- **LLM providers via OpenAI-compatible abstraction (`republic` / any-llm-sdk):** model, api_key, api_base, fallback models configured in settings and passed into `LLM(...)` (`src/bub/builtin/settings.py:34-48`, `src/bub/builtin/agent.py:603-617`).
- **Tool-calling runtime:** all tools registered in a central registry and passed to the model through `tape.run_tools_async` / `stream_events_async` (`src/bub/tools.py:13-15`, `184-199`; `src/bub/builtin/agent.py:543-561`).
- **Shell/terminal execution:** `bash`, `bash.output`, `bash.kill` tools backed by async subprocess manager (`src/bub/builtin/tools.py:70-119`, `src/bub/builtin/shell_manager.py:39-53`).
- **Filesystem editing:** `fs.read`, `fs.write`, `fs.edit` tools resolve paths relative to runtime workspace (`src/bub/builtin/tools.py:121-155`, `317-327`).
- **Web fetch / HTTP:** `web.fetch` via `aiohttp` GET (`src/bub/builtin/tools.py:240-254`).
- **Session memory / tape services:** `tape.info`, `tape.search`, `tape.reset`, `tape.handoff`, `tape.anchors` with tape store/query APIs (`src/bub/builtin/tools.py:174-238`).
- **Subagents:** `subagent` tool launches nested agent runs with per-run allowed tools/skills (`src/bub/builtin/tools.py:256-283`).
- **Channels:** CLI and Telegram adapters for inbound/outbound messaging (`src/bub/builtin/hook_impl.py:252-259`, `src/bub/channels/telegram.py:148-190`).
- **Plugin integration:** external hook plugins via Python entry points group `bub` (`src/bub/framework.py:63-87`).

No vector DB/RAG pipeline (Chroma/Pinecone/pgvector) is wired in core runtime.

## 5. Notable Code Walkthrough

- `src/bub/framework.py:105-140` - Central turn orchestrator; executes hook lifecycle and dispatches outbounds. This is the framework backbone that all channels/plugins pass through.
- `src/bub/builtin/agent.py:216-257` - Defines the iterative agent loop and step control (`max_steps`, continue/error handling, auto handoff), i.e., the main runtime reasoning/execution engine.
- `src/bub/builtin/tools.py:70-155` - Implements high-impact action tools (`bash`, `fs.read/write/edit`) that make the agent operational for workflow tasks (automation, patching, commands).
- `src/bub/builtin/tools.py:256-283` - Implements nested subagent execution with session/tool/skill scoping; this is the primary multi-agent mechanism in code.
- `src/bub/channels/manager.py:142-176` - Runs channel listeners and schedules inbound processing concurrently; shows the event-driven “message in -> turn task” production flow.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. The runtime is designed to receive human/channel tasks, execute tool-augmented LLM steps, and return outputs while persisting session context (`src/bub/framework.py:105-140`, `src/bub/builtin/agent.py:521-561`). Its built-in actions (shell, file edits, web fetch, tape management, skill loading) align directly with automating operational workflows rather than code-only generation or retrieval-centric QA (`src/bub/builtin/tools.py:70-254`). The gateway/channel architecture further supports automation across interaction surfaces (CLI + Telegram) rather than one-off chat (`src/bub/channels/manager.py:142-153`, `src/bub/channels/telegram.py:168-190`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Hook-first extension model gives clear lifecycle interception points (`src/bub/hookspecs.py:24-109`).
  - Practical tool set (shell/fs/web/tape) enables real task completion, not just conversation (`src/bub/builtin/tools.py:70-254`).
  - Built-in channel abstraction supports both local and messaging-platform operation (`src/bub/builtin/hook_impl.py:252-259`).
  - Tape handoff and auto context-overflow mitigation are operationally robust for long sessions (`src/bub/builtin/agent.py:327-353`, `445-471`).
  - Subagent capability allows constrained delegation within one runtime (`src/bub/builtin/tools.py:256-283`).

- **Limitations:**
  - No explicit planner/verifier multi-role architecture; default is one main agent loop (`src/bub/builtin/hook_impl.py:160-166`, `src/bub/builtin/agent.py:216-257`).
  - Subagent use is model-invoked and unconstrained by built-in coordination policies (no dependency graph/task board primitives) (`src/bub/builtin/tools.py:256-283`).
  - `web.fetch` is raw GET text; no richer browsing stack, search API, or structured extraction pipeline (`src/bub/builtin/tools.py:240-254`).
  - Filesystem tools can write/edit broadly; safety relies heavily on prompting/policy rather than hard sandboxing (`src/bub/builtin/tools.py:132-155`, `317-327`).
  - No native retrieval/vector-memory subsystem beyond tape history.

- **Research relevance:**
  - Evidence of a **pluginized agent runtime** where lifecycle stages are modularized via hooks.
  - Example of **tool-augmented autonomous loop** with bounded iterative control and streaming/non-streaming modes.
  - Example of **optional recursive multi-agent delegation** implemented as a callable tool rather than separate framework.
  - Useful case for studying **channel-driven, event-based deployment** of LLM agents in production-like messaging contexts.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
