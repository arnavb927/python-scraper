---
repo_name: run-llama/llama-agents
url: "https://github.com/run-llama/llama-agents"
stars: 353
forks: 62
contributors_count: 32
last_commit_date: "2026-04-22T18:29:17+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T17:26:03.361803+00:00"
model: auto
duration_s: 93.5
clone_size_kb: 19902
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`run-llama/llama-agents` is primarily an execution and serving stack for **event-driven workflows** (the `workflows` engine plus HTTP server/client/runtime layers), not an end-user “chat agent app” by itself. In practice, a user defines typed `StartEvent`/`StopEvent` workflow steps, registers them on `WorkflowServer`, and runs them over HTTP (`packages/llama-agents-server/src/llama_agents/server/server.py:29-159`, `examples/server/server_example.py:246-272`). The runtime handles scheduling, retries, persistence, streaming events, and human-in-the-loop event injection (`packages/llama-index-workflows/src/workflows/runtime/control_loop.py:121-307`, `packages/llama-agents-client/src/llama_agents/client/client.py:323-466`). So what users get is a durable workflow orchestration platform for AI/application pipelines, not a fixed multi-agent assistant product.

## 2. Agent Framework & Architecture

The actual framework used in this repo is **LlamaIndex Workflows + custom runtime wrappers**, not CrewAI/LangGraph/AutoGen. Core imports are from `workflows` (the package in this monorepo) and server wrappers around it (`packages/llama-index-workflows/src/workflows/workflow.py:41-57`, `packages/llama-agents-server/src/llama_agents/server/server.py:12-24`).  

LLM-agent primitives (`AgentWorkflow`, `FunctionAgent`, `ReActAgent`) appear mainly in **integration tests**, imported from `llama_index.core.agent.workflow` rather than implemented here (`packages/llama-agents-integration-tests/tests/conftest.py:15-22`). Those tests usually create a single agent workflow with mock LLMs (`.../conftest.py:69-85`, `116-137`), indicating this repo is mostly infrastructure that can host agentic workflows, not a repository of concrete multi-agent teams.

Architecturally, the intelligence/control is concentrated in typed event transitions and reducer-like loop logic: `@step` metadata defines accepted/returned events (`packages/llama-index-workflows/src/workflows/decorators.py:43-59`, `199-209`), then the control loop routes events to eligible steps, runs workers, and emits stream events (`packages/llama-index-workflows/src/workflows/runtime/control_loop.py:1057-1129`, `727-883`). Server/client layers expose this runtime over REST/SSE with persistence and resumability (`packages/llama-agents-server/src/llama_agents/server/_service.py:196-243`, `packages/llama-agents-client/src/llama_agents/client/client.py:357-436`).

## 3. Orchestration Pattern

Closest match: **event-driven orchestration** (with reducer/state-machine characteristics).

Control is not “manager agent delegates to worker agents”; instead events are dispatched to steps that declare compatible input types, and step outputs enqueue further events.

```1057:1113:packages/llama-index-workflows/src/workflows/runtime/control_loop.py
def _process_add_event_tick(...):
    ...
    for step_name, step_config in state.config.steps.items():
        is_accepted = type(tick.event) in step_config.accepted_events
        if is_accepted and (tick.step_name is None or tick.step_name == step_name):
            handled = True
            subcommands = _add_or_enqueue_event(...)
            commands.extend(subcommands)
```

```753:777:packages/llama-index-workflows/src/workflows/runtime/control_loop.py
if isinstance(result, StepWorkerResult):
    if isinstance(result.result, StopEvent):
        commands.append(CommandPublishEvent(event=result.result))
        commands.append(CommandCompleteRun(result=result.result))
    elif isinstance(result.result, Event):
        if isinstance(result.result, InputRequiredEvent):
            commands.append(CommandPublishEvent(event=result.result))
        commands.append(CommandQueueEvent(event=result.result, ...))
```

This is a typed event graph with async worker execution, retries, and lifecycle events—not a peer swarm.

## 4. Tools & External Integrations

