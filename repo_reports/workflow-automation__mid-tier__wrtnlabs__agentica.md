---
repo_name: wrtnlabs/agentica
url: "https://github.com/wrtnlabs/agentica"
stars: 1021
forks: 62
contributors_count: 14
last_commit_date: "2026-04-14T06:20:15+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T16:03:50.729679+00:00"
model: auto
duration_s: 100.4
clone_size_kb: 20910
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`agentica` is a TypeScript framework for building LLM-driven function-calling agents that automate real-world tasks by orchestrating API calls, class methods, and MCP tools. A user typically instantiates `Agentica` (or `MicroAgentica`) with a model vendor (OpenAI-compatible client) plus one or more controllers, then calls `conversate()` with natural language input (`packages/core/src/Agentica.ts:138-189`). The runtime decides which tools/functions are relevant, executes them with validated arguments, and optionally generates a natural-language explanation of results (`packages/core/src/orchestrate/execute.ts:41-59`, `packages/core/src/orchestrate/describe.ts:15-62`). In practice, this yields a workflow-style assistant that can translate user intent into multi-step tool execution, not just plain chat (`test/src/cli/index.ts:73-166`).

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework** (not LangGraph/LangChain/CrewAI/AutoGen). The orchestration logic is implemented directly in `@agentica/core` with its own executor interfaces and orchestration modules (`packages/core/src/structures/IAgenticaExecutor.ts:28-167`, `packages/core/src/orchestrate/*.ts`). LLM calls are made through the OpenAI SDK abstraction in `getChatCompletionFunction()` (`packages/core/src/utils/request.ts:16-139`), and schemas/tools are generated via `typia`/`@typia/utils`.

Architecture-wise, `Agentica` composes operations from controllers (class/http/mcp) into a unified operation collection (`packages/core/src/context/internal/AgenticaOperationComposer.ts:17-57`). Its runtime then coordinates internal role-specialized “agents”: initializer, selector, caller/executor, describer, and canceler (`packages/core/src/structures/IAgenticaExecutor.ts:30-167`). `MicroAgentica` is a lighter variant that skips the selection filter and directly exposes all functions to the caller/describer path (`packages/core/src/MicroAgentica.ts:33-41`, `:166-177`).

The “intelligence” primarily lives in role-specific prompts + tool-call schemas + retry/correction loops: selection and cancellation use dedicated tool schemas (`selectFunctions`/`cancelFunctions`) with validation feedback (`packages/core/src/orchestrate/select.ts:176-193`, `:237-258`; `packages/core/src/orchestrate/cancel.ts:152-168`, `:180-203`), while call execution includes JSON parse/type correction loops before invoking tools (`packages/core/src/orchestrate/call.ts:172-214`, `:355-468`).

## 3. Orchestration Pattern

Closest match: **hierarchical/sequential manager-worker pipeline** (custom), with optional parallel partitioning for large toolsets.

Control flow is explicitly staged in `execute()`:

```43:59:packages/core/src/orchestrate/execute.ts
const executes: AgenticaExecuteEvent[] = await (
  executor?.call ?? call
)(ctx, ctx.stack.map(s => s.operation));

// EXPLAIN RETURN VALUES
if (executor?.describe !== null && executor?.describe !== false) {
  await (
    typeof executor?.describe === "function"
      ? executor.describe
      : describe
  )(ctx, executes);
}
```

Selection writes candidate operations into a shared stack that downstream call/describer consume:

```25:37:packages/core/src/orchestrate/internal/selectFunctionFromContext.ts
const selection: AgenticaOperationSelection
  = createOperationSelection({
    operation,
    reason: reference.reason,
  });
ctx.stack.push(selection);

const event: AgenticaSelectEvent = createSelectEvent({
  selection,
  assistant: reasoning?.assistant,
});
```

This is not a graph/state-machine library; it is a deterministic staged loop (`initialize -> cancel -> select -> call -> describe`, then repeat while stack has work) (`packages/core/src/orchestrate/execute.ts:13-59`).

## 4. Tools & External Integrations

