---
repo_name: moazbuilds/CodeMachine-CLI
url: "https://github.com/moazbuilds/CodeMachine-CLI"
stars: 2444
forks: 235
contributors_count: 8
last_commit_date: "2026-02-25T21:08:57+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T15:06:38.606735+00:00"
model: auto
duration_s: 108.9
clone_size_kb: 9057
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`CodeMachine-CLI` is a TypeScript CLI runtime for running repeatable, long-lived coding workflows composed of multiple role-specific AI agents. A user runs the `codemachine` CLI, selects or loads a workflow template, and the system executes agent steps with pause/resume, autonomous/manual modes, and step-level progression controls (`src/runtime/cli-setup.ts:349-466`, `src/workflows/run.ts:43-343`). The output is not just one model response: it is an orchestrated workflow session with tracked agent runs, persisted state, and optional controller-driven delegation. It is designed to automate multi-step software/process work by turning prompts, templates, and agent definitions into an execution pipeline.

## 2. Agent Framework & Architecture

This repo does **not** use LangChain/LangGraph/CrewAI/AutoGen/LlamaIndex directly (no such imports found in source). It uses a **custom multi-agent framework** built in-house around:  
- a workflow FSM (`src/workflows/state/machine.ts:120-377`),  
- a workflow runner loop (`src/workflows/runner/index.ts:215-303`),  
- a coordinator DSL for parallel/sequential agent execution (`src/agents/coordinator/parser.ts:21-130`, `src/agents/coordinator/execution.ts:43-109`), and  
- pluggable engine adapters that call external model CLIs (`src/infra/engines/core/base.ts:67-82`, `src/infra/engines/providers/claude/execution/runner.ts:173-383`).

Agents are defined in workflow templates and agent config catalogs, then resolved at runtime. Each workflow step maps to a module agent (`agentId`, prompt paths, engine/model overrides, MCP permissions), and can include behaviors like loop/trigger/checkpoint (`src/workflows/templates/types.ts:33-48`, `src/workflows/templates/types.ts:6-27`). The “intelligence” is distributed across prompt templates, step/session state, and orchestration rules (mode handlers, directives, signal tools), rather than a single planner graph.

The architecture also supports nested coordination: agents can call MCP tools such as `run_agents`, which invokes the coordinator service to launch additional agents in parallel/sequential groups under parent-child monitoring relationships (`src/infra/mcp/servers/agent-coordination/tools.ts:16-50`, `src/infra/mcp/servers/agent-coordination/executor.ts:33-74`, `src/agents/coordinator/service.ts:63-104`).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker + state-machine orchestration** (with optional parallel worker groups).  
- The workflow runner acts as manager via FSM states (`running` → `awaiting`/`delegated` → transitions), while step agents are workers (`src/workflows/state/machine.ts:151-229`, `src/workflows/runner/index.ts:240-283`).  
- Within a step or MCP call, coordinator scripts can spawn multiple workers in parallel (`&`) or ordered sequences (`&&`) (`src/agents/coordinator/parser.ts:68-97`, `src/agents/coordinator/execution.ts:82-109`).

Example control flow excerpt:
```152:188:src/workflows/state/machine.ts
running: {
  on: {
    STEP_COMPLETE: [
      {
        target: 'delegated',
        guard: (ctx) => {
          const step = ctx.steps[ctx.currentStepIndex];
          const isInteractive = step?.interactive !== false;
          return ctx.autoMode && !ctx.paused && (ctx.hasController || !isInteractive);
        },
```

And coordinator execution pattern:
```46:87:src/agents/coordinator/execution.ts
// Execute groups sequentially (even if group itself is parallel)
for (const group of plan.groups) {
  const groupResults = await this.executeGroup(group);
  results.push(...groupResults);
}
...
private async executeParallel(commands: AgentCommand[]) {
  const promises = commands.map(cmd => this.executeCommand(cmd));
  return Promise.all(promises);
}
```

## 4. Tools & External Integrations

