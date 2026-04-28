---
repo_name: openai/openai-agents-js
url: "https://github.com/openai/openai-agents-js"
stars: 2816
forks: 705
contributors_count: 87
last_commit_date: "2026-04-21T01:55:29+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T13:59:37.493220+00:00"
model: auto
duration_s: 75.5
clone_size_kb: 9204
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`openai-agents-js` is a TypeScript SDK/monorepo for building LLM-driven agent workflows, not a single end-user app. A developer defines one or more `Agent` objects (instructions, model, tools, handoffs, guardrails), then runs them through `run()`/`Runner.run()` to execute multi-step tasks. At runtime, the SDK loops through model responses, executes tool calls (function/shell/computer/apply_patch/hosted tools), handles approvals/interruptions, and either produces final output or hands off to another agent. Users typically run their own script/app (examples show research and financial workflows) and get structured outputs or reports with traceable intermediate steps.

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework** (OpenAI Agents SDK), not LangGraph/LangChain/AutoGen/CrewAI. The core primitives are implemented directly in this codebase: `Agent`, `Handoff`, `Runner`, tool abstractions, and turn-resolution logic (`packages/agents-core/src/agent.ts`, `packages/agents-core/src/run.ts`, `packages/agents-core/src/runner/*`).

Architecture is centered on a **turn-based runtime loop**. `Runner.run()` initializes state, prepares model input, calls the model, parses model outputs into actionable items (messages, tool calls, handoffs, approvals), executes side effects, then decides next step (`run again`, `handoff`, `interruption`, `final output`) (`packages/agents-core/src/run.ts:403-411`, `packages/agents-core/src/runner/turnResolution.ts:631-855`). Intelligence is distributed across:
- per-agent prompts/instructions (`Agent.instructions`),
- model output interpretation (`processModelResponse*`),
- orchestration policy (`resolveTurnAfterModelResponse`),
- optional guardrails and approvals.

