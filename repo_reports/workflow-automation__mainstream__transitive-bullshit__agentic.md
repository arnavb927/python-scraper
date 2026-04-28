---
repo_name: transitive-bullshit/agentic
url: "https://github.com/transitive-bullshit/agentic"
stars: 18128
forks: 2236
contributors_count: 142
last_commit_date: "2026-02-11T04:50:00+00:00"
primary_use_case: Workflow Automation
user_tier: Mainstream
total_score: 7
architecture_labels: [LangChain]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T10:52:12.799479+00:00"
model: auto
duration_s: 83.8
clone_size_kb: 38298
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`agentic` is a TypeScript monorepo for publishing, hosting, and monetizing MCP/OpenAPI tools behind a managed gateway, rather than a runtime multi-agent system itself. A developer typically deploys an MCP server or OpenAPI backend, then consumers call tools through URLs like `/{deployment}/{tool}` or `/{deployment}/mcp` and get normalized tool responses with auth, rate limits, caching, and usage tracking (`apps/gateway/src/app.ts:55-140`). The repo also ships SDK adapters that convert hosted tools into formats expected by AI frameworks (LangChain, LlamaIndex, Mastra, Vercel AI SDK), so users can plug these tools into their own agents (`stdlib/*/src/*.ts`). In practice, users run CLI deploy/publish workflows and gateway services, and receive “paid MCP/API products” consumable by LLM apps.

## 2. Agent Framework & Architecture

The core platform does **not** implement an internal agent framework (no runtime LangGraph/CrewAI/AutoGen-style multi-agent orchestration in gateway/api paths). Instead, it provides interoperability layers for external agent frameworks: e.g., `@langchain/core/tools` in `stdlib/langchain/src/langchain.ts:11-34`, `llamaindex` in `stdlib/llamaindex/src/llamaindex.ts:10-31`, and Mastra tools in `stdlib/mastra/src/mastra.ts:11-44`.

Architecture is a gateway-centric tool serving pipeline. `AgenticToolClient` discovers deployment metadata and exposes each tool as an executable AI function that issues HTTP POST calls to the gateway (`packages/tool-client/src/agentic-tool-client.ts:90-111`). The gateway resolves request mode (HTTP vs MCP), authenticates consumer/pricing context, validates schema, calls origin (OpenAPI or MCP), then applies cache/rate-limit/usage bookkeeping (`apps/gateway/src/lib/resolve-edge-request.ts:17-40`, `resolve-http-edge-request.ts:17-82`, `resolve-origin-tool-call.ts:33-361`).

“Intelligence” (prompting/planning/tool selection) is intentionally left to external LLM runtimes; this repo mainly standardizes tool contracts and transport. Even where LangGraph appears, it is in generated code snippets for docs/UI (`apps/web/src/lib/developer-config.ts:571-593`), not platform orchestration logic.

## 3. Orchestration Pattern

Closest match: **event-driven request pipeline** (not multi-agent coordination).

Control flow is request-driven through deterministic stages:

```55:83:apps/gateway/src/app.ts
app.all(async (ctx) => {
  const resolvedEdgeRequest = await resolveEdgeRequest(ctx)
  if (resolvedEdgeRequest.edgeRequestMode === 'MCP') {
    const mcpInfo = await resolveMcpEdgeRequest(ctx, resolvedEdgeRequest)
    return DurableMcpServer.serve('/*', { binding: 'DO_MCP_SERVER' }).fetch(...)
  }
  // HTTP path continues...
})
```

```17:40:apps/gateway/src/lib/resolve-edge-request.ts
const parsedToolIdentifier = parseToolIdentifier(requestedToolIdentifier)
const deployment = await getAdminDeployment(ctx, parsedToolIdentifier.deploymentIdentifier)
const edgeRequestMode = parsedToolIdentifier.toolName === 'mcp' ? 'MCP' : 'HTTP'
```

This is orchestration of network/tool execution stages, not planner-worker agent roles. Example agent executors exist only as integration examples (`examples/ts-sdks/langchain/bin/weather.ts:13-32`) and instantiate a single framework agent.

## 4. Tools & External Integrations

