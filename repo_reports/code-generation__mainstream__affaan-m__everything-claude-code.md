---
repo_name: affaan-m/everything-claude-code
url: "https://github.com/affaan-m/everything-claude-code"
stars: 164454
forks: 25531
contributors_count: 175
last_commit_date: "2026-04-21T22:41:36+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T10:01:07.321435+00:00"
model: auto
duration_s: 237.2
clone_size_kb: 59365
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`affaan-m/everything-claude-code` is a cross-harness agent operations toolkit, not a single runnable “app,” that installs and manages prompts, agent definitions, hooks, and orchestration helpers for Claude Code/Cursor/Codex-style environments. In practice, users run CLI commands like `ecc install`, `ecc plan`, `ecc doctor`, and orchestration scripts to provision a local agent workflow surface and monitor it (`scripts/ecc.js:7-52`, `scripts/install-apply.js:99-150`). The repository’s core value is operational: it standardizes how multiple specialized agents (planner, reviewer, security reviewer, etc.) are defined and coordinated, then enforces workflows via hooks and guardrails (`agents/planner.md:1-16`, `hooks/hooks.json:3-99`). It also includes a concrete tmux + git-worktree launcher that can run multiple worker agents in parallel and collect structured handoffs (`scripts/lib/tmux-worktree-orchestrator.js:175-311`, `scripts/orchestrate-codex-worker.sh:58-107`). So the user gets a reusable agent-harness layer for software delivery rather than a standalone chatbot product.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/AutoGen/CrewAI imports in the runtime orchestration path I inspected. The architecture is primarily **custom orchestration + harness-native agent specs**:
- Custom Node/Bash orchestration code for tmux/worktree worker execution (`scripts/orchestrate-worktrees.js:7-12`, `scripts/lib/tmux-worktree-orchestrator.js:482-587`, `scripts/orchestrate-codex-worker.sh:80-93`).
- Agent definitions as Markdown frontmatter files consumed by host harnesses (e.g., Claude Code) (`agents/planner.md:1-6`, `agents/code-reviewer.md:1-6`).
- Hook-driven control plane for policy and lifecycle events (`hooks/hooks.json:3-330`).

A secondary Python module (`src/llm/...`) provides a generic LLM provider abstraction (Anthropic/OpenAI/Ollama) and prompt adaptation (`src/llm/providers/resolver.py:14-35`, `src/llm/providers/claude.py:19-87`, `src/llm/prompt/builder.py:74-103`), but this is not the main multi-agent orchestration engine in the repo’s operational scripts.

“Intelligence” mostly lives in: (1) role prompts in `agents/*.md`, (2) skills in `skills/*/SKILL.md`, and (3) orchestration policies encoded in hook/launcher scripts.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)** with event-driven guardrails.

A manager script builds worker plans (branch/worktree/task/handoff/status), then launches each worker in a separate tmux pane:

```188:240:scripts/lib/tmux-worktree-orchestrator.js
const defaultLauncher = config.launcherCommand || '';
...
const workerPlans = workers.map((worker, index) => {
  ...
  const branchName = `orchestrator-${sessionName}-${workerSlug}`;
  const worktreePath = path.join(worktreeRoot, `${repoName}-${sessionName}-${workerSlug}`);
  ...
  const launcherCommand = worker.launcherCommand || defaultLauncher;
  ...
  return { ... launchCommand: renderTemplate(launcherCommand, templateVariables), ... };
});
```

Control then flows to execution: create worktrees, start tmux session, split panes, and send each pane a worker launch command:

```513:567:scripts/lib/tmux-worktree-orchestrator.js
for (const workerPlan of plan.workerPlans) {
  runCommandImpl('git', workerPlan.gitArgs, { cwd: plan.repoRoot });
  ...
}
...
const splitResult = runCommandImpl(
  'tmux',
  ['split-window', '-d', '-P', '-F', '#{pane_id}', '-t', plan.sessionName, '-c', workerPlan.worktreePath],
  { cwd: plan.repoRoot }
);
...
runCommandImpl('tmux', ['send-keys', '-t', paneId, `cd ${shellQuote(workerPlan.worktreePath)} && ${workerPlan.launchCommand}`, 'C-m'], ...)
```

The worker launcher (`scripts/orchestrate-codex-worker.sh`) acts as a constrained worker runtime, invoking `codex exec` with a task file and writing structured handoff/status artifacts (`scripts/orchestrate-codex-worker.sh:58-95`).

## 4. Tools & External Integrations

