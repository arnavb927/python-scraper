---
repo_name: JackChen-me/open-multi-agent
url: "https://github.com/JackChen-me/open-multi-agent"
stars: 5828
forks: 2291
contributors_count: 12
last_commit_date: "2026-04-22T18:31:20+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 9
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-05-05T06:41:38.742157+00:00"
model: auto
duration_s: 71.2
clone_size_kb: 4038
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`open-multi-agent` is a TypeScript framework for orchestrating multiple LLM agents around a single goal, exposed both as an SDK (`OpenMultiAgent`) and a CLI (`oma`). In typical use, a developer defines a team of role-specific agents, then calls `runTeam(team, goal)` to automatically decompose work, execute tasks in dependency order (with parallelism), and synthesize a final answer (`src/orchestrator/orchestrator.ts:978-1303`). The same engine also supports explicit DAG execution via `runTasks` and one-shot execution via `runAgent` (`src/orchestrator/orchestrator.ts:1319-1383`, `901-972`). Users get structured outputs including per-agent results, task records, and token accounting (`src/orchestrator/orchestrator.ts:1659-1705`; `src/cli/oma.ts:241-253`).

## 2. Agent Framework & Architecture

This repo uses a **custom multi-agent framework**, not LangGraph/LangChain/CrewAI/AutoGen. The core imports and dependencies show in-house orchestrator/runner/tool abstractions and only model SDK deps (`@anthropic-ai/sdk`, `openai`, `zod`) (`package.json:62-71`; `src/agent/agent.ts`; `src/agent/runner.ts`; `src/orchestrator/orchestrator.ts`). A code search finds LangGraph/CrewAI mentions only in docs comparisons, not runtime imports (`README.md`, `docs/DECISIONS.md`).