- **MCP (Model Context Protocol) servers + router**: custom in-process/external MCP aggregation and tool routing with per-agent tool filtering (`src/infra/mcp/router/index.ts:84-143`).
- **Agent coordination MCP tools**: `run_agents`, `get_agent_status`, `list_active_agents`, `list_available_agents` (`src/infra/mcp/servers/agent-coordination/tools.ts:16-146`, wired in `handler.ts:162-253`).
- **Workflow signal MCP tools**: structured step proposal/approval tools (`propose_step_completion`, `approve_step_transition`, `get_pending_proposal`) for transition gating (`src/infra/mcp/servers/workflow-signals/tools.ts:16-150`, `handler.ts:43-175`).
- **LLM engine CLIs (provider adapters)**: engine plugin interface plus provider runners (e.g., Claude CLI wrapper with streaming JSON parsing, telemetry/session extraction) (`src/infra/engines/core/base.ts:67-82`, `src/infra/engines/providers/claude/execution/runner.ts:233-311`).
- **Filesystem and local project context**: prompt/template loading, input file ingestion, placeholder resolution, and workspace persistence (`src/workflows/step/execute.ts:93-132`, `src/agents/coordinator/execution.ts:272-305`).
- **Observability**: OpenTelemetry logging/tracing/metrics bootstrap in CLI runtime (`src/runtime/cli-setup.ts:41-64`).

No external vector DB/RAG stack appears to be wired as a core dependency in the analyzed runtime path.

## 5. Notable Code Walkthrough

- `src/workflows/run.ts:43-343` - Main workflow entrypoint. It sets up workspace state, loads templates, filters steps by tracks/conditions, initializes event bus/status services, then constructs and runs `WorkflowRunner`.
- `src/workflows/runner/index.ts:215-303` - Core orchestration loop. It advances FSM states, executes step agents, handles awaiting/delegated modes, and finalizes workflow status.
- `src/workflows/state/machine.ts:151-356` - Explicit state machine for transitions among `running`, `awaiting`, `delegated`, and terminal states; this is the control backbone for manual vs autonomous behavior.
- `src/agents/runner/runner.ts:196-546` - Low-level agent executor. Resolves engine/model, handles auth fallback, writes MCP context for tool filtering, streams model output, persists monitoring/session IDs, and supports resume.
- `src/agents/coordinator/parser.ts:21-130` and `src/agents/coordinator/execution.ts:43-221` - Multi-agent script parser + executor implementing sequential/parallel groups and composite prompt building for coordinated sub-agent runs.

## 6. Use-Case Mapping

The assigned use case **Workflow Automation** is correct. The repository operationalizes workflow automation by encoding work into templates with ordered/conditional agent steps, then running them under a durable orchestration runtime (state machine, resume indexing, directives, signals) rather than one-off prompts (`src/workflows/templates/types.ts:94-103`, `src/workflows/run.ts:188-223`, `src/workflows/runner/index.ts:240-283`). It also supports automated progression and controller-governed delegation, making it suitable for repeatable multi-stage coding/ops flows rather than ad-hoc chat.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong runtime orchestration primitives (FSM, pause/resume, autonomous/manual switching) in production code (`src/workflows/state/machine.ts:120-377`).
  - True multi-agent execution modes including parallel and sequential groups via script DSL (`src/agents/coordinator/parser.ts:21-130`, `src/agents/coordinator/execution.ts:82-109`).
  - Tool-governed agent interaction through MCP with per-step/per-agent access filtering (`src/infra/mcp/router/index.ts:100-126`, `src/agents/runner/runner.ts:315-325`).
  - Practical operability: monitoring IDs, session continuity, log streams, and engine fallback/auth caching (`src/agents/runner/runner.ts:21-48`, `src/agents/runner/runner.ts:344-399`).

- **Limitations:**
  - Orchestration is mostly linear step sequencing + grouped parallelism; no general DAG optimizer/planner.
  - Coordinator parser explicitly notes simplified mixed-mode handling and no full parenthesized grammar in MVP path (`src/agents/coordinator/parser.ts:12-16`, `:99-130`).
  - Heavy dependence on external CLI engines (auth/install/runtime behavior can vary by environment) (`src/infra/engines/core/base.ts:17-23`, `src/infra/engines/providers/claude/execution/runner.ts:315-320`).
  - Architecture is complex and spread across many modules, increasing maintenance and verification overhead.

- **Research relevance:**
  - Good evidence for **applied hierarchical MAS orchestration** in developer tooling (manager FSM + worker agents + sub-agent groups).
  - Useful case study for **tool-mediated coordination protocols** (MCP-based signaling/approval instead of plain-text action tags).
  - Demonstrates **stateful multi-agent runtime concerns** (resume, monitoring lineage, mode switching, interruption handling) in real-world code.
  - Shows a pattern of **engine-agnostic orchestration layer** over heterogeneous LLM backends.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