- **Claude/Codex CLI binaries**: worker execution and REPL wrappers call external CLIs (`scripts/orchestrate-codex-worker.sh:80`, `scripts/claw.js:86-104`).
- **tmux + git worktrees**: parallel multi-worker coordination and isolation (`scripts/lib/tmux-worktree-orchestrator.js:232-239`, `scripts/lib/tmux-worktree-orchestrator.js:523-567`).
- **MCP servers**: integrations for GitHub, Context7, Exa, Playwright, memory, etc. are wired in config (`.mcp.json:2-27`, `mcp-configs/mcp-servers.json:2-169`).
- **MCP health-control hook**: pre/post MCP-call probing, failure tracking, reconnect behavior (`scripts/hooks/mcp-health-check.js:5-13`, `scripts/hooks/mcp-health-check.js:486-549`).
- **Claude hook lifecycle integration**: PreToolUse/PostToolUse/Stop/Session hooks dispatch policy automation (`hooks/hooks.json:3-99`, `hooks/hooks.json:125-223`, `hooks/hooks.json:237-313`).
- **SQLite state store (`sql.js`)**: session/status persistence for CLI reporting (`scripts/lib/state-store/index.js:6-24`, `scripts/lib/state-store/index.js:164-184`).

No embedded vector DB/RAG pipeline is wired as a first-class runtime module in the core orchestration scripts I reviewed; retrieval-like capabilities are delegated to optional MCP services (e.g., Exa/Context7).

## 5. Notable Code Walkthrough

- `scripts/lib/tmux-worktree-orchestrator.js:175-311` — Builds normalized worker plans (tasks, branches, worktrees, launcher templates) and tmux command sequences; this is the central coordinator for multi-agent execution.
- `scripts/lib/tmux-worktree-orchestrator.js:482-587` — Executes orchestration with rollback semantics (cleanup of tmux/worktrees/branches on failure), showing production-oriented control-plane robustness.
- `scripts/orchestrate-codex-worker.sh:58-107` — Defines worker contract and invokes `codex exec`; captures deterministic handoff and status files for manager consumption.
- `hooks/hooks.json:3-330` — Declares event-driven governance across tool lifecycle (preflight checks, quality gates, MCP health, session telemetry), making orchestration policy-enforced rather than ad hoc.
- `scripts/claw.js:61-115` — Implements a lightweight session-aware REPL around `claude -p`, including skill-context loading and local history management, useful for single-agent interactive operation.

## 6. Use-Case Mapping

The upstream primary label (`Code Generation`) is only partially correct. This repo **enables** code generation workflows, but its implemented core is broader: it orchestrates, governs, and operationalizes agent workflows across harnesses (install, policy hooks, orchestration, session/state tracking). The strongest fit is **Workflow Automation** because the main runtime logic coordinates agent execution environments and lifecycle rules, rather than implementing one specific code-generation model pipeline (`scripts/ecc.js:7-52`, `scripts/install-apply.js:20-47`, `scripts/lib/tmux-worktree-orchestrator.js:482-587`, `hooks/hooks.json:3-330`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Mature, practical manager-worker orchestration using tmux + worktrees with rollback/cleanup safeguards (`scripts/lib/tmux-worktree-orchestrator.js:390-480`).
- Strong policy layer via hook events (quality, governance, MCP health, session telemetry) (`hooks/hooks.json:125-313`).
- Harness-agnostic packaging and selective install planning (`scripts/lib/install-manifests.js:374-538`).
- Rich integration surface through MCP configuration, including web, browser, docs, and VCS tools (`mcp-configs/mcp-servers.json:13-169`).

- **Limitations:**
- Heavy reliance on prompt/spec Markdown means behavior quality depends on external harness compliance, not strongly typed runtime logic (`agents/planner.md:1-16`).
- No unified, typed agent graph runtime (e.g., explicit DAG/state-machine abstraction) despite orchestration scripts.
- Operational complexity is high (many hooks and shell invocations), increasing debugging burden (`hooks/hooks.json:3-330`).
- Multi-agent execution is mostly shell-driven; limited in-process observability compared to purpose-built MAS frameworks.

- **Research relevance:**
- Useful evidence of **real-world agent ops engineering** (governance hooks + orchestration + lifecycle persistence) rather than toy benchmarks.
- Demonstrates a practical **manager-worker MAS pattern** over standard dev tools (git/tmux/CLI agents).
- Illustrates how **tool reliability controls** (MCP health checking/reconnect) are embedded in agentic workflows (`scripts/hooks/mcp-health-check.js:486-597`).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
