---
repo_name: antvis/mcp-server-chart
url: "https://github.com/antvis/mcp-server-chart"
stars: 4002
forks: 370
contributors_count: 21
last_commit_date: "2026-02-25T14:04:06+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 4
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T14:48:16.976993+00:00"
model: auto
duration_s: 60.9
clone_size_kb: 333
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`antvis/mcp-server-chart` is a TypeScript Model Context Protocol (MCP) server that exposes chart-generation tools (25+ chart/map/table variants) to an external AI client. A user runs the server via CLI (`stdio`, `sse`, or `streamable` transport), connects it from an MCP-capable app (Cursor/Claude/etc.), and then invokes tools like `generate_line_chart` or `generate_map` through that client. The server validates tool inputs with Zod, forwards requests to a chart-rendering HTTP backend, and returns chart image URLs plus metadata/spec. In practice, this repo is a tool-provider backend for LLM workflows rather than an autonomous agent system itself.

## 2. Agent Framework & Architecture

Framework evidence in code indicates **MCP SDK** (`@modelcontextprotocol/sdk`) plus **Express/Axios/Zod**, and **no LangGraph/LangChain/AutoGen/CrewAI/LlamaIndex runtime**. Core imports are from MCP server transports and request schemas (e.g., `src/server.ts`, `src/services/*.ts`, `package.json`).

Architecture is a single MCP server process with:
- a server constructor (`createServer`) that registers `ListTools` and `CallTool` handlers (`src/server.ts:19-83`);
- chart tool descriptors exported from `src/charts/*` and aggregated in `src/charts/index.ts`;
- a dispatcher (`callTool`) mapping tool names to chart types and validation schemas (`src/utils/callTool.ts:8-122`);
- an HTTP generation client (`generateChartUrl`/`generateMap`) that calls external rendering services (`src/utils/generate.ts:26-80`).

The “intelligence” in this repo is mostly **schema-driven tool contracts** and chart-specific descriptions/constraints (e.g., `src/charts/line.ts`, `src/charts/base.ts`), not multi-agent planning/routing. Any LLM reasoning happens in the external MCP client that chooses when/how to call these tools.

## 3. Orchestration Pattern

Closest match: **Other (request-driven tool-dispatch server)**, not a multi-agent orchestration pattern. Control flow is MCP request handling -> tool-name dispatch -> HTTP rendering call.

```70:81:src/server.ts
function setupToolHandlers(server: Server): void {
  logger.info("setting up tool handlers...");
  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: getEnabledTools().map((chart) => chart.tool),
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request: any) => {
    logger.info("calling tool", request.params.name, request.params.arguments);
    return await callTool(request.params.name, request.params.arguments);
  });
}
```

```55:94:src/utils/callTool.ts
export async function callTool(tool: string, args: object = {}) {
  logger.info(`Calling tool: ${tool}`);
  const chartType = CHART_TYPE_MAP[tool as keyof typeof CHART_TYPE_MAP];

  if (!chartType) throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${tool}.`);
  // ...schema validation...
  const isMapChartTool = ["generate_district_map", "generate_path_map", "generate_pin_map"].includes(tool);
  if (isMapChartTool) return (await generateMap(tool, args));
  const url = await generateChartUrl(chartType, args);
  // ...return MCP content + _meta...
}
```

## 4. Tools & External Integrations

- **MCP protocol server transports** (`stdio`, `SSE`, streamable HTTP) via `@modelcontextprotocol/sdk`; wired in `src/index.ts`, `src/server.ts`, `src/services/stdio.ts`, `src/services/sse.ts`, `src/services/streamable.ts`.
- **External chart-rendering HTTP API** (default `https://antv-studio.alipay.com/api/gpt-vis` or custom `VIS_REQUEST_SERVER`); called with Axios in `src/utils/generate.ts` and configured in `src/utils/env.ts`.
- **Map generation backend mode** with optional `SERVICE_ID`; wired in `src/utils/generate.ts` + `src/utils/env.ts`.
- **Runtime tool filtering** using env var `DISABLED_TOOLS`; wired in `src/server.ts:53-64` and `src/utils/env.ts:23-29`.
- **No built-in web search/browser automation/vector DB/RAG store/shell-agent subsystem** in repository runtime code.

## 5. Notable Code Walkthrough

- `src/server.ts:19-113` - Creates the MCP server, registers list/call tool handlers, and starts transport-specific server paths; this is the central orchestration point.
- `src/utils/callTool.ts:8-122` - Implements canonical tool-name -> chart-type routing, Zod validation cache, map-vs-chart branching, and MCP-compliant result/error shaping.
- `src/utils/generate.ts:26-80` - Encapsulates outbound HTTP calls for rendering; all generation ultimately depends on this integration layer.
- `src/charts/line.ts:24-69` - Representative chart module showing input schema + tool metadata that external LLM clients use to decide invocation.
- `src/services/streamable.ts:17-54` - Shows stateless per-request transport/session behavior for streamable MCP over HTTP.

## 6. Use-Case Mapping

This repo fits **Workflow Automation** as an MCP automation component: it standardizes chart-generation tasks as callable tools that AI assistants can invoke inside larger workflows (analysis -> choose chart tool -> render -> return URL/spec). It automates repeated visualization operations through typed tool contracts and transport adapters, enabling plug-and-play use in multiple AI clients.  

However, it does **not** implement multi-agent coordination internally; it is better characterized as **single MCP tool server infrastructure** consumed by external agents.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear MCP integration across `stdio`/`SSE`/streamable transports for broad client compatibility.
  - Strong schema-first tool interfaces (Zod + JSON schema) for robust parameter validation.
  - Clean separation between protocol handling, dispatch logic, and rendering API calls.
  - Practical operational controls (`VIS_REQUEST_SERVER`, `DISABLED_TOOLS`, `SERVICE_ID`) for deployment flexibility.

- **Limitations:**
  - No in-repo LLM orchestration/planning/memory; “agentic” behavior is delegated to external clients.
  - Single external rendering endpoint is a runtime dependency/SPOF (`generate.ts`).
  - Minimal retry/backoff/circuit-breaker logic around outbound HTTP calls.
  - Map support appears geographically constrained by upstream service assumptions (China-focused POI/map flow).

- **Research relevance:**
  - Useful evidence for **MCP tool-server design patterns** in LLM ecosystems.
  - Good case for **schema-constrained tool invocation** as reliability mechanism.
  - Not strong evidence for multi-agent coordination algorithms or emergent MAS behaviors.
  - Relevant to studies of **agent-tool boundary architecture** (agent outside, tools inside MCP server).

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
