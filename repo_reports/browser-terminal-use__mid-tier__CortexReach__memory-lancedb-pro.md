---
repo_name: CortexReach/memory-lancedb-pro
url: "https://github.com/CortexReach/memory-lancedb-pro"
stars: 4254
forks: 701
contributors_count: 66
last_commit_date: "2026-04-21T12:53:17+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T12:21:21.179263+00:00"
model: auto
duration_s: 107.2
clone_size_kb: 2864
uses_mas: no
final_use_case: RAG + Agents
---
## 1. Overview

`memory-lancedb-pro` is an OpenClaw memory plugin that gives agents long-term memory backed by LanceDB, with hybrid retrieval (vector + BM25), reranking, and scoped isolation. In practice, users run OpenClaw with this plugin enabled and/or use the `openclaw memory-pro ...` CLI commands to inspect, migrate, compact, and manage memory entries (`index.ts:2290-2331`, `cli.ts:1-43`). At runtime, it hooks into agent lifecycle events to auto-recall relevant memories before prompt construction and auto-capture/store new memories after interaction (`index.ts:2337-2453`, `index.ts:2739-2807`). It also includes a reflection pipeline that summarizes prior sessions into “invariants/derived” guidance and injects those back into future prompts (`index.ts:3195-3342`). The core problem it solves is persistent, governable memory quality for OpenClaw agents across sessions and scopes.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph, LangChain, AutoGen, CrewAI, or LlamaIndex. The concrete framework is the **OpenClaw plugin SDK** (`import type { OpenClawPluginApi } from "openclaw/plugin-sdk"`) with custom TypeScript orchestration (`index.ts:6`, `index.ts:1896-1927`).

Architecture is plugin-centric, not a standalone agent runtime. The plugin initializes storage/retrieval components (LanceDB store, embedder, retriever, scope manager), registers memory tools, registers lifecycle hooks, and optionally initializes an LLM-backed smart extractor (`index.ts:1724-1839`, `src/tools.ts:2226-2257`). “Intelligence” lives mostly in:
- retrieval/ranking logic (`src/retriever.ts`),
- extraction and dedup prompts (`src/smart-extractor.ts`, `src/extraction-prompts.ts`),
- reflection generation/injection logic (`index.ts:3195-3504`),
- tool policies and scope controls (`src/tools.ts`, `src/scopes.ts`).

It references multiple *agent IDs* and subagent session handling, but these are identities/scopes in the host OpenClaw system, not independently implemented cooperative LLM agents in this repo (`src/scopes.ts:64-106`, `index.ts:2360-2369`, `index.ts:3264-3267`).

## 3. Orchestration Pattern

Closest match: **event-driven pipeline** (plugin hooks), with sequential processing inside each hook.

Control flow is driven by OpenClaw events (`message_received`, `before_prompt_build`, `after_tool_call`, `session_end`, command hooks), not by agent-to-agent graph routing. Example:

`index.ts:2347-2363`
```ts
api.on("message_received", (event: any, ctx: any) => { ... });
api.on("before_prompt_build", async (event: any, ctx: any) => {
  const sessionKey = typeof ctx.sessionKey === "string" ? ctx.sessionKey : "";
  if (sessionKey.includes(":subagent:")) return;
  ...
});
```

Reflection is another event-driven loop guarded by dedup/locks/cooldown:

`index.ts:3374-3396`
```ts
const runMemoryReflection = async (event: any) => {
  const sessionKey = typeof event.sessionKey === "string" ? event.sessionKey : "";
  if (!sessionKey) return;
  if (_dedupHookEvent("reflection", event)) return;
  const globalLock = getGlobalReflectionLock();
  if (sessionKey && globalLock.get(sessionKey)) return;
  ...
};
```

So orchestration is not manager-worker or swarm MAS; it is hook-based automation around a single host-agent execution flow.

## 4. Tools & External Integrations

