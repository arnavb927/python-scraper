---
repo_name: grafana/mcp-grafana
url: "https://github.com/grafana/mcp-grafana"
stars: 2893
forks: 339
contributors_count: 73
last_commit_date: "2026-04-23T07:33:31+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T13:56:50.500698+00:00"
model: auto
duration_s: 82.0
clone_size_kb: 2812
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`grafana/mcp-grafana` is a Go-based Model Context Protocol (MCP) server that exposes Grafana operations as callable tools for MCP-compatible AI clients (Cursor, Claude Desktop, etc.). Users run the `mcp-grafana` binary (stdio/SSE/streamable HTTP), point it at a Grafana instance, and the client can then invoke tools such as dashboard search, Prometheus/Loki queries, alerting operations, and incident/on-call actions. The server handles auth/context extraction and translates MCP tool calls into Grafana/IRM API calls. In short, it is an “AI tool backend” for Grafana workflows, not an LLM runtime itself.

## 2. Agent Framework & Architecture

The actual framework in use is **MCP server infrastructure via `mark3labs/mcp-go`**, not LangGraph/LangChain/AutoGen/CrewAI/LlamaIndex. This is evident from imports and dependency wiring in `go.mod` (`github.com/mark3labs/mcp-go v0.46.0`) and runtime code (`cmd/mcp-grafana/main.go:17-23`, `tools.go:12-21`). I did not find any in-repo LLM orchestration framework or model SDK usage in core runtime paths.

Architecture is server-centric: startup builds one `MCPServer`, registers tool categories, and composes request context extractors for auth + clients (`cmd/mcp-grafana/main.go:109-236`, `mcpgrafana.go:1112-1162`). Each tool is a typed handler wrapped by `ConvertTool`, which auto-generates JSON schema and executes with OpenTelemetry tracing (`tools.go:160-379`). “Intelligence” (reasoning/planning) lives outside this repo in whatever MCP client/LLM calls these tools.

There is optional **tool federation/proxying**: the server discovers MCP-capable datasources (currently Tempo), creates downstream MCP clients, and dynamically re-exposes those remote tools with namespaced names (`proxied_tools.go:28-33`, `proxied_tools.go:246-310`, `proxied_client.go:25-79`). That is multi-server tool orchestration, but still not multi-agent LLM coordination.

## 3. Orchestration Pattern

Closest match: **event-driven tool server** (with dynamic session-scoped tool registration), not manager-worker LLM agents.

Control flow is hook-driven before tool listing/calls:

```193:202:cmd/mcp-grafana/main.go
hooks.OnBeforeCallTool = []server.OnBeforeCallToolFunc{
  func(ctx context.Context, id any, request *mcp.CallToolRequest) {
    ensureSessionRegistered(ctx)
    if stm != nil {
      if session := server.ClientSessionFromContext(ctx); session != nil {
        stm.InitializeAndRegisterProxiedTools(ctx, session)
```

And proxied tool execution forwards calls to a selected remote MCP server:

```51:58:proxied_handler.go
datasourceType, originalToolName, err := parseProxiedToolName(h.toolName)
if err != nil { ... }
// Get the proxied client for this datasource
var client *ProxiedClient
```

```85:87:proxied_handler.go
// Forward the call to the remote MCP server
return client.CallTool(ctx, originalToolName, forwardArgs)
```

## 4. Tools & External Integrations

