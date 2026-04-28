---
repo_name: kelos-dev/kelos
url: "https://github.com/kelos-dev/kelos"
stars: 113
forks: 18
contributors_count: 4
last_commit_date: "2026-04-16T13:09:25+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T17:03:14.019703+00:00"
model: auto
duration_s: 89.1
clone_size_kb: 3107
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`kelos-dev/kelos` is a Kubernetes-native automation system that runs AI coding agents as Kubernetes `Task` resources and continuously spawns those tasks from external work sources (GitHub issues/PRs, Jira, cron ticks, and webhooks). Users deploy a controller plus per-source spawner loops; those loops discover work items and create `Task` CRs, and the controller converts each `Task` into a Kubernetes `Job` that runs an agent container (`claude-code`, `codex`, `gemini`, `opencode`, or `cursor`). The system handles dependency gating (`dependsOn`), branch locking, credential injection, and post-run output parsing from logs into structured task status. In practice, a user gets an always-on workflow where incoming events become agent executions that can open branches/PRs and report status back to source systems.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/AutoGen/CrewAI imports; it is a **custom multi-agent orchestration framework** built in Go on top of Kubernetes controller-runtime. The core runtime is in Kubernetes controllers and CRDs (`Task`, `TaskSpawner`, `Workspace`, `AgentConfig`) rather than a Python prompt-graph framework (`internal/controller/task_controller.go:65-167`, `api/v1alpha1/task_types.go:91-157`, `api/v1alpha1/taskspawner_types.go:622-662`).

“Agents” are external CLI agent containers selected by `task.spec.type` (`claude-code`, `codex`, `gemini`, `opencode`, `cursor`) and launched via Jobs (`internal/controller/job_builder.go:110-124`, `:351-358`). The intelligence split is:
- **Work discovery/planning layer:** spawner loop discovers work items from external systems and materializes tasks (`cmd/kelos-spawner/main.go:273-418`, `internal/source/github.go:83-160`).
- **Execution layer:** task controller resolves workspace/config/secrets and starts an agent container with prompt, model, repo, branch, MCP/plugin config (`internal/controller/task_controller.go:203-336`, `internal/controller/job_builder.go:499-566`).
- **Coordination logic:** dependency DAG checks, branch lock queueing, retriggering when new trigger comments/reviews appear (`internal/controller/task_controller.go:684-752`, `cmd/kelos-spawner/main.go:310-327`).

## 3. Orchestration Pattern

Closest match: **event-driven workflow orchestration** (with sequential dependency gating).

Control flow is driven by Kubernetes reconciliation plus external triggers (poll/webhook), not a centralized LLM manager planning sub-agents in-memory. A `TaskSpawner` event causes discovery; discovery creates `Task`; `Task` reconcile creates `Job`; terminal `Task` states re-enqueue dependents.

Example 1 (event-driven task creation from discovered items):
```369:417:cmd/kelos-spawner/main.go
task, err := tb.BuildTask(
    taskName,
    ts.Namespace,
    &ts.Spec.TaskTemplate,
    templateVars,
    &taskbuilder.SpawnerRef{...},
)
...
if err := cl.Create(ctx, task); err != nil { ... }
```

Example 2 (sequential gating across tasks via dependencies/branch locks):
```108:113:internal/controller/task_controller.go
if len(task.Spec.DependsOn) > 0 {
    ready, result, err := r.checkDependencies(ctx, &task)
    if err != nil || !ready {
        return result, err
    }
}
```

```930:980:internal/controller/task_controller.go
Watches(&kelosv1alpha1.Task{}, handler.EnqueueRequestsFromMapFunc(r.enqueueDependentTasks)).
...
// Re-enqueue tasks that depend on this task
```

## 4. Tools & External Integrations

