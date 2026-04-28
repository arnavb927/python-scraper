---
repo_name: Enderfga/openclaw-claude-code
url: "https://github.com/Enderfga/openclaw-claude-code"
stars: 386
forks: 60
contributors_count: 7
last_commit_date: "2026-04-16T15:51:22+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T17:21:37.152432+00:00"
model: auto
duration_s: 58.3
clone_size_kb: 1888
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`openclaw-claude-code` is an OpenClaw plugin that turns coding CLIs (Claude Code, Codex, Gemini, Cursor, or a custom CLI) into managed, programmable “agent sessions” with tool APIs and optional multi-agent coordination. A user runs it through OpenClaw plugin tools (e.g., `claude_session_start`, `claude_session_send`, `council_start`) or via the embedded HTTP server/OpenAI-compatible endpoint. The system maintains session lifecycle, routing, persistence, and cost/context telemetry so agent workflows can run unattended. Its core value is workflow automation for coding tasks: orchestrating autonomous agent runs, team-style collaboration, and review/planning loops from one control plane.

## 2. Agent Framework & Architecture

This repo does **not** use CrewAI/LangGraph/LangChain/AutoGen imports; it is a **custom multi-agent orchestration framework** built directly in TypeScript (`src/council.ts`, `src/session-manager.ts`, `src/index.ts`). Agent “intelligence” is delegated to external coding CLIs, while this codebase handles orchestration, prompts, runtime control, and integrations.

Architecture-wise, `SessionManager` is the runtime hub: it creates per-engine session wrappers (`PersistentClaudeSession`, `PersistentCodexSession`, `PersistentGeminiSession`, `PersistentCursorSession`, `PersistentCustomSession`) and exposes orchestration primitives (`startSession`, `sendMessage`, `teamSend`, `councilStart`, `ultraplanStart`, `ultrareviewStart`) (`src/session-manager.ts:242-352`, `src/session-manager.ts:1144-1158`, `src/session-manager.ts:1166-1250`).

Multi-agent behavior is implemented in the `Council` engine: multiple personas are assigned isolated git worktrees, run in rounds, exchange indirect context via round history, and terminate only on unanimity consensus (`[CONSENSUS: YES]`) (`src/council.ts:125-240`, `src/council.ts:273-366`, `src/council.ts:563-671`). Higher-level workflows (`ultrareview`) programmatically instantiate many reviewer personas and run them through the same council runtime (`src/session-manager.ts:1373-1563`).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker orchestration with round-based parallel workers** (plus event-driven lifecycle emissions). `SessionManager`/`Council` acts as manager; each persona is a worker agent run in isolated environment.

Control flow is explicit: build prompts per round, execute all agents in parallel, collect votes, continue or stop on unanimous consensus.

From `src/council.ts:615-630`:
```ts
const agentTasks = this.config.agents.map((agent) => {
  const workDir = worktreeMap.get(agent.name) || this.config.projectDir;
  let prompt = buildAgentPrompt(agent, trimmedTask, round, session.responses, this.config.agents);
  const systemPrompt = buildSystemPrompt(agent, this.config.agents, workDir);
  return { agent, prompt, systemPrompt, workDir };
});
const results = await Promise.allSettled(
  agentTasks.map(({ agent, prompt, systemPrompt, workDir }) =>
    this.runSingleAgent(agent, prompt, systemPrompt, workDir, round, session.id),
  ),
);
```

From `src/council.ts:656-663`:
```ts
const allYes = roundVotes.length === this.config.agents.length && roundVotes.every((v) => v);
if (allYes) {
  session.status = 'awaiting_user';
  break;
}
```

## 4. Tools & External Integrations

