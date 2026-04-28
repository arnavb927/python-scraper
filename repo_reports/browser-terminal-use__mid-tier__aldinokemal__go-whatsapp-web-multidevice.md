---
repo_name: aldinokemal/go-whatsapp-web-multidevice
url: "https://github.com/aldinokemal/go-whatsapp-web-multidevice"
stars: 3806
forks: 902
contributors_count: 28
last_commit_date: "2026-04-21T11:22:13+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 5
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T13:37:56.975999+00:00"
model: auto
duration_s: 81.2
clone_size_kb: 8341
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`aldinokemal/go-whatsapp-web-multidevice` is a Go server that exposes WhatsApp Multi-Device capabilities through two runtime modes: a REST API (`go run . rest`) and an MCP server over SSE (`go run . mcp`). In practice, users run it to connect one or more WhatsApp accounts, then automate messaging, chat querying, media download, group management, and webhook forwarding. The MCP mode is designed so external AI clients can call WhatsApp actions as MCP tools, while the REST mode serves UI/API integrations and operational endpoints. It solves “WhatsApp as programmable infrastructure” rather than implementing an internal LLM chat agent itself.

## 2. Agent Framework & Architecture

The only agent-related framework actually used in code is **MCP (Model Context Protocol)** via `github.com/mark3labs/mcp-go`; there is no LangChain, LangGraph, AutoGen, CrewAI, or LlamaIndex dependency (`src/go.mod:5-27`). The server creates one MCP server instance and registers domain-specific tool handlers (`src/cmd/mcp.go:36-56`).

Architecture-wise, this is a layered automation backend: CLI/bootstrap (`cmd`), handlers (`ui/mcp` and `ui/rest`), use cases (`usecase`), and infrastructure (`infrastructure/whatsapp`, `infrastructure/chatstorage`, `infrastructure/chatwoot`). In MCP mode, each tool handler maps a tool invocation to a concrete use case method (e.g., send text, list chats, archive chat), with device context injected by helper logic (`src/ui/mcp/helpers/context.go:10-25`).  

The “intelligence” is primarily in the **external MCP client/agent** (e.g., Claude Desktop or another LLM host) deciding which tools to call and in what order. Inside this repo, behavior is deterministic request handling and event processing; there is no internal planner/router LLM or multi-agent runtime.

## 3. Orchestration Pattern

Closest match: **event-driven + tool-RPC backend (other)**, not multi-agent orchestration.

Control flow for MCP tool calls is registration-based dispatch: the server registers many tools, each mapped to a handler function.

```34:42:src/cmd/mcp.go
mcpServer := server.NewMCPServer(
    "WhatsApp Web Multidevice MCP Server",
    config.AppVersion,
    server.WithToolCapabilities(true),
    server.WithResourceCapabilities(true, true),
)
```

```45:56:src/cmd/mcp.go
sendHandler := mcp.InitMcpSend(sendUsecase)
sendHandler.AddSendTools(mcpServer)
queryHandler := mcp.InitMcpQuery(chatUsecase, userUsecase, messageUsecase)
queryHandler.AddQueryTools(mcpServer)
appHandler := mcp.InitMcpApp(appUsecase)
appHandler.AddAppTools(mcpServer)
```

Separately, WhatsApp runtime behavior is event-driven via a type switch over incoming protocol events (`src/infrastructure/whatsapp/event_handler.go:33-74`), forwarding to handlers such as `handleMessage`, `handleReceipt`, and `handleGroupInfo`.

## 4. Tools & External Integrations

