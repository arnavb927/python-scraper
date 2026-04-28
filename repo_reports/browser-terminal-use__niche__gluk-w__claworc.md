---
repo_name: gluk-w/claworc
url: "https://github.com/gluk-w/claworc"
stars: 218
forks: 28
contributors_count: 7
last_commit_date: "2026-04-19T05:45:31+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:44:28.411019+00:00"
model: auto
duration_s: 81.6
clone_size_kb: 17298
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`gluk-w/claworc` is a control plane that runs and manages many isolated OpenClaw agent environments in Docker or Kubernetes, each with a browser, terminal, and gateway endpoint. A user runs the Go backend + React dashboard, creates instances, and then interacts with each instance through proxied chat, terminal, desktop (noVNC), and file APIs. The project also adds an internal “moderator” service that can auto-route Kanban tasks to the most suitable instance, execute them via OpenClaw chat sessions, and collect artifacts/evaluations. So the core value is operational orchestration of agent containers plus task-level automation on top of them. It is not an LLM framework itself; it is an orchestration platform around OpenClaw runtimes.

## 2. Agent Framework & Architecture

No LangChain/LangGraph/CrewAI/AutoGen/LlamaIndex framework is used in this repo (no matching imports; search returns none). The intelligence layer is custom Go code plus external OpenClaw runtime behavior inside containers. The control plane wires services in `control-plane/main.go` (notably `moderator.New(...)`, LLM gateway startup, SSH tunnels, and API routes).

Architecture has two AI layers:

1. **Per-instance OpenClaw agent runtime** inside the `agent/` image. The service script starts `openclaw gateway run`, configures gateway auth/basePath/model/provider defaults, and exposes browser/terminal tooling in that environment (`agent/rootfs/etc/s6-overlay/s6-rc.d/svc-openclaw/run`, `agent/TOOLS.md`).
2. **Control-plane moderator** (manager-like component) that dispatches Kanban tasks to one chosen instance, streams agent output, captures tool events/artifacts, and performs an evaluator LLM pass (`control-plane/internal/moderator/*.go`, `control-plane/internal/modwiring/adapters.go`).

So this is a **custom multi-instance orchestration system** where each worker is an OpenClaw agent instance, and the control-plane moderator performs routing/summarization/evaluation using separate LLM calls.

## 3. Orchestration Pattern

Closest pattern: **hierarchical (manager-worker)** with workflow automation semantics.

- Manager role: `moderator.Service` dispatches and runs tasks (`Dispatch` -> `Run`) and can stop/reopen jobs.
- Worker role: selected OpenClaw instance receives `chat.send` via gateway WebSocket session and executes work.
- Supporting control loop: periodic summarizer updates “souls” (instance summaries) used for routing.

Control flow evidence:

```15:25:control-plane/internal/moderator/dispatcher.go
func (s *Service) Dispatch(ctx context.Context, taskID uint) error {
    task, err := s.opts.Store.GetTask(ctx, taskID)
    // ...
    if len(board.EligibleInstances) == 1 {
        chosen = board.EligibleInstances[0]
    } else {
        chosen, reason, err = s.rank(ctx, task, board.EligibleInstances, souls)
    }
```

```77:93:control-plane/internal/moderator/runner.go
conn, err := s.opts.Dialer.Dial(ctx, instanceID, sessionKey)
// ...
sendFrame := map[string]any{
    "type":   "req",
    "id":     "kanban-send-1",
    "method": "chat.send",
    "params": map[string]any{
        "sessionKey": sessionKey,
        "message":    message,
```

This is not a peer swarm or graph-state engine; it is centrally managed dispatch/execution around independent agent instances.

## 4. Tools & External Integrations