- **Coding CLIs (primary agent backends):** Claude, Codex, Gemini, Cursor Agent, plus custom binaries (`src/session-manager.ts:1144-1158`; wrappers in `src/persistent-session.ts`, `src/persistent-codex-session.ts`, `src/persistent-gemini-session.ts`, `src/persistent-cursor-session.ts`, `src/persistent-custom-session.ts`).
- **Git / worktree automation:** creates per-agent branches/worktrees, merges/cleanup, review artifacts (`src/council.ts:125-240`, `src/council.ts:889-1013`).
- **OpenClaw Plugin SDK tools:** registers a large tool surface for session/team/council/ultra workflows (`src/index.ts:128-853`).
- **HTTP server + OpenAI-compatible API:** embedded server routes and `/v1/chat/completions` bridge to managed sessions (`src/embedded-server.ts:28-423`, `src/openai-compat.ts:502-678`).
- **Model gateway/proxy:** Anthropic-format proxy translating to OpenAI/Gemini/gateway backends with streaming support (`src/proxy/handler.ts:149-224`, `src/proxy/handler.ts:279-445`).
- **Cross-session messaging (“inbox”):** direct or queued inter-agent/session message passing (`src/inbox-manager.ts:38-96`, `src/session-manager.ts:1261-1278`).
- **Filesystem + local persistence:** stores session metadata/PIDs and logs under `~/.openclaw` (`src/session-manager.ts:36-76`, `src/session-manager.ts:1019-1104`, `src/council.ts:738-762`).
- **External web APIs:** Anthropic/OpenAI/Gemini HTTP APIs and optional OpenClaw gateway forwarding (`src/proxy/handler.ts:171-213`, `src/proxy/handler.ts:281-354`).

## 5. Notable Code Walkthrough

- `src/index.ts:128-853` — Plugin entrypoint that exposes the operational API: session lifecycle, team messaging, council orchestration, ultraplan, and ultrareview. This is the external control surface users and upstream agents call.
- `src/session-manager.ts:242-424` — Core session orchestration, including safe startup, engine selection, concurrency serialization per session, and message streaming hooks; this is the execution backbone.
- `src/council.ts:563-693` — Main multi-agent runtime loop: round construction, parallel agent execution, consensus gating, retries/follow-ups, and transcript generation.
- `src/persistent-session.ts:117-367` — Long-lived Claude CLI process wrapper with stream-json protocol parsing and event hooks; demonstrates where token/tool telemetry and turn completion semantics are derived.
- `src/openai-compat.ts:502-670` — OpenAI API bridge that maps chat-completion requests into persistent managed sessions, including session-keying logic and tool-call parsing contract.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. The repo automates end-to-end coding workflows: spawn agents, route tasks, coordinate multiple specialists, enforce round protocols, summarize/review outputs, and expose all of it as programmable tools and HTTP APIs (`src/index.ts`, `src/council.ts`, `src/session-manager.ts`). It also has strong overlap with “Code Generation” and “Browser/Terminal Use” (via coding CLIs), but the dominant design goal is orchestrating repeatable autonomous workflows rather than a single coding assistant UX.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Engine-agnostic agent runtime (Claude/Codex/Gemini/Cursor/custom) behind one orchestration interface.
  - Concrete multi-agent coordination with isolation (git worktrees), not just prompt role-play.
  - Consensus-driven completion protocol and explicit round structure (`[CONSENSUS: YES/NO]` parsing).
  - Production-style operational features: TTL cleanup, persistence, circuit breaker, rate limits, status reporting.
  - Rich integration layer (plugin tools + embedded HTTP + OpenAI-compat + model proxy).

- **Limitations:**
  - Coordination is prompt/protocol-driven; no formal planner graph/state machine with typed transitions.
  - Consensus quality depends on model honesty/format compliance; no deep verifier beyond vote parsing and heuristics.
  - Heavy reliance on shelling out to external CLIs and git; behavior can vary by environment/tool version.
  - Some safety tradeoffs in autonomous mode (explicit bypass-permissions defaults for council contexts).
  - Limited built-in evaluation harness for agent outcome quality beyond tests of components.

- **Research relevance:**
  - Evidence of practical **multi-agent software engineering orchestration** with real tool execution boundaries.
  - Example of **hybrid architecture**: LLM intelligence outsourced to vendor CLIs, orchestration implemented as deterministic middleware.
  - Useful case for studying **consensus-based stopping criteria** and round-based collaboration in applied MAS.
  - Demonstrates how **agent interoperability** can be achieved across heterogeneous model providers via adapter/proxy layers.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
