---
repo_name: AgentsMesh/AgentsMesh
url: "https://github.com/AgentsMesh/AgentsMesh"
stars: 1683
forks: 170
contributors_count: 13
last_commit_date: "2026-04-17T11:00:28+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T12:46:01.729516+00:00"
model: auto
duration_s: 136.0
clone_size_kb: 31526
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

AgentsMesh is a full-stack platform for running and coordinating AI coding agents in isolated “pods” (terminal sessions) managed by a backend and runner daemon. In practice, users create pods bound to specific repositories/runners/agents, then interact via UI/API while the runner executes Claude/Codex/Gemini-style CLIs in PTY or ACP mode. The system adds higher-level automation through “loops” (repeatable tasks with optional cron) and an autopilot controller that can keep driving a pod toward completion. It also supports cross-pod collaboration via MCP tools (discover pods, bind permissions, read/write another pod, channel messaging, trigger loops). So users get an operational agent workforce platform, not just a single chatbot wrapper.

## 2. Agent Framework & Architecture

This repo uses a **custom agent architecture** (Go backend + Go runner) rather than LangGraph/LangChain/CrewAI/AutoGen. I found no framework imports in runtime code; only a blog markdown mentions CrewAI/LangGraph terms. The orchestration primitives are homegrown in files like `runner/internal/autopilot/*`, `runner/internal/mcp/*`, and backend orchestrators like `backend/internal/service/loop/*` and `backend/internal/service/agentpod/*`.

At runtime, “agents” are primarily external agent CLIs launched inside pods (e.g., Claude Code/Codex/etc.), while AgentsMesh provides orchestration around them. `PodOrchestrator.CreatePod` builds effective AgentFile config and dispatches `create_pod` to runners (`backend/internal/service/agentpod/pod_orchestrator_create.go:16-208`). `RunnerMessageHandler.OnCreatePod` then creates the isolated pod process, wires relay, and starts PTY/ACP I/O (`runner/internal/runner/message_handler.go:35-145`).

A second layer of intelligence is the **AutopilotController**: a supervisory controller agent that observes pod state and sends next instructions iteratively (`runner/internal/autopilot/autopilot_controller.go:16-67`, `autopilot_controller_logic.go:7-79`). This control agent uses MCP tools (`get_pod_snapshot`, `send_pod_input`, `get_pod_status`) defined in the embedded prompt (`runner/internal/autopilot/prompt_builder.go:64-202`) and executed through ACP/CLI control-process runners (`runner/internal/autopilot/control_runner_acp.go:104-157`).

## 3. Orchestration Pattern

Closest match: **event-driven manager-worker orchestration** (with optional multi-agent collaboration tooling).

- **Manager-worker:** Autopilot acts as manager; target pod agent acts as worker.  
- **Event-driven:** iterations trigger on pod waiting-state transitions, not a static linear chain.

Excerpt 1 (event trigger -> decision cycle), `runner/internal/autopilot/autopilot_controller_logic.go:7-18`:

```go
func (ac *AutopilotController) OnPodWaiting() {
    if !ac.iterCtrl.CheckTriggerDedup() { return }
    if ac.userHandler.IsUserTakeover() { return }
    if !ac.phaseMgr.CanProcessIteration() { return }
    // ...
}
```

Excerpt 2 (loop orchestrator creates pod then optional autopilot), `backend/internal/service/loop/loop_orchestrator_start.go:64-76,111-115`:

```go
podResult, err := o.podOrchestrator.CreatePod(ctx, &agentpodSvc.OrchestrateCreatePodRequest{ ... })
if loop.IsAutopilot() && o.autopilotSvc != nil {
    autopilotKey, err = o.startAutopilot(ctx, loop, run, pod, resolvedPrompt)
}
```

For multi-agent (peer collaboration), MCP exposes tools to create/bind/control other pods (`runner/internal/mcp/http_tools_pod.go`, `http_tools_binding.go`), but that is capability-level orchestration rather than a fixed graph runtime.

## 4. Tools & External Integrations

- **Terminal/PTY + ACP agent execution**: Pod execution and prompt injection through PTY/ACP (`runner/internal/runner/message_handler.go:35-145`, `runner/internal/runner/message_handler_ops.go:122-144`).
- **MCP server (local HTTP)**: Runner starts an MCP HTTP server for collaboration/tooling (`runner/internal/mcp/http_server.go:35-87`, `89-135`).
- **MCP collaboration tools**:
  - Pod discovery: `list_available_pods`, `list_runners`, `list_repositories` (`runner/internal/mcp/http_tools_discovery.go:11-63`).
  - Pod control: `get_pod_snapshot`, `send_pod_input`, `get_pod_status` (`runner/internal/mcp/http_tools_pod_interaction.go:12-155`).
  - Binding/permissions between pods: `bind_pod`, `accept_binding`, etc. (`runner/internal/mcp/http_tools_binding.go:12-178`).
  - Channel messaging/docs: `send_channel_message`, `get_channel_messages`, `update_channel_document` (`runner/internal/mcp/http_tools_channel_messaging.go:12-182`).
  - Pod spawning and loop triggering via MCP: `create_pod`, `trigger_loop` (`runner/internal/mcp/http_tools_pod.go:74-186`, `runner/internal/mcp/http_tools_loop.go:57-85`).