Architecture is layered: `OpenMultiAgent` creates teams and runs workflows; `TaskQueue` manages dependency states; `Scheduler` assigns unassigned tasks; `AgentPool` enforces concurrency; each `Agent` runs an `AgentRunner` loop that alternates LLM turns and tool execution (`src/orchestrator/orchestrator.ts:519-773`; `src/task/queue.ts`; `src/orchestrator/scheduler.ts`; `src/agent/pool.ts`; `src/agent/runner.ts:673-1058`). “Intelligence” lives in two places: (1) LLM prompts for a temporary coordinator that decomposes/synthesizes goals, and (2) each worker agent’s own system prompt/tool loop (`src/orchestrator/orchestrator.ts:1094-1157`, `1427-1565`; `src/agent/agent.ts:156-179`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with DAG task execution**.

A temporary coordinator agent acts as manager: it plans tasks, workers execute, then coordinator synthesizes.

```ts
// src/orchestrator/orchestrator.ts:1094-1101,1118-1133
const coordinatorConfig: AgentConfig = {
  name: 'coordinator',
  ...
  systemPrompt: this.buildCoordinatorPrompt(agentConfigs, coordinatorOverrides),
}
const decompositionPrompt = this.buildDecompositionPrompt(goal, agentConfigs)
const decompositionResult = await coordinatorAgent.run(decompositionPrompt, decompTraceOptions)
agentResults.set('coordinator:decompose', decompositionResult)
```

Task control flow is queue-driven: pending tasks dispatch in parallel, dependency unblocking happens after completion, then the next round runs.

```ts
// src/orchestrator/orchestrator.ts:547-560,714-716,741-743
const pending = queue.getByStatus('pending')
...
const dispatchPromises = pending.map(async (task): Promise<void> => { ... })
...
const completedTask = queue.complete(task.id, result.output)
completedThisRound.push(completedTask)
...
await Promise.all(dispatchPromises)
```

This is not a LangGraph state machine; it is a dynamic, coordinator-generated DAG executed by queue + scheduler.

## 4. Tools & External Integrations

- **LLM providers (Anthropic/OpenAI/Gemini/Azure OpenAI/Bedrock/Grok/DeepSeek/etc.)**: adapter factory with lazy provider imports in `src/llm/adapter.ts:71-130`.
- **Shell/terminal execution**: built-in `bash` tool using `spawn('bash', ['-c', ...])` in `src/tool/built-in/bash.ts:22-63`, `93-97`.
- **Filesystem tools**: built-ins `file_read`, `file_write`, `file_edit`, plus `grep` and `glob` registered in `src/tool/built-in/index.ts:37-44,64-74`.
- **MCP servers**: `connectMCPTools()` bridges MCP stdio tools into framework tools (`src/tool/mcp.ts:230-296`), exported via subpath entrypoint (`src/mcp.ts:1-5`).
- **Inter-agent delegation tool**: `delegate_to_agent` enables synchronous handoff to another roster agent with depth/cycle checks (`src/tool/built-in/delegate.ts:24-108`).
- **CLI integration**: `oma run` and `oma task` wrap `runTeam`/`runTasks` for CI/shell usage (`src/cli/oma.ts:265-267`, `374-405`, `422-449`).
- **Not present**: no native browser automation stack (e.g., Playwright/Browserbase) or vector DB/RAG pipeline wiring in core runtime.

## 5. Notable Code Walkthrough

- `src/orchestrator/orchestrator.ts:978-1303` - Main `runTeam` pipeline: coordinator decomposition, task parsing/loading, queue execution, and coordinator synthesis; this is the project’s core MAS behavior.
- `src/agent/runner.ts:673-1058` - Core agent loop (`while (true)`): LLM call -> parse tool calls -> execute tools in parallel -> append tool results -> continue/break; includes loop detection, token budget checks, and context compaction.
- `src/task/queue.ts:55-177,424-446` - Dependency-aware queue with lifecycle events and unblock/cascade logic; determines when tasks become runnable and how failures propagate.
- `src/tool/mcp.ts:230-296` - MCP bridge that converts external MCP tool schemas/results into local `ToolDefinition`s, enabling tool surface extension without changing orchestrator code.
- `src/tool/built-in/delegate.ts:24-108` - Built-in agent-to-agent delegation tool; enforces guardrails (self-delegation, unknown target, cycle/depth limits, pool saturation) and returns delegated output + token metadata.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially accurate. The code clearly supports **terminal/file automation** via `bash` + filesystem tools (`src/tool/built-in/bash.ts`, `src/tool/built-in/index.ts`), and can orchestrate these across multiple agents. However, there is no first-class browser control module (no Playwright/Chromium primitives in core source). The better category is **Workflow Automation**: goal decomposition, dependency DAG execution, scheduling, retries, approval gates, and synthesis are the primary product behavior (`src/orchestrator/orchestrator.ts`, `src/task/queue.ts`, `src/orchestrator/scheduler.ts`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong end-to-end manager-worker orchestration with automatic decomposition and synthesis in one API (`runTeam`) (`src/orchestrator/orchestrator.ts:978-1303`).
  - Practical execution controls: retries, token budgeting, cancellation, progress/trace hooks (`src/orchestrator/orchestrator.ts:266-333`, `689-705`; `src/agent/runner.ts:798-811`).
  - Robust tool loop engineering: parallel tool execution, loop detection, context compaction/compression (`src/agent/runner.ts:885-983`, `817-858`, `1064-1276`).
  - Extensible integration model via runtime tools + MCP bridging (`src/tool/framework.ts`, `src/tool/mcp.ts`).

- **Limitations:**
  - Coordinator planning relies on JSON extraction from free-form LLM output (regex/JSON parse fallback), which is brittle under model drift (`src/orchestrator/orchestrator.ts:350-397`).
  - No persistent workflow checkpointing/resume state in core orchestration (in-memory execution-centric design).
  - Browser automation is not a native first-class capability despite terminal tooling.
  - Scheduler strategies are heuristic (keyword matching, round-robin, dependent counts), not learned or cost-aware (`src/orchestrator/scheduler.ts:245-320`).

- **Research relevance:**
  - Useful evidence for production-oriented hierarchical MAS design (coordinator + worker DAG) in TypeScript ecosystems.
  - Demonstrates concrete engineering patterns for tool-using LLM agents: safe loop termination, budget accounting, and context management.
  - Shows one implementation of hybrid orchestration (explicit DAG + optional intra-task delegation) with concurrency/deadlock safeguards (`src/tool/built-in/delegate.ts`, `src/agent/pool.ts`).

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