- **HTTP API serving + SSE streaming**: Starlette/Uvicorn server for running workflows and streaming events (`packages/llama-agents-server/src/llama_agents/server/server.py:11-25`, `201-225`; `packages/llama-agents-client/src/llama_agents/client/client.py:323-436`).
- **Persistence backends**: abstract store interface with concrete memory/sqlite/postgres implementations for handlers/events/ticks (`packages/llama-agents-server/src/llama_agents/server/_store/abstract_workflow_store.py:110-167`; store implementations are wired in `server.py:81-115`).
- **Human-in-the-loop event injection**: client/server send external events into active runs (`packages/llama-agents-server/src/llama_agents/server/_service.py:143-167`; `packages/llama-agents-client/src/llama_agents/client/client.py:438-466`).
- **DBOS durability runtime**: optional DBOS-backed runtime for resumable workflows (`examples/dbos/durable_workflow.py:22-27`, `74-84`).
- **AWS Bedrock AgentCore integration**: adapter service around Bedrock AgentCore app + workflow runtime decorators (`packages/llama-agents-agentcore/src/llama_agents/agentcore/_service.py:1-5`, `39-61`).
- **LLM/tool calling exists mostly in tests**: mocked LlamaIndex `FunctionAgent`/`ReActAgent` and tool call events in integration tests (`packages/llama-agents-integration-tests/tests/conftest.py:15-22`, `69-85`; `.../test_event_streaming.py:57-87`).

## 5. Notable Code Walkthrough

- `packages/llama-index-workflows/src/workflows/workflow.py:41-57,322-397` — Defines the core `Workflow` abstraction (`@step` graph + `run()` entrypoint). This is the API users subclass to build orchestrations.
- `packages/llama-index-workflows/src/workflows/runtime/control_loop.py:121-130,337-555,1057-1129` — Implements the deterministic async control loop that schedules workers, pulls events, reduces ticks, and routes events through the workflow graph.
- `packages/llama-agents-server/src/llama_agents/server/server.py:29-57,104-123,138-159` — Composes runtime decorators (persistence + idle release), registers workflows, and exposes them as HTTP endpoints.
- `packages/llama-agents-server/src/llama_agents/server/_service.py:196-243` — Handles handler lifecycle (`start_workflow`, `await_workflow`) and bridges API calls to runtime operations.
- `packages/llama-agents-client/src/llama_agents/client/client.py:222-321,323-436` — Client API for sync/async runs and resilient SSE event streaming with reconnect cursor tracking.

## 6. Use-Case Mapping

The assigned label `RAG + Agents` is only **partially** supported by this repo itself. The codebase mostly provides orchestration/runtime infrastructure for arbitrary workflows (including AI ones), while concrete RAG/agent applications are largely in external templates or tests (`packages/llamactl/src/llama_agents/cli/templates.py:117-123`, integration tests).  

So this repository is better categorized as **Workflow Automation**: it operationalizes event-driven execution, durability, retries, streaming, and HITL control. It can host RAG + agent flows, but those are not the dominant in-repo implementation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong event-driven runtime with deterministic control-loop semantics and replay-oriented tick model.
  - Durable execution model (memory/sqlite/postgres stores, resumable handlers, idle release).
  - Clean API layering (workflow core vs server vs client vs runtime decorators).
  - Built-in human-in-the-loop patterns via `InputRequiredEvent`/external event injection.
  - Good test coverage around runtime behavior, failure modes, and persistence.

- **Limitations:**
  - Very few in-repo real-world multi-agent compositions; most “agent” behavior is in tests or external templates.
  - LLM integrations in this repo are mostly mocked/test-time, so limited evidence of production prompt/agent strategy.
  - No native planner-worker debate/society abstractions in core runtime; orchestration is event-step centric.
  - Complexity of runtime/store decorators may raise implementation overhead for simple use cases.

- **Research relevance:**
  - Useful evidence for **event-driven, durable orchestration** in agentic systems.
  - Useful for studying **HITL insertion points** and interrupt/resume semantics in async workflows.
  - Useful for examining **state/tick persistence and replay** as reliability mechanisms.
  - Less suitable as evidence for emergent multi-agent coordination strategies (debate/swarm/role-play).

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