- **Backend gRPC bridge for MCP tool calls**: MCP methods routed to backend services (`backend/internal/api/grpc/runner_adapter_mcp_pod.go:13-67`, `runner_adapter_mcp_discovery.go:15-176`).
- **Git repository/worktree sandboxing**: Pod creation includes repo/branch and sandbox resume semantics via orchestrator/runner workspace modules (`backend/internal/service/agentpod/pod_orchestrator_create.go:125-190`, loop resume usage in `loop_orchestrator_start.go:57-76`).
- **External MCP config support**: sidecar loads MCP config; root `.mcp.json` wires `chrome-devtools-mcp` (`runner/internal/runner/sidecar_services.go:32-49`, `.mcp.json:1-15`).

## 5. Notable Code Walkthrough

- `backend/internal/service/agentpod/pod_orchestrator_create.go:16-208`  
  Core pod lifecycle orchestrator: validates inputs, resolves AgentFile layers/config, picks runner, creates DB pod, builds runner command, and dispatches `create_pod`. This is the backend “control plane” center.

- `runner/internal/runner/message_handler.go:35-145`  
  Runner-side command handler for pod creation and startup; wires PTY/ACP, relay, monitor, and MCP registration. This is where backend intent becomes live agent process execution.

- `runner/internal/autopilot/autopilot_controller.go:16-67` and `runner/internal/autopilot/autopilot_decision.go:11-53`  
  Defines supervised autopilot composition and per-iteration decision loop with timeout/retry/error thresholds. This is the main autonomous orchestration logic.

- `runner/internal/autopilot/prompt_builder.go:64-202`  
  Encodes manager-agent prompting contract (control agent must supervise worker pod via MCP tools and emit structured decisions). This is where orchestration policy is prompt-engineered.

- `runner/internal/mcp/http_tools_pod.go:74-186` + `runner/internal/mcp/http_tools_binding.go:12-178`  
  Exposes tool surface for spawning/binding/interacting with other pods. This is what enables multi-agent collaboration and delegation across pods.

## 6. Use-Case Mapping

Although the upstream assigned use case is `Code Generation`, the codebase itself is broader and is better classified as **Workflow Automation** with code generation as a major workload. The loop subsystem models repeatable jobs with scheduling/triggering (`backend/internal/domain/loop/loop.go:46-97`), and `LoopOrchestrator` can instantiate pods plus autopilot to run those jobs end-to-end (`backend/internal/service/loop/loop_orchestrator_start.go:11-138`). Multi-pod bindings, channels, and tool-driven coordination further indicate generalized orchestration workflows beyond pure “generate code once.”

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong separation of control plane (backend) and execution plane (runner), with explicit pod orchestration boundaries.
  - Real multi-agent collaboration primitives (pod discovery, binding permissions, cross-pod I/O, channels) exposed as MCP tools.
  - Event-driven autopilot loop with lifecycle phases, dedup, retries, max-iteration guardrails.
  - AgentFile-based configuration layering gives reproducible per-agent runtime config.
  - Practical production concerns included: sandbox resume, relay wiring, status tracking, quota/error mapping.

- **Limitations:**
  - Heavy reliance on prompt conventions for control decisions (JSON parsing) can be brittle under model drift.
  - No explicit global planner graph for many agents; collaboration is tool-enabled but mostly decentralized/manual.
  - Control prompt and behavior are partly hardcoded (including Chinese prompt text), reducing portability/customization.
  - Architecture complexity is high (many services/protocol edges), raising operational/debug burden.
  - Multi-agent coordination quality depends on external agent CLI behavior, not fully deterministic internal logic.

- **Research relevance:**
  - Good evidence of **manager-worker supervisory loops** over tool-using terminal agents in real infrastructure.
  - Useful example of **MCP as inter-agent coordination substrate** (permissions, observation, action delegation).
  - Demonstrates **event-driven autonomous control** tied to execution-state signals (`waiting` transitions).
  - Illustrates practical design tradeoffs in production MAS platforms (isolation, tenancy, observability, policy layers).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