- **OpenClaw gateway (WS/HTTP)**: proxied chat/control traffic to instances (`control-plane/internal/handlers/chat.go`, `control-plane/internal/handlers/control.go`, `control-plane/internal/modwiring/adapters.go`).
- **LLM providers (OpenAI-compatible + Anthropic-style APIs)**: internal token-resolving proxy and direct moderator completion calls (`control-plane/internal/llmgateway/gateway.go`, `control-plane/internal/modwiring/adapters.go`).
- **Browser automation runtime (CDP-backed Chromium)**: provided inside agent environment and consumed by OpenClaw tools (`agent/TOOLS.md`, `agent/Dockerfile`).
- **Terminal/SSH operations**: SSH manager/tunnels, file read/write/list, terminal WS sessions (`control-plane/internal/sshproxy/*`, `control-plane/internal/sshterminal/*`, `control-plane/internal/modwiring/adapters.go`).
- **Container orchestration backends**: Docker and Kubernetes instance lifecycle (`control-plane/internal/orchestrator/docker.go`, `control-plane/internal/orchestrator/kubernetes.go`).
- **Databases**: SQLite via GORM for control plane state and LLM usage logs (`control-plane/internal/database/*`, `control-plane/internal/llmgateway/gateway.go`).
- **Desktop/VNC stack**: noVNC/websockify + Xvnc in agent image, proxied in control-plane (`agent/Dockerfile`, `control-plane/internal/handlers/desktop.go`).
- **Provider catalog HTTP proxy**: admin API route to external catalog endpoint (`control-plane/main.go` `/llm/catalog` routes, handler implementation in `handlers/providers`).

No vector DB/RAG pipeline is central here.

## 5. Notable Code Walkthrough

- `control-plane/main.go:140-215` - Composes orchestrator, SSH/tunnel managers, internal LLM gateway, and moderator service; this is where agent/task automation is actually wired into runtime.
- `control-plane/internal/moderator/dispatcher.go:12-107` - LLM-based routing engine that chooses the best instance from board-eligible candidates using “soul” summaries.
- `control-plane/internal/moderator/runner.go:16-199` - End-to-end execution loop: builds prompt context, sends `chat.send`, streams assistant/tool events, collects artifacts, and marks task done/failed.
- `control-plane/internal/modwiring/adapters.go:29-269` - Concrete adapters from abstract moderator ports to SSH tunnels, workspace FS, and provider HTTP completion calls.
- `agent/rootfs/etc/s6-overlay/s6-rc.d/svc-openclaw/run:26-54` - Bootstraps and runs OpenClaw gateway in each container, including auth token, base path, and provider/model bootstrap config.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is partially correct for the per-instance runtime: each worker environment explicitly provides browser (CDP + VNC) and terminal/file operations (`agent/TOOLS.md`, SSH/file/terminal handlers). However, at repository level, the standout mechanism is **automated Kanban task routing and execution across multiple instances** (dispatch, run, evaluate), which is closer to **Workflow Automation** than a pure browser/terminal agent demo. 

So: browser/terminal is an enabling substrate, but the primary coordinated behavior implemented by this codebase is workflow orchestration of agent workers.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear manager-worker decomposition with dependency-inverted ports (`moderator/ports.go`) and concrete adapters (`modwiring/adapters.go`).
  - Production-minded infra integration: Docker/K8s lifecycle + SSH tunnels + VNC + auth + usage logging.
  - Practical task memory loop: prior artifacts/comments reinjected before reruns (`runner.go`).
  - Built-in evaluator and periodic “soul” summarization to improve routing decisions.
  - Internal LLM gateway abstracts provider keys and API-type differences centrally.

- **Limitations:**
  - No explicit multi-worker collaboration per task (dispatch selects one instance; no cooperative decomposition).
  - Routing relies on free-form LLM JSON output with simple fallback, limited formal guarantees.
  - Summarizer currently infers “soul” mainly from markdown files; shallow signal quality possible.
  - Tight coupling to OpenClaw gateway protocol/events for execution semantics.
  - Limited explicit benchmarking/ablation of routing quality vs non-LLM heuristics in repo code.

- **Research relevance:**
  - Evidence of a real-world **centralized orchestration layer** managing many autonomous LLM-agent runtimes.
  - Useful case of **LLM-in-the-loop scheduling/routing** over worker profiles (“souls”).
  - Demonstrates integration of agent execution with operational controls (auth, logs, artifacts, retries) in production-style systems.
  - Illustrates boundary between “agent framework” and “agent operations platform” in MAS-adjacent deployments.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
