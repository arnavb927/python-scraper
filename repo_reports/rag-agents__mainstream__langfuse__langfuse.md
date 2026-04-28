---
repo_name: langfuse/langfuse
url: "https://github.com/langfuse/langfuse"
stars: 25763
forks: 2609
contributors_count: 150
last_commit_date: "2026-04-22T15:49:38+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 8
architecture_labels: [LangGraph, LangChain, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T09:30:18.697325+00:00"
model: auto
duration_s: 108.9
clone_size_kb: 32718
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`langfuse/langfuse` is an LLM engineering platform, not an agent runtime: users run a web app + worker stack that ingests telemetry/events from their AI systems, stores them, and exposes observability, prompt management, evals, and analytics. In practice, teams instrument their own apps (including agent frameworks), send traces via OTEL/API, and use Langfuse to inspect traces, tool calls, costs, and behavior over time. The codebase centers on ingestion, normalization, storage, and query surfaces rather than task-solving agents. It also exposes an MCP server so external assistants can read/manage prompts inside Langfuse.

## 2. Agent Framework & Architecture

The repo does **not** implement a native multi-agent runtime (no in-process planner/worker/debate/swarm loop). Instead, it implements a **custom observability architecture** that recognizes and normalizes traces produced by external frameworks (LangGraph/LangChain, Microsoft Agent Framework, Pydantic AI, etc.). This is evident in adapter code such as `packages/shared/src/utils/chatml/adapters/langgraph.ts` and `.../microsoft-agent.ts`, where framework-specific message formats are detected and transformed.

The “intelligence” here lives in:
- adapter detection/preprocessing rules (`selectAdapter` chooses first matching adapter),
- OTEL ingestion mapping logic that extracts input/output/tools from many telemetry conventions,
- storage/query layers that reconstruct graph-like views for UI.

Example detection/dispatch path:
```269:277:packages/shared/src/utils/chatml/adapters/langgraph.ts
export const langgraphAdapter: ProviderAdapter = {
  id: "langgraph",

  detect(ctx: NormalizerContext): boolean {
    const meta = parseMetadata(ctx.metadata);

    // EXPLICIT: Framework hint
    if (ctx.framework === "langgraph") return true;
```

```23:34:packages/shared/src/utils/chatml/adapters/index.ts
function selectAdapter(ctx: NormalizerContext): ProviderAdapter {
  // Explicit override
  if (ctx.framework) {
    const adapter = adapters.find((a) => a.id === ctx.framework);
    if (adapter) return adapter;
  }

  // First adapter that matches wins
  for (const adapter of adapters) {
```

## 3. Orchestration Pattern

Closest match: **event-driven data pipeline** (not multi-agent orchestration).

Control flow is telemetry/event ingestion -> normalization/extraction -> event creation/storage -> query/visualization. The worker processes OTEL spans and emits Langfuse ingestion events; UI/API then queries these events and can render “agent graphs” from observed traces.

```521:530:packages/shared/src/server/otel/OtelIngestionProcessor.ts
async processToIngestionEvents(
  resourceSpans: ResourceSpan[],
): Promise<IngestionEventType[]> {
  return await instrumentAsync(
    { name: "otel-ingestion-processor" },
    async (span) => {
      span.setAttribute("project_id", this.projectId);
```

```255:263:web/src/features/events/server/eventsRouter.ts
getAgentGraphData: protectedProjectProcedure
  .input(
    zodSchema.object({
      projectId: zodSchema.string(),
      traceId: zodSchema.string(),
      minStartTime: zodSchema.string(),
      maxStartTime: zodSchema.string(),
```

## 4. Tools & External Integrations

- **OpenTelemetry ingestion**: core OTEL span processing and semantic mapping in `packages/shared/src/server/otel/OtelIngestionProcessor.ts`.
- **Framework trace adapters** (LangGraph/LangChain, Microsoft Agent, AI SDK, Gemini, Semantic Kernel, Pydantic AI): `packages/shared/src/utils/chatml/adapters/*.ts`, wired via `.../adapters/index.ts`.
- **Tool-call extraction pipeline** for observed LLM/tool interactions: `packages/shared/src/server/ingestion/extractToolsBackend.ts`.
- **Queue + blob storage pipeline** (async ingestion): S3 upload + queue job enqueue in `OtelIngestionProcessor.publishToOtelIngestionQueue` (`.../otel/OtelIngestionProcessor.ts`).
- **MCP server integration** (for external assistants to operate on prompts): endpoint `web/src/pages/api/public/mcp/index.ts`, server wiring in `web/src/features/mcp/server/mcpServer.ts`, tool registry in `.../server/registry.ts`, prompt tools in `.../features/prompts/...`.
- **Datastores**: Postgres (Prisma usage in API routes), ClickHouse-backed events querying (e.g., `eventsRouter` calling shared server query utilities), Redis for dedupe/rate-limit/session-like infra.

No evidence that Langfuse agents directly call browser automation, shell, or web-search tools as part of an internal autonomous agent loop.

## 5. Notable Code Walkthrough

- `packages/shared/src/server/otel/OtelIngestionProcessor.ts:142-3070`  
  Central ingestion engine: converts OTEL resource spans into Langfuse trace/observation events, extracts model/tool metadata across many ecosystems, deduplicates shallow traces, and emits typed ingestion events.

- `packages/shared/src/utils/chatml/adapters/index.ts:11-38`  
  Adapter router selecting framework-specific normalizers in priority order; this is where heterogeneous agent-framework payloads become normalized ChatML-like structures.

- `packages/shared/src/utils/chatml/adapters/langgraph.ts:269-386`  
  LangGraph/LangChain detector + preprocessor; handles role/type normalization, tool-call flattening, and metadata-based framework fingerprinting.

- `packages/shared/src/server/ingestion/extractToolsBackend.ts:306-387`  
  Extracts tool definitions and tool invocations from raw input/output payloads (OpenAI-style, Anthropic tool_use, LangChain kwargs, etc.) and converts them into ClickHouse-friendly structures.

- `web/src/pages/api/public/mcp/index.ts:65-168`  
  Public MCP endpoint implementing auth, rate limiting, context binding, and request dispatch to MCP tool handlers; enables external agent clients (Cursor/Claude Desktop) to access Langfuse prompt operations.

## 6. Use-Case Mapping

The assigned label **RAG + Agents** is only partially accurate. This repo does not itself run a coordinated agent team; instead, it provides infrastructure to **observe, manage, and analyze** applications that may include RAG and/or agents. Evidence: framework-specific ingestion/normalization is extensive, but there is no runtime planner-worker/supervisor execution loop in core services.

Better fit from your taxonomy: **Workflow Automation** (platform workflow around telemetry ingestion, normalization, prompt ops, eval/analytics, and MCP-based prompt tooling). So this repository is better viewed as agent-adjacent infrastructure than an agentic runtime.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad cross-framework compatibility via explicit adapters and metadata heuristics (`chatml/adapters/*`).
  - Strong event-driven ingestion architecture with dedupe, fallback parsing, and resilient error handling (`OtelIngestionProcessor`).
  - Rich tool-call extraction across provider formats, enabling downstream analysis (`extractToolsBackend.ts`).
  - Practical interoperability surface through MCP server + tool registry abstraction (`web/src/features/mcp/server/*`).

- **Limitations:**
  - No native multi-agent execution semantics (no planner/worker runtime), so MAS behavior must come from external apps.
  - Framework detection is heuristic-heavy and may require ongoing maintenance as telemetry schemas evolve.
  - “Agent graph” in UI is reconstructed from traces, not authoritative runtime control logic (`buildStepData.ts` is post-hoc layout logic).
  - MCP feature set appears prompt-centric currently (bootstrap registers prompts only), not a full agent-tool ecosystem.

- **Research relevance:**
  - Useful as evidence of how production platforms normalize heterogeneous agent-framework traces into common schemas.
  - Useful for studying observability-driven analysis of tool-calling and agent workflows rather than agent policy itself.
  - Useful for examining interoperability patterns (OTEL + MCP) in LLM system infrastructure.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
