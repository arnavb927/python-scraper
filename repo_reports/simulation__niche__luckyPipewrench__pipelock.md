---
repo_name: luckyPipewrench/pipelock
url: "https://github.com/luckyPipewrench/pipelock"
stars: 340
forks: 35
contributors_count: 4
last_commit_date: "2026-04-22T20:17:24+00:00"
primary_use_case: Simulation
user_tier: Niche
total_score: 4
architecture_labels: [LangGraph, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T15:36:57.056271+00:00"
model: auto
duration_s: 76.3
clone_size_kb: 20173
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`pipelock` is a Go security proxy that sits between an AI agent runtime and external network/tool surfaces, then enforces scanning and policy decisions before traffic reaches the model process. In practice, users run CLI commands like `pipelock run` (HTTP/fetch/forward proxy) or `pipelock mcp proxy` (MCP stdio/HTTP/WS wrapper), and route agent traffic through it. The binary scans outbound inputs (DLP, SSRF, policy, tool-chain behavior) and inbound responses (prompt-injection/tool-poisoning), then blocks/warns/strips/asks based on config. It is not an LLM application itself; it is an enforcement and mediation layer around agent systems.

## 2. Agent Framework & Architecture

This repo does **not** implement LangGraph/LangChain/AutoGen/CrewAI runtime agents. The dependency graph (`go.mod`) has no agent framework libraries, and the core runtime is custom Go proxy code (`go.mod:5-28`). The references to CrewAI/LangGraph/AutoGen are in project-scanning heuristics, not execution-time orchestration (`internal/projectscan/detect.go:15-57`).

Architecture is custom and policy-driven: CLI wiring builds a runtime server/proxy stack (`internal/cli/root.go:43-131`, `internal/cli/runtime/server.go:282-577`), while MCP/HTTP paths are scanned by dedicated components (`internal/mcp/proxy.go`, `internal/mcp/proxy_http.go`, `internal/mcp/input_scan.go`, `internal/proxy/proxy.go`). The “intelligence” lives in scanner/policy rules and gating logic, not in prompts or model-generated plans. So this is agent-security infrastructure for external agent systems, not a multi-agent runtime itself.

## 3. Orchestration Pattern

Closest match: **other (policy-gated middleware pipeline / event-driven proxy)**, not multi-agent orchestration.

Control flow is request/response pipeline execution with layered gates:

- MCP subprocess mode runs concurrent input and output scan loops around a child server process (`internal/mcp/proxy.go:1028-1092`).
- HTTP listener mode processes each request through sequential gates (kill switch -> input scan -> policy -> upstream -> response scan) (`internal/mcp/proxy_http.go:1155-1405`).

Example excerpt 1 (`internal/mcp/proxy.go:1035-1046`):
```go
if inputCfg != nil && inputCfg.Enabled {
    ForwardScannedInput(...)
} else if opts.policyCfg() != nil || bindingCfg != nil || opts.chainMatcher() != nil {
    ForwardScannedInput(... config.ActionWarn, config.ActionBlock, ...)
}
```

Example excerpt 2 (`internal/mcp/proxy_http.go:1287-1305`):
```go
decision := scanHTTPInputDecision(body, safeLogW, chainSessionKey, auditSessionKey, scanOpts)
if blocked := decision.Blocked; blocked != nil {
    if blocked.SyntheticResponse != nil {
        _, _ = w.Write(blocked.SyntheticResponse)
    } else {
        _, _ = w.Write(blockRequestResponse(*blocked))
    }
    return
}
```

## 4. Tools & External Integrations

- **MCP servers (stdio subprocess wrapping)**: launches and mediates arbitrary MCP server commands via `exec.CommandContext` (`internal/mcp/proxy.go:844-875`).
- **MCP HTTP upstream**: stdio-to-HTTP bridge and reverse-proxy listener (`internal/mcp/proxy_http.go:34-49`, `943-966`).
- **MCP WebSocket upstream**: WS proxy mode from CLI (`internal/cli/runtime/mcp.go:645-673`).
- **General HTTP proxy/fetch/WebSocket proxy**: `/fetch`, `/ws`, CONNECT/forward proxy endpoints (`internal/proxy/proxy.go:1926-1934`).
- **Kill switch + admin/session APIs**: API endpoints for kill switch and session controls (`internal/proxy/proxy.go:1937-1944`, `internal/cli/runtime/server.go:700-739`).
- **Observability sinks**: webhook/syslog/OTLP emitters (`internal/cli/runtime/run.go:205-262`).
- **Sentry error reporting**: optional runtime initialization (`internal/cli/runtime/mcp.go:334-341`, `internal/cli/runtime/server.go:362-367`).
- **Flight recorder / signed receipts**: tamper-evident decision logging (`internal/cli/runtime/mcp.go:505-568`, `internal/cli/runtime/server.go:483-549`).
- **Sandboxing and file sentry**: optional containment and file-write DLP monitoring in MCP subprocess mode (`internal/cli/runtime/mcp.go:750-834`, `847-919`).

No vector store/RAG index/browser automation framework is wired as agent tools inside this repo.

## 5. Notable Code Walkthrough

- `internal/cli/runtime/mcp.go:190-956` - Main MCP command surface (`scan`, `proxy`) that chooses transport modes, builds scanner/policy/tool-chain configs, and launches the corresponding proxy runner.
- `internal/mcp/proxy.go:827-1144` - Core stdio MCP mediation loop: spawns child MCP server, runs bidirectional scan goroutines, tracks request IDs, and enforces fail-closed behavior.
- `internal/mcp/proxy_http.go:213-789` - HTTP-side input decision engine combining DLP/injection/policy/chain/taint/DoW checks into a strictest-action verdict.
- `internal/proxy/proxy.go:1921-1988` - Main HTTP proxy route composition and server startup for `/fetch`, `/ws`, metrics/stats, and security APIs.
- `internal/cli/runtime/server.go:584-1157` - Runtime lifecycle orchestration: listener binding, hot-reload integration, MCP listener startup, metrics/API servers, and graceful shutdown sequencing.

## 6. Use-Case Mapping

The assigned primary use case **Simulation** appears incorrect. The code is not simulating agents or environments; it is an operational control plane that automates security enforcement over agent traffic and tool calls. A better fit is **Workflow Automation**: it automates runtime mediation, risk scoring, blocking/redirecting actions, and audit/receipt generation across HTTP/MCP workflows (`internal/mcp/input_scan.go`, `internal/mcp/proxy*.go`, `internal/proxy/proxy.go`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Strong fail-closed enforcement patterns across parse errors, kill-switch states, and malformed MCP traffic (`internal/mcp/proxy.go`, `internal/mcp/proxy_http.go`).
- Broad transport coverage (MCP stdio, MCP HTTP, MCP WS, fetch/forward/WebSocket HTTP proxy paths).
- Rich policy stack beyond prompt injection: DLP, tool poisoning, tool-chain detection, taint, denial-of-wallet, redaction.
- Hot-reload-aware runtime with preserved security state and guarded restart-only config changes (`internal/cli/runtime/server.go:1172-1393`).
- Good operational hooks: metrics, signed receipts, capture/recorder, session APIs.

- **Limitations:**
- No in-repo LLM reasoning/planning runtime; protections depend on external agent systems routing through pipelock.
- No true multi-agent coordination logic (no planner-worker/swarms/agent graph execution engine).
- Some functionality is mode/transport-conditional and operationally complex (many config toggles and runtime branches).
- MCP and policy behavior relies heavily on rule quality; false positives/negatives are still a practical risk in pattern-based scanning.

- **Research relevance:**
- Evidence for **agent firewall / egress mediation** design in agentic ecosystems.
- Useful case study for **policy-composed safety gates** (DLP + injection + tool policy + behavioral escalation) on tool traffic.
- Practical reference for **transport-parity security engineering** across heterogeneous agent interfaces (HTTP/WS/MCP).
- Demonstrates operational security patterns (fail-closed defaults, hot-reload safety, signed audit trails) rather than MAS cognition.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
