---
repo_name: lbjlaq/Antigravity-Manager
url: "https://github.com/lbjlaq/Antigravity-Manager"
stars: 28542
forks: 3111
contributors_count: 50
last_commit_date: "2026-04-19T08:09:12+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:30:45.411105+00:00"
model: auto
duration_s: 87.1
clone_size_kb: 38428
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`Antigravity-Manager` is a Tauri desktop app (React frontend + Rust backend) that runs a local proxy/control plane for Antigravity accounts and model access. Users run the GUI (or `--headless` mode) to manage multiple account tokens, switch/route traffic, and expose unified OpenAI/Claude/Gemini-compatible endpoints on a local port (`src-tauri/src/lib.rs:109-289`, `src-tauri/src/proxy/server.rs:371-433`). In practice, it gives one local endpoint that client tools can use while the app handles account selection, retries, quota/rate-limit logic, model mapping, and protocol translation. It also syncs configurations for multiple AI CLIs (Claude/Codex/Gemini/OpenCode), so local terminal tools can transparently use the managed proxy (`src-tauri/src/proxy/cli_sync.rs:166-240`).

## 2. Agent Framework & Architecture

This repo does **not** use LangChain/LangGraph/CrewAI/AutoGen/LlamaIndex imports in the runtime code; it is a **custom Rust proxy/orchestration system**, not an LLM-agent framework in the usual sense. The backend is an Axum server with protocol handlers and mappers (`src-tauri/src/proxy/server.rs:364-452`, `src-tauri/src/proxy/handlers/openai.rs:10-23`, `src-tauri/src/proxy/handlers/claude.rs:15-30`).

The “intelligence” lives in routing/retry/account-selection logic rather than multi-agent planning: request handlers transform incoming protocol payloads, choose token/account via `TokenManager`, call upstream APIs, and translate responses back (`src-tauri/src/proxy/handlers/openai.rs:159-220`, `src-tauri/src/proxy/token_manager.rs:41-64`). Additional intelligence appears as context/thinking transformations and tool/schema adaptation layers (`src-tauri/src/proxy/handlers/claude.rs:39-158`, `src-tauri/src/proxy/common/tool_adapter.rs:7-41`).

So architecturally this is best understood as a **single service orchestrator** for LLM API traffic, not multiple coordinated runtime agents with distinct roles.

## 3. Orchestration Pattern

Closest match: **event-driven request pipeline** (HTTP-driven), with some sequential internal stages (map model -> pick account -> transform -> upstream call -> postprocess).

Control flow is route-driven in Axum:

> `server.rs` wires protocol endpoints directly to handlers (`/v1/chat/completions`, `/v1/messages`, `/v1beta/models/...`) and applies middleware layers for filtering/auth/monitoring (`src-tauri/src/proxy/server.rs:371-452`).

Within a handler, control is sequential with retries/rotation, not agent-to-agent messaging:

```385:405:src-tauri/src/proxy/handlers/openai.rs
for attempt in 0..max_attempts {
    ...
    let (access_token, project_id, email, account_id, _wait_ms) = match token_manager
        .get_token(&config.request_type, attempt > 0, Some(&session_id), &mapped_model)
        .await
```

And routing itself is endpoint orchestration:

```376:383:src-tauri/src/proxy/server.rs
.route("/v1/models", get(handlers::openai::handle_list_models))
.route("/v1/chat/completions", post(handlers::openai::handle_chat_completions))
.route("/v1/completions", post(handlers::openai::handle_completions))
```

## 4. Tools & External Integrations