- **MCP runtime (server-side):** Tool registration, transports, hooks via `mcp-go` (`cmd/mcp-grafana/main.go:200-225`, `tools.go:47-68`).
- **Grafana core HTTP/OpenAPI APIs:** Main Grafana operations through `grafana-openapi-client-go` and custom transport middleware (`mcpgrafana.go:821-966`, `tools/search.go:61-101`).
- **Grafana Incident API:** Incident tools via `github.com/grafana/incident-go` (`mcpgrafana.go:1016-1061`, `tools/incident.go:52-83`).
- **Grafana OnCall API:** Uses `github.com/grafana/amixr-api-go-client`, fetching OnCall URL from plugin settings first (`tools/oncall.go:18-63`, `tools/oncall.go:65-111`).
- **Grafana rendering endpoint / Image Renderer plugin:** Fetches PNG via `/render/*` and returns MCP image content (`tools/rendering.go:84-155`, `tools/rendering.go:157-218`).
- **Remote MCP servers (proxied datasources):** Discovers MCP-enabled datasources and proxies downstream MCP tools (`proxied_tools.go:42-174`, `proxied_client.go:35-66`).
- **Observability integrations:** OpenTelemetry spans/metrics around tool execution and sessions (`tools.go:196-223`, `session.go:24-46`).

No vector DB, browser automation, shell execution, or in-repo RAG pipeline is wired up.

## 5. Notable Code Walkthrough

- `cmd/mcp-grafana/main.go:109-236` — Core assembly: enables/disables tool categories, creates session/hook infrastructure, and constructs the MCP server with capability instructions.
- `tools.go:160-379` — Generic tool adapter (`ConvertTool`) that validates handler signatures, builds JSON schemas, instruments spans, marshals/unmarshals arguments, and normalizes return values.
- `mcpgrafana.go:1112-1162` — Context composition chain for stdio/SSE/HTTP: injects Grafana config, auth/header extraction, and per-request clients.
- `proxied_tools.go:312-414` — Dynamic per-session discovery/registration of proxied MCP tools, including deduplication and session-specific tool maps.
- `proxied_handler.go:27-87` — Runtime dispatcher for proxied tool calls; enforces `datasourceUid`, resolves proper proxied client, and forwards MCP calls downstream.

## 6. Use-Case Mapping

The assigned use case (**Workflow Automation**) is correct. This repo automates operational workflows by exposing Grafana actions as structured MCP tools (querying telemetry, searching dashboards, managing incidents/alerts/on-call) so external LLM assistants can execute runbook-like steps programmatically. The automation is achieved through deterministic tool APIs and transport/session orchestration rather than in-repo agent planning.  

Important nuance: this repository **enables** agentic workflows but does not itself implement multi-agent LLM behavior.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad operational surface area (dashboards, logs/metrics, incidents, alerting, on-call) under one MCP endpoint (`cmd/mcp-grafana/main.go:201-223`).
  - Strong tool contract engineering: typed handlers + generated JSON schemas + compatibility checks (`tools.go:343-379`, `tools.go:464-548`).
  - Good multi-tenant/session handling with reaper and dynamic session tools (`session.go:83-127`, `proxied_tools.go:312-414`).
  - Built-in observability for tool calls and server/session health (`tools.go:196-223`, `session.go:30-46`).
  - Extensible federation path through proxied MCP datasource tools (`proxied_client.go:25-79`, `proxied_tools.go:28-33`).

- **Limitations:**
  - No in-repo LLM planner/router/delegation layer; relies entirely on external MCP clients for reasoning.
  - Proxied datasource support is currently narrow (registry only includes Tempo by default) (`proxied_tools.go:29-32`).
  - Some integrations use reflection hacks due to client library limitations (e.g., OnCall HTTP client transport injection) (`tools/oncall.go:83-108`).
  - Error handling and retries are mostly per-tool/manual; no global policy engine for robust long workflows.
  - Workflow composition primitives (plans, memory, checkpoints) are absent because this is a tool server, not an agent runtime.

- **Research relevance:**
  - Useful evidence for **agent tooling infrastructure** and MCP-native tool engineering patterns.
  - Demonstrates session-aware dynamic tool exposure and cross-MCP tool federation in production-style code.
  - Good case study for observability and schema governance in LLM tool ecosystems.
  - Not suitable as evidence of multi-agent coordination algorithms, debate/planning, or autonomous agent swarms.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
