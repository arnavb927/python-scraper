---
repo_name: gastownhall/gastown
url: "https://github.com/gastownhall/gastown"
stars: 14496
forks: 1317
contributors_count: 322
last_commit_date: "2026-04-22T20:02:27+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T10:59:25.966189+00:00"
model: auto
duration_s: 102.9
clone_size_kb: 26067
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`gastown` is a Go CLI system (`gt`) for running and coordinating multiple coding agents across a shared workspace, with persistent work state stored in Beads/Dolt instead of transient chat context. A user runs commands like `gt mayor attach`, `gt sling`, and `gt convoy` to dispatch tasks to role-specific agents (mayor, deacon, witness, polecats, crew) and monitor progress. The codebase focuses on operational reliability: it spins up agent runtimes in tmux sessions, injects startup prompts/hooks, tracks assignment/status in beads, and recovers from stale or dead sessions. The result is a workflow engine for multi-agent software work, not just a single chatbot shell.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex in runtime code. It is a **custom orchestration framework in Go**, with its own role model and runtime abstraction. The core dependency surface (`go.mod`) is Cobra + tmux/process tooling + Beads/Dolt + observability, while agent providers are external CLIs (Claude, Codex, Gemini, Cursor agent, Copilot, etc.) configured through internal presets.

The “intelligence” is split across:  
1) role/session startup prompts and hook injection (`internal/session/startup.go`, `internal/runtime/runtime.go`),  
2) dispatch/control logic (`internal/cmd/sling.go`), and  
3) persistent coordination state in Beads (assignees, statuses, molecules/convoys, mail).  

Agents are defined as runtime presets (command, args, hook capability, prompt mode, readiness semantics) in `internal/config/agents.go`, then instantiated per role by managers (e.g., witness/deacon/polecat managers).

```223:252:internal/config/agents.go
AgentClaude: {
    Name:                AgentClaude,
    Command:             "claude",
    Args:                []string{"--dangerously-skip-permissions"},
    ...
},
AgentCodex: {
    Name:                AgentCodex,
    Command:             "codex",
    ...
    SupportsHooks:       false,
    PromptMode:        "none",
```

## 3. Orchestration Pattern

Closest fit: **hierarchical manager-worker with event-driven messaging**.

- **Hierarchical:** `gt sling` acts as dispatcher/manager; it resolves target, can spawn polecats, hooks work, and starts sessions.
- **Event-driven:** mail/nudge queues provide asynchronous signaling to running sessions and turn-boundary delivery.

Control flow from dispatch to worker startup is explicit:

```659:688:internal/cmd/sling.go
resolved, err := resolveTarget(target, ResolveTargetOptions{
    ...
    HookBead:   beadID,
})
...
targetAgent := resolved.Agent
...
if err := hookBeadWithRetry(beadID, targetAgent, hookDir); err != nil {
    return err
}
```

```480:487:internal/polecat/session_manager.go
if err := m.tmux.NewSessionWithCommand(sessionID, workDir, command); err != nil {
    return fmt.Errorf("creating session: %w", err)
}
```

The event-driven notification layer (mail -> idle nudge / queued nudge fallback) is handled in router logic:

```1633:1660:internal/mail/router.go
waitErr := r.tmux.WaitForIdle(sessionID, timeout)
if waitErr == nil {
    if err := r.tmux.NudgeSession(sessionID, notification); err == nil {
        ...
    }
} else if r.townRoot != "" {
    if err := nudge.Enqueue(r.townRoot, sessionID, nudge.QueuedNudge{
        Sender:   msg.From,
        Message:  notification,
```

## 4. Tools & External Integrations

- **LLM agent CLIs (Claude/Codex/Gemini/Cursor/Copilot/OpenCode/etc.)**: runtime preset registry and startup wiring in `internal/config/agents.go` and `internal/config/*` resolution paths.
- **tmux terminal control**: session lifecycle, readiness checks, nudges, pane health in `internal/tmux/tmux.go`; invoked broadly by role/session managers.
- **Beads + Dolt work/state backend**: issue routing, assignees, mail, convoys, queueing in `internal/beads/*`, `internal/mail/router.go`, `internal/cmd/sling.go`, `internal/polecat/manager.go`.
- **Git worktrees**: polecat workspace creation/removal and branch lifecycle in `internal/polecat/manager.go`.
- **GitHub CLI (`gh`)**: merge queue/dashboard PR data in `internal/web/fetcher.go`.
- **OpenTelemetry**: event/metric emission across runtime and lifecycle paths (`internal/telemetry/*`).
- **Browser integration**: no core browser-automation agent loop found; `go-rod` appears in browser E2E test files (`internal/web/browser_e2e_test.go`), while production web code is dashboard/HTTP + subprocess fetchers.

## 5. Notable Code Walkthrough

- `internal/cmd/sling.go:25-1100`  
  Main orchestration command. Resolves targets, enforces dispatch rules, handles formulas/convoys, hooks beads, triggers session nudges, and manages rollback paths on failed startup.

- `internal/polecat/session_manager.go:341-645`  
  Worker-session startup pipeline: resolve runtime config, build startup beacon/prompt, create tmux session, set env + liveness metadata, wait for readiness, and deliver fallback nudges for non-hook runtimes.

- `internal/polecat/manager.go:524-1048`  
  Worker provisioning lifecycle (git worktree, CLAUDE/PRIME provisioning, shared beads redirect, runtime settings, agent bead creation) with robust cleanup/rollback and concurrency locks.

- `internal/config/agents.go:13-513`  
  Canonical provider abstraction (command, args, hooks support, prompt mode, readiness, process matching) enabling the same orchestration layer to run multiple agent CLIs.

- `internal/mail/router.go:853-1700`  
  Event-driven communication substrate: durable message creation in beads, address/group resolution, and runtime delivery via direct nudge or queued nudge when session is busy.

## 6. Use-Case Mapping

Assigned primary use case (`Browser / Terminal Use`) is **partially true**, but the stronger classification is **Workflow Automation**. The dominant behavior is multi-agent task routing, lifecycle management, and persistent stateful coordination for software workflows (`sling`, convoys, mail, watchdog roles, merge/refinery). Terminal interaction (tmux sessions, CLI nudges) is the execution substrate, not the end-user task domain. Browser functionality is mostly dashboard/monitoring, not autonomous browser-task solving.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong runtime abstraction across many agent CLIs via a uniform preset model.
  - Durable coordination state (Beads/Dolt) decouples workflow memory from LLM context windows.
  - Practical reliability engineering: stale-session detection, retry/backoff, rollback, lock-based race control.
  - Multi-role operations (deacon/witness/polecat/refinery) implemented as concrete runtime processes, not just conceptual docs.
  - Hybrid sync/async control plane (direct tmux nudge + queued nudge/mail).

- **Limitations:**
  - Heavy operational complexity (many moving parts: tmux, bd/dolt, hooks, role configs) raises deployment/debug burden.
  - External CLI/runtime dependence means behavior quality varies by provider and local environment.
  - Logic is distributed across large command/manager files, making formal reasoning and verification hard.
  - Browser automation is not central in production runtime despite “browser” ecosystem references.
  - Some integrations are subprocess-driven (`bd`, `gh`, `tmux`), which can be brittle under platform differences.

- **Research relevance:**
  - Good real-world example of **multi-agent orchestration as systems engineering**, not prompt-only composition.
  - Illustrates manager-worker + event-queue hybrid control in production-style dev workflows.
  - Useful evidence for studying persistence-backed agent coordination (state in DB/ledger vs. chat memory).
  - Shows practical failure-handling patterns (session liveness, queue fallback, recovery loops) in MAS operations.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