- **Upstream LLM APIs (OpenAI/Claude/Gemini-compatible):** handled via protocol-specific routes and transformers in `handlers/*` + `mappers/*` (`src-tauri/src/proxy/server.rs:375-429`, `src-tauri/src/proxy/handlers/openai.rs:10-12`, `src-tauri/src/proxy/handlers/claude.rs:15-20`).
- **z.ai services + MCP endpoints:** reverse-proxying `web_search_prime`, `web_reader`, and `zai-mcp-server` plus built-in vision MCP session handling (`src-tauri/src/proxy/server.rs:408-417`, `src-tauri/src/proxy/handlers/mcp.rs:116-157`, `src-tauri/src/proxy/handlers/mcp.rs:191-230`).
- **CLI ecosystem integration (terminal tools):** scans local installs and rewrites configs for Claude/Codex/Gemini/OpenCode CLI (`src-tauri/src/proxy/cli_sync.rs:13-72`, `src-tauri/src/proxy/cli_sync.rs:190-237`).
- **OpenCode provider/plugin integration:** model catalog and config generation for OpenCode (`src-tauri/src/proxy/opencode_sync.rs:50-177`).
- **Cloudflare tunnel integration:** managed Cloudflared state/commands exposed through app command layer (`src-tauri/src/lib.rs:568-573`, `src-tauri/src/proxy/server.rs:113`).
- **Local persistence/databases:** token stats, security, and user token DB initialized at startup (`src-tauri/src/lib.rs:124-137`).

No vector database/RAG store wiring (e.g., Chroma/Pinecone/pgvector) is evident in inspected runtime code.

## 5. Notable Code Walkthrough

- `src-tauri/src/lib.rs:109-289`  
  App entrypoint for desktop/headless modes; initializes DBs/config and starts proxy/admin services. This is where runtime mode and startup behavior are decided.

- `src-tauri/src/proxy/server.rs:364-452`  
  Central router assembly: OpenAI/Claude/Gemini/MCP endpoints plus middleware stack. This is the backbone of request orchestration.

- `src-tauri/src/proxy/handlers/openai.rs:28-260`  
  Main OpenAI-compatible request pipeline: format normalization, model routing, adapter detection, token/account acquisition, retries, upstream dispatch.

- `src-tauri/src/proxy/token_manager.rs:41-90` and `:126-208`  
  Core account pool manager for loading account files, rate-limit cleanup, session/account stickiness, and account lifecycle operations.

- `src-tauri/src/proxy/cli_sync.rs:166-240`  
  Defines supported CLI apps/config file targets and sync behavior, showing how this backend bridges local terminal AI clients to the managed proxy.

## 6. Use-Case Mapping

Assigned label `Browser / Terminal Use` is **partly correct**: the repo clearly integrates with terminal AI clients via CLI config sync (`src-tauri/src/proxy/cli_sync.rs:166-237`) and also exposes MCP/web-related endpoints (`src-tauri/src/proxy/server.rs:408-417`).  
However, the dominant behavior is broader **workflow automation for account/proxy operations**: startup, switching, retries, mapping, monitoring, and policy enforcement across multiple providers (`src-tauri/src/commands/proxy.rs:79-208`, `src-tauri/src/proxy/token_manager.rs:41-64`).  
Best fit after code inspection: **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Robust multi-protocol compatibility layer (OpenAI/Claude/Gemini/MCP) in one local service.
  - Practical production features: retries, account rotation, sticky sessions, circuit-breaker/rate-limit support.
  - Strong integration with real user tooling (CLI sync, desktop + headless modes, cloudflared exposure).
  - Clear separation of handlers/mappers/middleware/token manager modules.

- **Limitations:**
  - Not a true multi-agent runtime (no planner-worker/swarm debate graph despite “agent” terminology).
  - Large, complex handlers with substantial embedded logic make formal verification/testing harder.
  - Heavy provider-specific transformation code may be brittle as upstream APIs evolve.
  - Some behavior appears config- and side-effect-heavy, increasing operational complexity.

- **Research relevance:**
  - Useful evidence for **agent-adjacent orchestration infrastructure** (protocol normalization + account scheduling).
  - Good case study for **tool/client adaptation layers** around LLM APIs (adapters, schema transforms, MCP bridging).
  - Demonstrates real-world **operational control plane** patterns for LLM access, not MAS cognition algorithms.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