- **MCP servers (upstream tools):** resolved and called via MCP client/transport (`packages/platform/src/origin-adapters/mcp.ts:29-57`, `apps/gateway/src/lib/resolve-origin-tool-call.ts:249-353`).
- **OpenAPI backends:** OpenAPI spec validated and converted to tool operations, then invoked as HTTP requests (`packages/platform/src/origin-adapters/openapi.ts:37-72`, `apps/gateway/src/lib/create-http-request-for-openapi-operation.ts` and `resolve-origin-tool-call.ts:198-248`).
- **Agentic Gateway HTTP API:** `AgenticToolClient` executes tool calls against hosted endpoints (`packages/tool-client/src/agentic-tool-client.ts:100-108`).
- **LLM framework adapters:** LangChain (`stdlib/langchain/src/langchain.ts`), LlamaIndex (`stdlib/llamaindex/src/llamaindex.ts`), Mastra (`stdlib/mastra/src/mastra.ts`), AI SDK (`stdlib/ai-sdk/src/ai-sdk.ts`), Genkit.
- **MCP protocol SDK:** `@modelcontextprotocol/sdk` clients/transports used both in stdlib and platform (`stdlib/mcp/src/mcp-tools.ts:1-193`).
- **Billing/rate limiting/caching infra:** Stripe references and usage/rate-limit enforcement in gateway (`apps/gateway/src/lib/external/stripe.ts`, `resolve-origin-tool-call.ts:167-181`, `fetch-cache.ts`).
- **CLI deployment automation:** deploy/publish/list/get flows for project deployments (`packages/cli/src/commands/*.ts`).

No embedded browser automation, terminal agents, vector store RAG, or autonomous task-planning subsystem was found in the main runtime paths.

## 5. Notable Code Walkthrough

- `apps/gateway/src/app.ts:55-140` - Main edge entrypoint; routes each incoming request into MCP or HTTP handling, wraps with error handling, response normalization, and async usage recording.
- `apps/gateway/src/lib/resolve-origin-tool-call.ts:33-361` - Core execution engine for a tool invocation: schema validation, pricing-plan overrides, rate limiting, cache behavior, and branching to OpenAPI vs MCP origin calls.
- `packages/tool-client/src/agentic-tool-client.ts:58-196` - Consumer-facing abstraction that turns deployment tool metadata into executable AI functions and resolves project/deployment identifiers from Agentic API.
- `packages/platform/src/origin-adapters/openapi.ts:37-72` - Converts OpenAPI specs into normalized tool definitions and operation maps that the gateway can invoke.
- `stdlib/langchain/src/langchain.ts:17-61` - Representative adapter: wraps Agentic functions as `DynamicStructuredTool` for LangChain; demonstrates integration boundary where external agents consume Agentic tools.

## 6. Use-Case Mapping

The assigned use case **Workflow Automation** is appropriate. The platform automates the end-to-end workflow of exposing external capabilities (MCP/OpenAPI) as LLM-ready tools with standardized schemas, auth, metering, and gateway mediation (`packages/platform/src/resolve-origin-adapter.ts:15-60`, `apps/gateway/src/lib/resolve-http-edge-request.ts:17-82`). What gets automated is not “agent collaboration,” but operational workflows around tool publishing/consumption and reliable tool execution in production. So classification remains Workflow Automation, while `USES_MAS` should be `no` because runtime multi-agent coordination is not implemented here.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Clean separation between tool discovery/normalization and runtime invocation (`packages/platform` vs `apps/gateway`).
- Broad interoperability with major LLM SDKs through thin adapters (`stdlib/*`), minimizing lock-in.
- Strong production concerns (rate limits, caching, auth, usage accounting) built directly into tool gateway path.
- MCP-first support with both MCP-origin and MCP-client consumption modes.
- Good developer ergonomics via identifier-based client bootstrap (`fromIdentifier`) and CLI deployment flows.

- **Limitations:**
- No native multi-agent runtime (no planner/worker graphs, role specialization, or inter-agent messaging).
- “Agent intelligence” is externalized; behavior quality depends on third-party frameworks and user prompts.
- Some TODOs indicate incomplete areas (raw origin adapter unimplemented, several validation/feature TODOs in gateway).
- Limited evidence of advanced memory/RAG state management in core runtime.
- Archived status (Feb 2026) suggests reduced evolution/maintenance risk for future users.

- **Research relevance:**
- Useful evidence for **agent infrastructure** research (tool marketplaces, MCP/OpenAPI bridging, monetized tool serving).
- Demonstrates practical architecture for protocol translation and policy enforcement around LLM tool calls.
- Not strong evidence for emergent multi-agent coordination algorithms or cooperative agent planning.
- Suitable baseline for studies comparing “agent runtime” vs “agent tooling platform” layers.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
