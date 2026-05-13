---
repo_name: farion1231/cc-switch
url: "https://github.com/farion1231/cc-switch"
stars: 49438
forks: 3166
contributors_count: 97
last_commit_date: "2026-04-23T04:21:47+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:17:12.698782+00:00"
model: auto
duration_s: 103.0
clone_size_kb: 39369
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`cc-switch` is a cross-platform Tauri desktop control plane for AI coding CLIs (Claude Code, Codex, Gemini CLI, OpenCode, OpenClaw, Hermes), not a standalone chatbot runtime. A user runs the desktop app, configures multiple providers, MCP servers, prompts, and proxy/failover rules, and the app rewrites each tool’s local “live” config files plus runs a local HTTP proxy that routes requests to selected upstream models. The Rust backend persists state in SQLite and exposes many Tauri commands for the React frontend (`src-tauri/src/lib.rs:1032-1329`). In practice, users get centralized switching, failover, usage tracking, and config synchronization across several external agent tools.

## 2. Agent Framework & Architecture

This repo does **not** use LangChain/LangGraph/CrewAI/AutoGen/LlamaIndex in its own code (no such imports found in source). The architecture is mostly **custom orchestration + proxy middleware** in Rust, with a React/Tauri UI shell.

The core “intelligence” is in routing/failover logic and request transformation rather than planner-agent prompts. Provider selection is handled by a custom `ProviderRouter` with queue-based failover and circuit breakers (`src-tauri/src/proxy/provider_router.rs:16-109`). Request execution is handled by `RequestContext` + `RequestForwarder`, which picks provider chains, classifies errors, retries across providers, and records health (`src-tauri/src/proxy/handler_context.rs:127-171`, `src-tauri/src/proxy/forwarder.rs:114-756`).

“Agent” settings exist mainly as passthrough config management for **external** tools (especially OpenClaw `agents.defaults.*`), not locally executed role-based agents (`src-tauri/src/openclaw_config.rs:741-861`, `src-tauri/src/commands/openclaw.rs:45-91`).

## 3. Orchestration Pattern

Closest match: **event-driven workflow orchestration with sequential failover** (custom).

- Control flow is request-driven: HTTP proxy handlers create context, select an ordered provider list, then try providers in sequence.
- Failover and circuit-breaker state govern whether a provider is attempted; results feed back into health state.

Example (provider selection into request context):

```127:139:src-tauri/src/proxy/handler_context.rs
let providers = state
    .provider_router
    .select_providers(app_type_str)
    .await
    .map_err(|e| match e {
        crate::error::AppError::AllProvidersCircuitOpen => {
            ProxyError::AllProvidersCircuitOpen
        }
        crate::error::AppError::NoProvidersConfigured => ProxyError::NoProvidersConfigured,
        _ => ProxyError::DatabaseError(e.to_string()),
    })?;
```

Example (sequential failover loop):

```145:156:src-tauri/src/proxy/forwarder.rs
for provider in providers.iter() {
    let (allowed, used_half_open_permit) = if bypass_circuit_breaker {
        (true, false)
    } else {
        let permit = self
            .router
            .allow_provider_request(&provider.id, app_type_str)
            .await;
        (permit.allowed, permit.used_half_open_permit)
    };
```

## 4. Tools & External Integrations

- **Local proxy server + upstream LLM APIs**: Axum/Hyper proxy routes Claude/OpenAI/Gemini-style endpoints and forwards to configured providers (`src-tauri/src/proxy/server.rs:280-330`, `src-tauri/src/proxy/forwarder.rs:1419-1469`).
- **MCP server integration**: imports/syncs MCP entries across app configs (Claude/Codex/Gemini/OpenCode/Hermes) and persists SSOT in DB (`src-tauri/src/services/mcp.rs:13-51`, `:110-139`, `:243-430`).
- **External agent-tool live config manipulation**: reads/writes OpenClaw, Codex, Claude, Gemini, etc. config files; OpenClaw `agents.defaults`, `env`, `tools` sections are directly edited (`src-tauri/src/openclaw_config.rs:196-208`, `:741-912`).
- **Terminal integration**: launches/resumes sessions in external terminals (macOS-focused AppleScript/Open invocation) (`src-tauri/src/session_manager/terminal/mod.rs:3-30`, `:32-79`).
- **SQLite persistence + background workers**: app startup initializes DB, migrations, periodic usage sync, backup tasks, and WebDAV worker (`src-tauri/src/lib.rs:337-419`, `:930-981`, `:800-803`).
- **Deep-link ingestion**: `ccswitch://` links parsed and emitted to frontend for provider/MCP/prompt import workflows (`src-tauri/src/lib.rs:105-163`, `:727-751`).