- **OpenClaw plugin host + hooks/tools/CLI**: integration point for lifecycle events and tool registration (`index.ts:1896-2331`, `src/tools.ts:2226-2257`).
- **LanceDB vector store**: persistent memory storage, search, stats, migration (`src/store.ts:5-6`, `src/store.ts:203-220`).
- **OpenAI-compatible embedding APIs**: embedding generation with provider profiles and key rotation (`src/embedder.ts:11-15`, `src/embedder.ts:105-136`).
- **OpenAI-compatible LLM chat completions**: used for JSON extraction/dedup/reflection via custom client (`src/llm-client.ts:6`, `src/llm-client.ts:177-205`).
- **External rerank APIs** (Jina/Voyage/Pinecone/TEI-compatible via HTTP `fetch`): cross-encoder rerank during retrieval (`src/retriever.ts:45-64`, `src/retriever.ts:1241-1264`).
- **Filesystem + lockfile**: memory files, session file recovery, md mirror, cross-process write locking (`src/store.ts:57-67`, `index.ts:3422-3440`).
- **No browser automation / terminal-control toolchain inside agent runtime**: no Playwright/Browserbase/shell-agent control logic found in core runtime code.

## 5. Notable Code Walkthrough

- `index.ts:1724-1887` - Initializes singleton plugin state (store, embedder, retriever, scope manager, smart extractor, caches); this is the runtime composition root.
- `index.ts:2337-2668` - Auto-recall hook pipeline: gating, query truncation, retrieval, adaptive intent boost, dedup/governance filtering, and prompt context injection.
- `index.ts:3195-3504` - Reflection subsystem: captures tool-error signals, injects invariant/derived reflection blocks, and runs guarded reflection generation on command/session transitions.
- `src/tools.ts:506-2257` - Defines and registers memory tools (`memory_recall`, `memory_store`, `memory_forget`, `memory_update`, plus management/self-improvement tools) with per-agent scope enforcement.
- `src/smart-extractor.ts:545-760` - LLM-based candidate extraction and dedup/persist pipeline; this is where model output becomes structured memory writes.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** appears inaccurate for this codebase. The repo does not implement browser-driving agents or terminal-action agents; instead it provides long-term memory infrastructure and retrieval/reflection services for OpenClaw agents through hooks/tools (`index.ts:2337-2453`, `src/tools.ts:506-677`). The best fit is **RAG + Agents**: it performs retrieval augmentation, scoped memory management, and LLM-assisted memory extraction/reflection that feed agent prompts. If constrained to the provided primary-use assignment, this would only be an indirect dependency of browser/terminal agents, not a direct implementation of that use case.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong event-hook integration with host runtime, including guardrails for dedup/re-entrancy/cooldowns (`index.ts:1657-1693`, `index.ts:3352-3396`).
  - Rich retrieval stack: hybrid fusion, rerank options, diagnostics/traceability (`src/retriever.ts:1-4`, `src/retriever.ts:119-173`).
  - Practical memory governance (state/layer filtering, suppression, scope ACL) before prompt injection (`index.ts:2499-2508`, `src/scopes.ts:29-38`).
  - Production-oriented reliability patterns: singleton state, write locks, retries, timeout wrappers (`index.ts:1699-1723`, `src/store.ts:212-220`, `index.ts:2404-2410`).

- **Limitations:**
  - No true multi-agent coordination implemented internally; agent IDs are scope labels in host context, not autonomous collaborating agents (`src/scopes.ts:64-66`, `index.ts:2360-2369`).
  - Heavy logic concentration in `index.ts` increases complexity and maintenance risk.
  - LLM extraction/reflection quality depends on external model behavior; JSON repair/fallbacks mitigate but do not eliminate brittleness (`src/llm-client.ts:82-159`).
  - Tight coupling to OpenClaw event semantics limits portability to other agent frameworks.

- **Research relevance:**
  - Good evidence for **agent memory middleware** design patterns (hook-based recall/capture/reflection loops).
  - Useful for studying **governed memory injection** and retrieval-quality controls in agent systems.
  - Illustrates operational concerns (lock contention, dedup, timeout isolation) in long-running agent infrastructures.
  - Not strong evidence for MAS coordination algorithms (no planner-worker/swarm runtime here).

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: RAG + Agents