- **MCP server / tool surface**: wired in `src/cmd/mcp.go:36-71`, tool definitions in `src/ui/mcp/app.go`, `src/ui/mcp/send.go`, `src/ui/mcp/query.go`, `src/ui/mcp/group.go`.
- **WhatsApp protocol integration (whatsmeow)**: core messaging/device/events in `src/infrastructure/whatsapp/*` (e.g., `event_handler.go`, `device_manager.go`), dependency in `src/go.mod:24`.
- **REST API + UI**: Fiber-based endpoints and embedded frontend in `src/cmd/rest.go:36-171`, REST handlers in `src/ui/rest/*`.
- **Webhooks (outbound)**: WhatsApp events forwarded to configured webhook URLs inside event handlers (`src/infrastructure/whatsapp/event_handler.go:101-110`, `228-238`, `280-289`).
- **Chat storage DB (SQLite/Postgres support for WA/chat persistence)**: repository initialization in `src/cmd/root.go:328-374`, implementation in `src/infrastructure/chatstorage/sqlite_repository.go`.
- **Chatwoot CRM integration**: HTTP API client and sync logic in `src/infrastructure/chatwoot/client.go` and `src/infrastructure/chatwoot/sync.go`, routes wired in `src/cmd/rest.go:92-101` and `142-147`.
- **Filesystem/media handling**: QR image file read/encoding in MCP login (`src/ui/mcp/app.go:93-101`), media send/download flows in usecases and infra.

No built-in web search, browser automation framework, vector DB, or RAG retriever pipeline is present in runtime code.

## 5. Notable Code Walkthrough

- `src/cmd/mcp.go:29-73` — Entrypoint for MCP mode; creates the MCP SSE server, registers all WhatsApp tool groups, and starts `/sse` + `/message` endpoints. This is the key bridge between AI clients and WhatsApp operations.
- `src/ui/mcp/query.go:32-129` — Defines read/query tools (`whatsapp_list_contacts`, `whatsapp_list_chats`, etc.) and converts tool args into typed domain requests. It shows the pattern used across MCP handlers.
- `src/ui/mcp/helpers/context.go:10-25` — Resolves a default device and injects it into context so MCP handlers can reuse device-scoped business logic without REST middleware.
- `src/infrastructure/whatsapp/event_handler.go:21-77` — Central event dispatcher for WhatsApp protocol events; routes each event to specialized handlers and updates device state, demonstrating event-driven orchestration.
- `src/cmd/rest.go:124-147` — Wires device-scoped REST routes and Chatwoot sync/webhook paths, showing the non-MCP integration surface used in production automation workflows.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially accurate. This repository can be used from terminal (`go run . mcp`/`rest`) and from browser/UI (embedded web routes), but the core value is automating operational workflows around WhatsApp: sending/querying messages, webhook-driven event handling, and Chatwoot synchronization.

A better primary category is **Workflow Automation**. The code is a programmable communications backend and MCP tool provider, not a browser automation agent and not a terminal-control agent.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Cleanly exposes WhatsApp operations as MCP tools with typed arguments and structured results (`src/ui/mcp/*.go`).
  - Supports multi-device lifecycle/state management via a dedicated device manager path (`src/cmd/root.go:383-397`, infra layer).
  - Combines MCP, REST, webhook forwarding, and Chatwoot sync in one deployable service.
  - Strong event-driven handling for protocol updates (message, receipt, group, logout) in centralized dispatcher.
  - Practical production concerns included: reconnection routines, health endpoint, auth middleware, persistent storage.

- **Limitations:**
  - No internal LLM reasoning, planner, or multi-agent coordination runtime; “agentic” behavior is delegated to external clients.
  - MCP device selection is default-device oriented (`ContextWithDefaultDevice`), limiting fine-grained per-tool device targeting in some flows.
  - No explicit prompt/version management because prompts are not part of this system.
  - Tool handlers often perform direct argument extraction/validation inline, which can create repetitive logic and potential inconsistency.
  - Lacks built-in evaluation/telemetry focused on AI tool-use quality (success-by-intent, planning traces, etc.).

- **Research relevance:**
  - Useful as evidence of **MCP tool-serving infrastructure** for LLM agents rather than a MAS architecture.
  - Demonstrates how event-driven messaging backends can be wrapped for AI tool use with minimal changes.
  - Good case study for operational integration of communication APIs (WhatsApp + Chatwoot + webhooks) in automation systems.
  - Not suitable as evidence of emergent multi-agent coordination or planner-worker dynamics.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