- **Kubernetes API (CRDs, Jobs, Deployments, CronJobs, Pods, Secrets):** primary orchestration substrate (`internal/controller/task_controller.go`, `taskspawner_controller.go`, `workspace_controller.go`).
- **Agent CLIs in containers:** Claude Code, Codex, Gemini CLI, OpenCode, Cursor selected by task type (`internal/controller/job_builder.go:18-46`, `:110-124`).
- **GitHub REST API:** issue/PR discovery, comments/reviews, branch enrichment for issue_comment webhooks (`internal/source/github.go`, `internal/source/github_pr.go`, `internal/webhook/github_api.go`).
- **Jira REST API:** issue discovery with JQL and cloud/server auth modes (`internal/source/jira.go:78-199`).
- **Webhook ingestion (GitHub, Linear, Generic):** signature validation, filtering, idempotency cache, task creation (`internal/webhook/handler.go:144-257`, `github_filter.go`, `generic_filter.go`).
- **MCP servers:** configured in `AgentConfig`, rendered to `KELOS_MCP_SERVERS` JSON, secret-backed headers/env supported (`api/v1alpha1/agentconfig_types.go:28-33`, `internal/controller/job_builder.go:556-564`, `task_controller.go:425-470`).
- **Git operations / workspace bootstrap:** `git clone`, remote setup, branch checkout in init containers (`internal/controller/job_builder.go:382-475`).
- **skills.sh + plugin system:** installs skills via `npx skills add` and mounts plugin directory (`internal/controller/job_builder.go:522-554`, `:784-808`).
- **GitHub App token generation:** converts app creds to installation token for workspace/spawner usage (`internal/controller/task_controller.go:338-423`, `cmd/kelos-spawner/main.go:668-693`).
- **GitHub reporting back to source issues/PRs:** periodic reporting cycle in spawner (`cmd/kelos-spawner/reconciler.go:81-107`).

## 5. Notable Code Walkthrough

- `internal/controller/task_controller.go:65-167,203-336,684-752` - Main Task state machine: creates jobs, enforces dependency DAG/branch locks, captures outputs/results from pod logs, updates task lifecycle.
- `internal/controller/job_builder.go:238-358,364-497,499-566` - Converts Task spec into runnable agent job: credentials/env, workspace clone/branch prep, plugin/skills/MCP wiring.
- `cmd/kelos-spawner/main.go:273-471` - Discovery loop: fetches source items, deduplicates/retriggers, enforces concurrency/task budgets, creates Tasks and updates TaskSpawner status.
- `internal/source/github_pr.go:134-246,476-549` - Rich GitHub PR source adapter: review-state aggregation, comment-policy triggers, file-pattern filtering, trigger-time logic.
- `internal/webhook/handler.go:269-430,506-569` - Event-driven webhook executor: parses payloads, matches filters per spawner, builds template vars, creates uniquely named tasks idempotently.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is correct. This project automates an end-to-end ops pipeline: monitor external systems (GitHub/Jira/cron/webhooks), transform events into normalized work items, spawn/rate-limit agent executions, and track/report lifecycle in Kubernetes-native status objects. It is multi-agent in the sense of many coordinated agent runs (possibly chained via `dependsOn`) rather than one chat bot. While it uses code-generation agents, the core product value is orchestration/automation of those runs across workflows, not standalone code generation UX.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong Kubernetes-native control plane design with CRDs, reconciliation, and status-driven automation.
  - Supports multiple agent backends uniformly (Claude/Codex/Gemini/OpenCode/Cursor) with shared task contract.
  - Practical coordination features: dependency DAG, branch lock queueing, retrigger logic, concurrency/task-budget caps.
  - Broad trigger surface (polling + cron + GitHub/Linear/generic webhooks) with filtering and auth controls.
  - Extensibility via AgentConfig (plugins, skills.sh, MCP servers, custom instruction injection).

- **Limitations:**
  - No native LLM planner/critic/role-debate loop; “multi-agent” is orchestration of independent task runs, not cognitive collaboration in one runtime graph.
  - Output extraction relies on log markers/parsing (`ParseOutputs` path), which can be brittle across agent image changes.
  - Heavy dependence on external API availability/rate limits (GitHub/Jira) and Kubernetes operational complexity.
  - Task spec immutability and queue-by-reconcile model may constrain dynamic mid-flight replanning.
  - Security/secret handling is robust but still operationally sensitive due to many credential paths (PAT, app creds, MCP headers/env, webhook secrets).

- **Research relevance:**
  - Good real-world example of **agent orchestration as cloud-native workflow control**, not just prompt engineering.
  - Demonstrates event-driven MAS coordination patterns (triggering, dedupe, dependency gating, resource-constrained scheduling).
  - Useful evidence for studies comparing centralized “agent brain” frameworks vs decentralized controller-based automation.
  - Shows practical integration of MCP/plugin ecosystems into production-style agent execution pipelines.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
