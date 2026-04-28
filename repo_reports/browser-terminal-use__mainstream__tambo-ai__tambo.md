---
repo_name: tambo-ai/tambo
url: "https://github.com/tambo-ai/tambo"
stars: 11126
forks: 560
contributors_count: 58
last_commit_date: "2026-04-14T15:46:03+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 9
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T09:16:59.831825+00:00"
model: auto
duration_s: 80.6
clone_size_kb: 130843
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`tambo-ai/tambo` is a monorepo for a generative UI platform: developers provide UI components and tools, and Tambo runs an LLM loop that decides what to say, which tool to call, and which component to render next. In practice, users run the cloud API/web apps (or SDK) and send chat-style messages; the system streams AG-UI events plus persisted thread/run state. The backend repeatedly executes tool-calling turns (including MCP-backed tools), stores message history, and can auto-continue after tool responses. The result is an app-integrated assistant that performs workflow actions and drives UI state, not a standalone browser/terminal automation agent.

## 2. Agent Framework & Architecture

This repo does **not** implement LangGraph/LangChain/CrewAI orchestration internally. The core runtime is custom, built around:
- Vercel AI SDK (`ai`, `@ai-sdk/openai`, `@ai-sdk/anthropic`, etc.) in `packages/backend/src/services/llm/ai-sdk-client.ts`.
- AG-UI event model (`@ag-ui/core`, `@ag-ui/client`) for streaming/tool event semantics.
- MCP integration through `@modelcontextprotocol/sdk` in `packages/core/src/mcp-client.ts`.

Architecture-wise, the main “intelligence” sits in a **single decision loop** prompt + tool schema setup, then iterative tool execution. `runDecisionLoop` builds system prompt + messages + strict tool schemas and streams model deltas (`packages/backend/src/services/decision-loop/decision-loop-service.ts:115-310`). `ThreadsService` coordinates recursion when a server-side tool call appears, and continues until no further internal tool call remains (`apps/api/src/threads/threads.service.ts:1687-2233`).

There is an optional “agent provider” mode that wraps external agents (Mastra, CrewAI, LlamaIndex, PydanticAI HTTP agent) via AG-UI adapters (`packages/backend/src/services/llm/agent-client.ts:65-124`). That is an integration point, not native multi-agent orchestration implemented in this repo.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker loop** (single manager loop + tool workers), with recursive turns.  
- Manager: decision loop chooses next action/tool.  
- Workers: MCP tools, memory tools, or UI tool rendering responses.  
- Control returns to manager until completion.

Control-flow evidence:

```1687:1710:apps/api/src/threads/threads.service.ts
private async handleAdvanceThreadStream(
  contextInfo: ContextInfo,
  threadId: string,
  stream: AsyncIterableIterator<DecisionStreamItem>,
  ...
) {
  ...
  for await (const streamItem of fixStreamedToolCalls(stream)) {
```

```1328:1336:apps/api/src/threads/threads.service.ts
// This effectively recurses back into the decision loop with the tool response
await this.advanceThread(
  contextInfo,
  messageWithToolResponse,
  threadId,
  updatedToolCallCounts,
  allTools,
  queue,
);
```

The prompt explicitly enforces sequential tool use:

```17:19:packages/backend/src/prompt/decision-loop-prompts.ts
You may call any number of informational tools in sequence ...
However, you should not attempt to call tools in parallel.
```

## 4. Tools & External Integrations