## 5. Notable Code Walkthrough

- `src-tauri/src/proxy/forwarder.rs:114-756` - Core runtime request execution path: loops through provider candidates, applies retries/rectifiers, updates circuit-breaker health, and triggers failover switch updates.
- `src-tauri/src/proxy/provider_router.rs:32-109` - Provider selection strategy: current-provider mode vs failover-queue mode, with per-provider circuit-breaker gating.
- `src-tauri/src/services/mcp.rs:18-99` - Unified MCP CRUD and synchronization layer that propagates server changes into multiple external app ecosystems.
- `src-tauri/src/openclaw_config.rs:741-912` - Structured read/write API for OpenClaw `agents.defaults`, model catalog, env/tools; important because “agent” behavior is configured externally through this file.
- `src-tauri/src/lib.rs:1032-1329` - Tauri command surface that wires frontend actions to backend operations (providers, proxy, MCP, sessions, skills, prompts, usage).

## 6. Use-Case Mapping

Although it touches coding assistants, this repository is better categorized as **Workflow Automation** than pure `Code Generation`. It automates configuration, routing, failover, and operational control across multiple coding-agent CLIs, while the actual code generation happens in external tools/providers. The local proxy/failover chain (`src-tauri/src/proxy/forwarder.rs:114-756`) and multi-app config synchronization (`src-tauri/src/services/mcp.rs:173-192`, `src-tauri/src/lib.rs:612-680`) are orchestration infrastructure, not a direct in-repo coding agent.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong cross-tool unification (Claude/Codex/Gemini/OpenCode/OpenClaw/Hermes) under one control plane (`src-tauri/src/lib.rs:1032-1329`).
  - Mature failover/circuit-breaker machinery for production-ish reliability (`src-tauri/src/proxy/provider_router.rs:32-162`).
  - Rich protocol adaptation layer (Anthropic/OpenAI/Gemini endpoint and header handling) (`src-tauri/src/proxy/forwarder.rs:944-1811`).
  - Practical MCP synchronization workflows across heterogeneous apps (`src-tauri/src/services/mcp.rs:110-192`).
  - Defensive startup/recovery/backup logic for config takeover scenarios (`src-tauri/src/services/proxy.rs:206-260`, `src-tauri/src/lib.rs:879-908`).

- **Limitations:**
  - No native multi-agent reasoning/planning graph inside this codebase; “agents” are mostly external tool configs.
  - Very large, dense backend modules (notably proxy service/forwarder), raising maintenance complexity (`src-tauri/src/services/proxy.rs`, `src-tauri/src/proxy/forwarder.rs`).
  - Some terminal/session capabilities are platform-constrained (terminal resume path is macOS-only in current implementation) (`src-tauri/src/session_manager/terminal/mod.rs:13-15`).
  - Heavy reliance on rewriting external live configs can be brittle across upstream tool format changes.
  - Significant behavior encoded in operational logic rather than explicit declarative orchestration specs.

- **Research relevance:**
  - Useful evidence for **agent operations tooling** (multi-provider failover, health-aware routing, and runtime adaptation) in developer-agent ecosystems.
  - Demonstrates a pragmatic **agent middleware architecture**: protocol translation + reliability control between clients and model backends.
  - Illustrates MCP lifecycle management at scale across multiple host applications.
  - Good case study for “meta-agent infrastructure” (orchestration around agents) rather than in-model multi-agent collaboration algorithms.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
