---
repo_name: Narcooo/inkos
url: "https://github.com/Narcooo/inkos"
stars: 4810
forks: 929
contributors_count: 8
last_commit_date: "2026-04-22T09:13:10+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-04-27T13:22:45.045185+00:00"
model: auto
duration_s: 84.2
clone_size_kb: 6759
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`Narcooo/inkos` is a TypeScript monorepo for autonomous long-form novel production, where a user runs CLI commands (or Studio/TUI) to create books, generate chapters, audit quality/continuity, and auto-revise until acceptable. The core runtime (`packages/core`) maintains structured “truth files” and chapter state, then executes a multi-stage writing pipeline per chapter. Users can run atomic steps (`plan`, `compose`, `draft`, `audit`, `revise`) or one-shot automation (`write next`) from the terminal (`packages/cli/src/commands/*`). There is also a natural-language “agent mode” (`inkos agent`) where an LLM decides which internal tools to call. Output is a persisted book directory with chapters, runtime artifacts, and continuously updated world-state memory.

## 2. Agent Framework & Architecture

This is **not CrewAI/LangGraph/AutoGen** in implementation. It is a **custom multi-agent architecture** built around internal agent classes and a custom tool-calling loop, with LLM transport handled via `@mariozechner/pi-ai` (`packages/core/src/llm/provider.ts:1-20`, `:1073-1130`). The dependency list confirms this custom stack (`packages/core/package.json:46-54`), and core orchestration lives in `PipelineRunner` (`packages/core/src/pipeline/runner.ts:187+`).

Agents are role-specific classes (`ArchitectAgent`, `PlannerAgent`, `WriterAgent`, `ContinuityAuditor`, `ReviserAgent`, `RadarAgent`, etc.) instantiated directly inside pipeline methods (`packages/core/src/pipeline/runner.ts:8-22`, `:1378-1403`, `:2245-2312`). “Intelligence” is distributed across: (a) agent-specific prompts/parsers (e.g., planner memo + retry parse logic in `packages/core/src/agents/planner.ts:55-71`, `:235-262`), (b) deterministic governance/validation code (`packages/core/src/pipeline/chapter-review-cycle.ts:44-327`), and (c) tool-routed NL orchestration (`packages/core/src/pipeline/agent.ts:228-346`).

## 3. Orchestration Pattern

Closest match: **hierarchical sequential (manager-worker)** with iterative review loops.

A central manager (`PipelineRunner`) executes ordered worker agents per chapter (plan/compose/write/audit/revise/polish/persist). The review loop is explicit and bounded (`MAX_REVIEW_ITERATIONS = 3`) with score-based stop/rollback criteria (`packages/core/src/pipeline/chapter-review-cycle.ts:33-36`, `:221-291`, `:297-315`). In NL mode, another manager loop (`runAgentLoop`) repeatedly asks an LLM for tool calls and executes them until no calls remain (`packages/core/src/pipeline/agent.ts:311-343`).

```1343:1403:packages/core/src/pipeline/runner.ts
private async _writeNextChapterLocked(...) {
  ...
  const writer = new WriterAgent(this.agentCtxFor("writer", bookId));
  const output = await writer.writeChapter({...});
  const auditor = new ContinuityAuditor(this.agentCtxFor("auditor", bookId));
  const reviewResult = await runChapterReviewCycle({
    ...,
    createReviser: () => new ReviserAgent(this.agentCtxFor("reviser", bookId)),
    auditor,
  });
}
```

```311:341:packages/core/src/pipeline/agent.ts
for (let turn = 0; turn < maxTurns; turn++) {
  const result = await chatWithTools(config.client, config.model, messages, TOOLS);
  ...
  if (result.toolCalls.length === 0) break;
  for (const toolCall of result.toolCalls) {
    ...
    toolResult = await executeTool(pipeline, state, config, toolCall.name, args);
    messages.push({ role: "tool", toolCallId: toolCall.id, content: toolResult });
  }
}
```

## 4. Tools & External Integrations

