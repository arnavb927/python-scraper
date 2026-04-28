---
repo_name: vinilana/dotcontext
url: "https://github.com/vinilana/dotcontext"
stars: 476
forks: 89
contributors_count: 7
last_commit_date: "2026-04-12T06:24:58+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:19:37.353933+00:00"
model: auto
duration_s: 89.4
clone_size_kb: 3173
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`dotcontext` is a TypeScript runtime that gives AI coding tools a structured execution layer (PREVC workflow + harness state), rather than acting as an LLM app itself. Users typically run `dotcontext mcp` (or `npx @dotcontext/mcp install`) to expose MCP tools, then drive planning/execution from an external AI client (Cursor/Claude/Copilot, etc.). The system persists sessions, traces, artifacts, tasks, handoffs, and policy decisions under `.context/harness`, and also manages PREVC phase progression (`P->R->E->V->C`). In practice, users get an auditable workflow controller for agentic software delivery, plus sync/export tooling for agent docs/skills across ecosystems.

## 2. Agent Framework & Architecture

This repo uses a **custom agent orchestration framework**; it does **not** use LangChain/LangGraph/CrewAI/AutoGen/LlamaIndex (no such runtime imports in `src`, and dependencies center on MCP SDK, CLI, filesystem, zod). The key boundary is explicitly `cli -> harness <- mcp` (`src/index.ts`, `src/services/mcp/mcpServer.ts`, `src/services/harness/*`).

“Agents” are represented as typed specialist roles (`feature-developer`, `code-reviewer`, etc.) with routing/sequence logic in `src/workflow/orchestration/agentOrchestrator.ts:14-259`. Workflow intelligence lives in deterministic orchestration rules: phase-to-agent mappings, keyword routing, handoff sequences, gate checks, and policy checks (`src/workflow/orchestrator.ts:52-577`, `src/services/workflow/workflowService.ts:176-905`), not in model-level planning code.

The MCP server exposes these capabilities as tools (`agent`, `workflow-init`, `workflow-advance`, `workflow-manage`, `harness`, etc.) so an external LLM client can invoke them (`src/services/mcp/mcpServer.ts:107-721`). So the repo is a runtime/control plane for agentic work, while LLM inference is delegated to the host AI tool.

## 3. Orchestration Pattern

Closest match: **hierarchical + state-machine workflow orchestration** (manager/worker flavor), backed by a **phase-gated PREVC state machine**.

- The PREVC orchestrator enforces phase transitions and gates (`src/workflow/orchestrator.ts:368-402`), while workflow service applies policy/backpressure before advancing (`src/services/workflow/workflowService.ts:313-359`).
- Agent routing is deterministic and centrally managed (`src/workflow/orchestration/agentOrchestrator.ts:36-81`, `:216-259`), then invoked by MCP handlers.

Example flow excerpts:

```209:224:src/workflow/orchestrator.ts
async handoff(
  from: string,
  to: string,
  artifacts: string[]
): Promise<void> {
  await this.statusManager.updateAgent(from, {
    status: 'completed',
    outputs: artifacts,
  });
  await this.statusManager.updateAgent(to, { status: 'in_progress' });
}
```

```313:333:src/services/workflow/workflowService.ts
async advance(outputs?: string[], options?: { force?: boolean }): Promise<PrevcPhase | null> {
  const currentPhase = await this.orchestrator.getCurrentPhase();
  if (!options?.force) {
    const approval = await this.getApproval();
    await this.policyService.authorize({ tool: 'workflow', action: 'advance', risk: 'high', approval: approval?.plan_approved
      ? { approvedBy: approval.approved_by, note: approval.approval_notes }
      : undefined });
    const harnessStatus = await this.getHarnessStatus();
    if (harnessStatus?.completionCheck.blocked) throw new HarnessWorkflowBlockedError(...)
  }
```

## 4. Tools & External Integrations

- **MCP server/tooling** via `@modelcontextprotocol/sdk` (`src/services/mcp/mcpServer.ts:10-12`, `:113-721`), exposing exploration, workflow, agent, and harness operations.
- **Filesystem-backed runtime store** (sessions/traces/artifacts/checkpoints) under `.context/harness` (`src/services/harness/runtimeStateService.ts:122-425`).
- **Shell/terminal command execution for sensors** (`child_process.exec`) to run quality gates like tests/lint (`src/services/workflow/workflowService.ts:867-896`).
- **Git integration** for diff tracking, staging, and commits (`src/utils/gitService.ts:24-537`), including plan-phase commit support in workflow tooling.
- **Semantic code analysis** via optional **tree-sitter** + regex fallback (`src/services/semantic/treeSitter/treeSitterLayer.ts:24-568`) and semantic context generation (`src/services/semantic/contextBuilder.ts:45-819`).
- **No direct LLM provider SDK integration** (no OpenAI/Anthropic/LangChain runtime imports in `src`); LLM calls are expected from external MCP clients.

## 5. Notable Code Walkthrough

- `src/services/mcp/mcpServer.ts:107-721` - Registers the full MCP tool surface (`context`, `workflow-*`, `agent`, `harness`, etc.); this is the primary entrypoint through which AI assistants control the runtime.
- `src/services/workflow/workflowService.ts:114-905` - High-level PREVC service combining orchestrator, harness state, policies, sensors, and task/handoff contracts; central coordinator for runtime behavior.
- `src/workflow/orchestrator.ts:52-577` - Core PREVC state machine managing phase lifecycle, gate enforcement, role/agent state updates, and orchestration guidance.
- `src/workflow/orchestration/agentOrchestrator.ts:14-321` - Defines agent taxonomy and deterministic routing logic (phase/role/task keyword to agent sequence).
- `src/services/harness/runtimeStateService.ts:122-425` - Durable persistence layer for session telemetry and artifacts, enabling replayable and auditable workflows.

## 6. Use-Case Mapping

Although the upstream label says **Code Generation**, the codebase is better classified as **Workflow Automation** for AI-assisted engineering. It does not implement code-generation pipelines with embedded model calls; instead, it orchestrates process execution (planning, handoffs, approvals, sensors, policies, replay datasets) around external AI tools. Code generation can happen through connected clients, but this repo’s core value is governance, coordination, and operational control of agentic workflows (`src/services/mcp/mcpServer.ts`, `src/services/workflow/workflowService.ts`, `src/services/harness/executionService.ts`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong separation of concerns (`cli`, `harness`, `mcp`) with reusable runtime boundary.
  - Durable, auditable execution model (sessions/traces/artifacts/checkpoints/replay).
  - Explicit policy and gate enforcement before risky transitions/actions.
  - Deterministic multi-role orchestration abstractions (agent selection + handoff flows).
  - Broad MCP tool surface enabling integration with many AI coding clients.

- **Limitations:**
  - No built-in LLM runtime; orchestration depends on external clients to actually “be” agents.
  - Agent selection is mostly static/keyword-based heuristics, not adaptive planning.
  - Collaboration synthesis is rule/keyword-based text handling, not model-mediated reasoning (`src/workflow/collaboration.ts:140-214`).
  - Heavy filesystem JSON state can become operationally complex for large teams/repos.
  - Sensor execution relies on local shell commands and available scripts, limiting portability.

- **Research relevance:**
  - Evidence for **runtime-governed agent engineering** (policy + backpressure + contracts) rather than prompt-only control.
  - Useful example of **MCP-mediated orchestration layer** separating transport from execution semantics.
  - Demonstrates **human/LLM hybrid multi-agent scaffolding** where “agents” are structured roles with explicit handoffs.
  - Supports study of **traceability and postmortem analysis** through replay and failure dataset clustering.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