- **LLM provider (OpenAI-compatible API):** unified request/streaming/backoff/token accounting in `packages/core/src/utils/request.ts:16-139`; used by all internal agents.
- **MCP tools (Model Context Protocol):** MCP client tools are discovered (`tools/list`) and converted into callable LLM functions via `assertMcpController()` + `createMcpLlmApplication()` (`packages/core/src/functional/assertMcpController.ts:25-47`, `packages/core/src/functional/createMcpLlmApplication.ts:8-72`).
- **HTTP API integration (OpenAPI/Swagger -> functions):** `assertHttpController()` converts API specs to LLM-callable functions and executes via `HttpLlm.propagate` (`packages/core/src/functional/assertHttpController.ts:25-106`, `packages/core/src/orchestrate/call.ts:537-556`).
- **Local/class method tools:** class controllers execute in-process methods (`packages/core/src/orchestrate/call.ts:520-535`), used in tests with `BbsArticleService` (`test/src/features/test_micro_agentica.ts:23-31`).
- **Vector-based tool preselection (optional package):**
  - SQLite + `sqlite-vec` + Cohere embeddings (`packages/vector-selector/src/strategy/sqlite.strategy.ts:19-123`)
  - Postgres/connector-hive retrieval API strategy (`packages/vector-selector/src/strategy/postgres.strategy.ts:14-116`)
  - Wired as alternate selector logic via `BootAgenticaVectorSelector` (`packages/vector-selector/src/index.ts:23-56`).

## 5. Notable Code Walkthrough

- `packages/core/src/Agentica.ts:52-297` - Main runtime facade: builds operation inventory, handles conversation history/events, creates execution context, and delegates to the orchestrator.
- `packages/core/src/orchestrate/execute.ts:11-61` - Core pipeline driver implementing staged multi-agent flow (`initialize/cancel/select/call/describe`) and loop control.
- `packages/core/src/orchestrate/call.ts:37-170` and `:172-469` - Most critical runtime logic: prompts model with tool schemas, parses/validates tool calls, retries with correction prompts, then executes class/http/mcp operations.
- `packages/core/src/context/internal/AgenticaOperationComposer.ts:17-57` - Normalizes heterogeneous controllers into a single operation set, including optional capacity-based partitioning (`divided`) for scalable selection/cancellation.
- `test/src/cli/index.ts:73-166` - Practical end-to-end usage example showing an interactive workflow agent over shopping HTTP APIs with event tracing and iterative user commands.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. The project’s core behavior is: interpret user intent, select relevant operations from many possible tools, execute those operations with validated structured arguments, and narrate outcomes (`packages/core/src/orchestrate/execute.ts:35-59`, `packages/core/src/orchestrate/call.ts:193-214`). This is exactly automation of multi-step operational workflows (API invocations, business functions, MCP tools), not primarily code generation or retrieval QA. Even optional vector-selector logic is aimed at improving function/tool routing for large automation catalogs rather than document-centric RAG (`packages/vector-selector/src/index.ts:33-54`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear internal role decomposition (initialize/select/cancel/call/describe) with overridable executor hooks (`packages/core/src/structures/IAgenticaExecutor.ts:28-167`).
  - Strong robustness loop for malformed tool calls (JSON parse + schema validation + corrective reprompting) (`packages/core/src/orchestrate/call.ts:180-214`, `:355-468`).
  - Unified support for heterogeneous tool protocols (class/http/mcp) under one runtime (`packages/core/src/context/internal/AgenticaOperationComposer.ts:66-79`).
  - Streaming/event architecture with request/response tracing and token accounting (`packages/core/src/utils/request.ts:30-139`).
  - Scalable selection strategy options including vector-assisted prefiltering (`packages/vector-selector/src/index.ts:23-56`).

- **Limitations:**
  - Multi-agent is role-based within one runtime, not independent autonomous agents with explicit inter-agent memory/negotiation.
  - Control flow is largely fixed pipeline; no declarative graph/state transitions like LangGraph-style branching.
  - No built-in durable task queue/scheduler/long-running workflow engine semantics (it is per-conversation orchestration).
  - Selection/cancellation rely on LLM tool-call schemas that may still produce empty/ambiguous outputs, handled via retries but not guaranteed.
  - Optional vector selector adds external infra dependencies (Cohere, sqlite-vec, connector services) that increase deployment complexity.

- **Research relevance:**
  - Good evidence for **role-specialized internal agent orchestration** in practical function-calling systems.
  - Useful case of **LLM-in-the-loop validation repair** for structured tool invocation reliability.
  - Demonstrates **protocol-unified tool abstraction** (class/http/mcp) in one agent runtime.
  - Provides empirical basis for studying tradeoffs between full-tool exposure (`MicroAgentica`) vs. preselection (`Agentica` + vector selector).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