- **LLM providers / model routing**: Extensive OpenAI/Anthropic-compatible and many provider endpoints; transport abstraction in `packages/core/src/llm/provider.ts` and provider registry in `packages/core/src/llm/providers/endpoints/*.ts`.
- **Tool-calling runtime**: Internal tool schema + execution router for NL agent mode in `packages/core/src/pipeline/agent.ts:7-219` and `:348-655`.
- **Web search/fetch**: Tavily search + URL fetching (`packages/core/src/utils/web-search.ts:19-49`, `:55-82`), exposed to agent via `web_fetch` tool (`packages/core/src/pipeline/agent.ts:509-513`).
- **Notifications/webhooks**: Telegram/Feishu/Wechat-work/webhook dispatch (`packages/core/src/notify/dispatcher.ts:12-86`, `telegram.ts:6-25`, `webhook.ts:26-58`).
- **SQLite temporal memory index**: `node:sqlite`-based `memory.db` for facts/hooks/summaries (`packages/core/src/state/memory-db.ts:1-10`, `:69-80`), used as acceleration over markdown truth files.
- **Filesystem as primary state store**: chapter files + truth/control docs are read/written directly throughout runner/agents (`packages/core/src/pipeline/runner.ts:814-859`, `:1260-1290`).

No browser automation (Playwright/Browserbase), shell-execution tools, or MCP server framework are wired as runtime agent tools.

## 5. Notable Code Walkthrough

- `packages/core/src/pipeline/runner.ts:1316-1537` - Core end-to-end chapter pipeline (`writeNextChapter`) that coordinates writer, auditor, reviser loop, polishing, and persistence; this is the operational heart of the MAS.
- `packages/core/src/pipeline/agent.ts:7-219,228-346,348-655` - Defines 18 callable tools and runs the LLM tool loop, bridging natural-language instructions to concrete pipeline operations.
- `packages/core/src/agents/planner.ts:76-172,179-262` - Planner builds chapter intent/memo from long-term control docs and retries on strict parse failures, showing prompt+parser governance rather than freeform text generation.
- `packages/core/src/pipeline/chapter-review-cycle.ts:44-327` - Deterministic quality-control loop: assess, revise, re-assess, score thresholds, and rollback to best snapshot.
- `packages/cli/src/commands/agent.ts:5-52` - User-facing CLI entrypoint for agentic mode (`inkos agent ...`) that invokes `runAgentLoop` with streaming callbacks and turn limits.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially accurate. This project is strongly **terminal-driven** (CLI-first), but the agents are not doing generic computer-use tasks (no browser automation, no shell-agent acting on arbitrary OS tasks). Instead, they automate a domain workflow: multi-step novel production with governance, audit, and revision.

A better category is **Workflow Automation**. The multi-agent system orchestrates repeated business logic over structured project state (`plan -> compose -> write -> audit -> revise`) and exposes it as composable commands/tool calls, rather than acting as a browser/terminal operator.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent role decomposition with explicit orchestration in code, not just prompt claims (`runner.ts` imports/instantiation).
  - Strong hybrid design: LLM agents plus deterministic validators/scoring loops (`chapter-review-cycle.ts`).
  - Supports both atomic operations and LLM tool-routed orchestration (`agent.ts`), useful for controllability.
  - Persistent long-horizon memory model (truth files + SQLite temporal index) for continuity-sensitive generation.
  - Extensive provider abstraction and per-agent model routing for cost/quality tuning.

- **Limitations:**
  - Architecture is complex and heavily file-coupled; many side effects in one large runner class may reduce maintainability (`runner.ts` very large).
  - Domain specificity is high (novel writing), limiting generalization without substantial prompt/rule redesign.
  - Tool-calling relies on one central NL loop and static tool list; no dynamic planner graph or learned policy.
  - Heavy dependence on prompt contracts + parser correctness (e.g., planner retries), which can still fail on weak models.
  - Browser/terminal “agentic computer-use” capabilities are largely absent despite terminal-centric UX.

- **Research relevance:**
  - Good evidence for **practical hierarchical MAS** combining LLM workers with deterministic governance and rollback.
  - Useful case study of **stateful long-form generation** with explicit memory artifacts and audit-driven correction loops.
  - Demonstrates **tool-using NL supervisor** over atomic domain actions in production-style CLI software.
  - Illustrates tradeoffs in real-world MAS engineering: reliability layers, guardrails, and human-review checkpoints.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