The framework supports true multi-agent coordination through two mechanisms: **handoffs** (agent takeover with conversation continuity) and **agent-as-tool** (nested agent execution as a callable tool) (`packages/agents-core/src/agent.ts:596-603`, `packages/agents-core/src/handoff.ts:86-90`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with iterative event-loop execution**.

Why: one active agent runs at a time, but it can delegate to sub-agents via handoff or invoke specialist agents as tools; control returns to the loop and continues until completion. This is not a peer swarm and not a LangGraph-style explicit DAG/state graph API.

Short excerpts showing control flow:

```403:411:packages/agents-core/src/run.ts
 * 1. The agent is invoked with the given input.
 * 2. If there is a final output ... the loop terminates.
 * 3. If there's a handoff, we run the loop again, with the new agent.
 * 4. Else, we run tool calls (if any), and re-run the loop.
```

```736:748:packages/agents-core/src/runner/turnResolution.ts
// process handoffs
if (processedResponse.handoffs.length > 0) {
  return await executeHandoffCalls(...);
}
...
if (processedResponse.hasToolsOrApprovalsToRun()) {
  return new SingleStepResult(..., { type: 'next_step_run_again' });
}
```

Also visible in example-level manager-worker composition where a manager orchestrates planner/search/writer/verifier agents (`examples/financial-research-agent/manager.ts:20-106`).

## 4. Tools & External Integrations

- **OpenAI model APIs (Responses/Chat/streaming)**: model invocation and retries in runner/model modules (`packages/agents-core/src/run.ts`, `packages/agents-openai/src/openaiResponsesModel.ts`, `packages/agents-openai/src/openaiChatCompletionsModel.ts`).
- **Hosted OpenAI tools** (`web_search`, `file_search` via vector stores, `code_interpreter`, `image_generation`, `tool_search`, hosted MCP): tool constructors and provider payload mapping (`packages/agents-openai/src/tools.ts:35-279`, `:894-1031`).
- **MCP servers (local/remote)**: stdio, SSE, streamable HTTP MCP clients; tool conversion/caching/filtering (`packages/agents-core/src/mcp.ts:51-70`, `:334-520`, `:698-744`, `:779-847`).
- **Shell execution** (local or hosted container envs with skill references/network policies): shell tool definition and validation (`packages/agents-core/src/tool.ts:614-826`).
- **Computer use tool** (UI/computer actions + safety checks): `computerTool` and lifecycle management (`packages/agents-core/src/tool.ts:381-455`, `:513-612`).
- **Apply-patch editing tool**: first-class `apply_patch` tool type (`packages/agents-core/src/tool.ts:828-872`).
- **Human-in-the-loop approvals/interruptions**: approval item types and resume logic in turn resolution/run loop (`packages/agents-core/src/runner/turnResolution.ts:311-624`, `packages/agents-core/src/runner/runLoop.ts:59-129`).
- **Tracing/observability**: traces/spans integrated in run flow and shown in examples (`packages/agents-core/src/run.ts:526-580`, `examples/research-bot/manager.ts:21-24`).

## 5. Notable Code Walkthrough

- `packages/agents-core/src/agent.ts:267-391,446-1038`  
  Defines `Agent` configuration surface (instructions, tools, handoffs, guardrails, model settings), plus `asTool()` for nested agent invocation and `getEnabledHandoffs()`/`getAllTools()` for runtime capability exposure.

- `packages/agents-core/src/run.ts:342-580,622-1601`  
  Core runner orchestration loop: state/session prep, model call preparation, non-stream and stream loops, guardrails, turn processing, tracing, and error handling.

- `packages/agents-core/src/runner/modelOutputs.ts:628-898,900-1198`  
  Converts raw model outputs into structured run actions (message/tool/handoff/approval/search), including deferred tool loading and client `tool_search` execution paths.

- `packages/agents-core/src/runner/turnResolution.ts:631-855`  
  Decides what happens after each model response: execute tools in parallel, process handoffs, emit interruptions, validate structured output, or continue loop.

- `examples/financial-research-agent/manager.ts:76-99`  
  Representative real workflow: manager exposes specialist agents as tools (`financialsAgent.asTool`, `riskAgent.asTool`) to writer agent, then runs report generation + verification pipeline.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. The repo operationalizes workflow automation by letting developers encode multi-step business/research processes as agent pipelines: planning, parallel retrieval, specialist analysis, synthesis, and optional verification (`examples/research-bot/*`, `examples/financial-research-agent/*`). At framework level, automated orchestration is explicit in the run loop and turn-resolution engine, which repeatedly routes between tool execution, delegation, approval checkpoints, and finalization (`packages/agents-core/src/run.ts`, `packages/agents-core/src/runner/turnResolution.ts`). It also supports durable sessions and resumable interruptions, which are core workflow-automation concerns rather than one-shot chat UX.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Native multi-agent primitives (`handoff`, `asTool`) with concrete runtime semantics, not just prompt conventions.
  - Strong orchestration core with explicit next-step states (`run_again`, `handoff`, `interruption`, `final_output`).
  - Broad tool surface (function + MCP + hosted tools + shell/computer/apply_patch) under one abstraction.
  - Built-in HITL approval/resume mechanics suitable for controlled automation.
  - Streaming and non-streaming paths are both first-class and mostly behaviorally aligned.

- **Limitations:**
  - Coordination policy is largely model-driven; no first-class declarative graph planner/scheduler API like explicit DAG nodes/edges.
  - Complex control logic spread across many runner modules; high implementation complexity for contributors.
  - Safety/quality depends heavily on user-provided prompts/guardrails/tool policies; defaults cannot guarantee domain correctness.
  - Hosted tool behavior is provider-dependent; portability beyond OpenAI-hosted tool semantics is limited.
  - Example workflows are illustrative but relatively narrow compared to production-scale long-horizon orchestration.

- **Research relevance:**
  - Evidence of practical **LLM-centric manager-worker orchestration** with mixed delegation modes (handoff vs nested tool agent).
  - Useful case study for **HITL interruption and approval protocols** in autonomous workflows.
  - Demonstrates **tool-augmented agent runtime design** integrating MCP and environment-interaction tools.
  - Shows engineering patterns for **stateful, resumable, streaming multi-agent execution** in production SDKs.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