- **LLM providers (OpenAI/Anthropic/Gemini/Groq/Mistral/OpenAI-compatible/Cerebras)** wired in `packages/backend/src/services/llm/ai-sdk-client.ts:14-20, 413-446`.
- **Provider “skills” container execution** (OpenAI shell tool / Anthropic code_execution tool) wired in `packages/backend/src/services/llm/ai-sdk-client.ts:336-411`.
- **MCP servers (tool listing, calling, resource read, OAuth/session)** via `packages/core/src/mcp-client.ts:53-247` and `apps/api/src/common/systemTools.ts:42-282`.
- **Server-side MCP tool execution + result conversion (text/image/audio/resource)** in `apps/api/src/threads/util/tool.ts:200-262`.
- **Resource prefetch/cache from MCP URIs before model call** in decision/agent loops (`packages/backend/src/services/decision-loop/decision-loop-service.ts:159-163`, `packages/backend/src/services/decision-loop/agent-loop.ts:44-48`).
- **Database-backed thread/run/tool-call state** through Drizzle operations in `apps/api/src/v1/v1.service.ts` and `apps/api/src/threads/threads.service.ts`.
- **Object storage attachment fetcher** added as a resource fetcher in `apps/api/src/threads/threads.service.ts:1519-1527, 1610-1617`.
- **External agent framework adapters** (Mastra/CrewAI/LlamaIndex/PydanticAI) in `packages/backend/src/services/llm/agent-client.ts:78-117`.

No direct Playwright/browser-driving or shell-command execution loop is implemented as first-class internal tools here.

## 5. Notable Code Walkthrough

- `apps/api/src/threads/threads.service.ts:939-2233`  
  Core orchestration engine: loads tools (MCP + client + UI), runs decision loop, streams events, handles cancellation/limits, and recursively continues after server-side tool/UI/memory tool calls.

- `packages/backend/src/services/decision-loop/decision-loop-service.ts:115-310`  
  Main single-agent loop implementation: prompt construction, strict tool handling, streamed parse of tool calls, and conversion into `LegacyComponentDecision` + AG-UI events.

- `packages/backend/src/services/llm/ai-sdk-client.ts:144-329`  
  Provider-agnostic model execution wrapper around AI SDK (`streamText`/`generateText`) with model/provider options, tool conversion, telemetry, and optional provider-skills injection.

- `apps/api/src/common/systemTools.ts:42-282`  
  MCP discovery and schema wiring: fetches enabled MCP servers, lists their tools, prefixes tool names by server key, and exposes tool-source mapping for execution.

- `packages/backend/src/services/llm/agent-client.ts:65-124`  
  Adapter layer that can route to external AG-UI-compatible agent providers (Mastra/CrewAI/LlamaIndex/PydanticAI) when project config selects `AiProviderType.AGENT`.

## 6. Use-Case Mapping

The assigned `Browser / Terminal Use` label appears **incorrect** for this codebase. The repository primarily implements **workflow automation inside app UIs**: an LLM selects actions/tools/components, calls MCP or app tools, and iteratively advances thread state. There is no native browser automation stack (e.g., Playwright/Browserbase control loop) and no built-in terminal command agent.

Better category: **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong production-grade run/thread state machine with cancellation, locking, and replay-safe tool-result handling (`apps/api/src/v1/v1.service.ts`).
  - Clean MCP integration with per-server tool namespacing and resource fetching (`apps/api/src/common/systemTools.ts`, `apps/api/src/threads/util/tool.ts`).
  - Unified streaming abstraction that emits both model deltas and AG-UI events (`decision-loop-service`, `ai-sdk-client`, `threads.service`).
  - Supports both direct LLM mode and external agent-provider mode without changing API surface (`tambo-backend.ts`).
  - Practical safeguards (tool-call limits, strict schemas, argument filtering) reduce runaway loops and malformed tool calls.

- **Limitations:**
  - Not a native multi-agent runtime; mostly single-loop orchestration plus external-agent adapters.
  - Heavy recursion/complexity in `ThreadsService` may be hard to reason about formally or verify end-to-end.
  - Prompt-instruction routing remains largely text-driven; no explicit graph planner/state machine formalism.
  - Limited explicit parallel tool orchestration (prompt even discourages parallel calls).
  - Provider-specific behavior (skills tool names, metadata quirks) adds portability complexity.

- **Research relevance:**
  - Good evidence of **single-agent tool-augmented orchestration** in production SaaS settings.
  - Useful case study for **MCP-based tool ecosystems** and namespaced tool routing.
  - Demonstrates hybrid streaming architecture bridging LLM deltas, UI events, and DB-backed run state.
  - Illustrates practical governance mechanisms for iterative tool loops (limits, lock control, cancellation).

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
