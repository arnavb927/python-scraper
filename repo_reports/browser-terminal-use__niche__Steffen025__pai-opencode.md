---
repo_name: Steffen025/pai-opencode
url: "https://github.com/Steffen025/pai-opencode"
stars: 148
forks: 21
contributors_count: 11
last_commit_date: "2026-04-14T09:09:04+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:53:24.839213+00:00"
model: auto
duration_s: 106.3
clone_size_kb: 96448
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`Steffen025/pai-opencode` is a configuration-and-runtime scaffold that ports Daniel Miessler’s PAI system onto OpenCode, rather than a standalone agent framework binary. A user primarily runs OpenCode with this repo’s `.opencode` assets (skills, plugin hooks, agent model routing) plus helper scripts like `switch-provider.ts` and browser tools. In practice, this gives them a personalized AI environment with prewired multi-agent delegation patterns, research workflows, memory/observability hooks, and safety checks. The repo’s value is in orchestration policy and tooling glue: it tells the host assistant *how* to spawn and coordinate agents for different tasks and providers.

## 2. Agent Framework & Architecture

This repo does **not** implement CrewAI/LangGraph/AutoGen runtimes directly. The concrete framework is **OpenCode’s native plugin + skill + Task-subagent system**, with custom TypeScript glue around it (`.opencode/plugins/pai-unified.ts:338-360`, `.opencode/plugins/pai-unified.ts:545-580`, `.opencode/skills/Research/Workflows/StandardResearch.md:30-52`).

Architecture is split across:
- **Agent registry/config layer**: `opencode.json` defines named runtime agents and model assignments (`opencode.json:23-72`), while `.opencode/tools/switch-provider.ts` rewrites agent model routing across providers (`.opencode/tools/switch-provider.ts:197-331`).
- **Orchestration prompt layer**: skill workflow Markdown files encode “when and how” to launch subagents via `Task(...)`, including parallel fan-out and synthesis patterns (`.opencode/skills/Research/Workflows/QuickResearch.md:22-40`, `.opencode/skills/Agents/Workflows/SpawnParallelAgents.md:53-81`).
- **Execution governance layer**: a single OpenCode plugin intercepts lifecycle/tool events for security gates, capture, observability, and session state (`.opencode/plugins/pai-unified.ts:348-536`, `.opencode/plugins/pai-unified.ts:780-1241`).

The “intelligence” is mostly prompt-policy and routing logic (skills + agent profiles), while the plugin enforces guardrails and records outputs.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with parallel fan-out**, plus event-driven hooks.

The parent assistant acts as manager and dispatches specialized workers via `Task(subagent_type=...)` in one message for concurrency:

```34:50:.opencode/skills/Research/Workflows/StandardResearch.md
Task({
  subagent_type: "DeepResearcher",
  description: "[topic] academic depth",
  prompt: "Do ONE search for: [query optimized for depth/analysis]. Return findings immediately."
})
...
Task({
  subagent_type: "PerplexityResearcher",
  description: "[topic] real-time",
  prompt: "Do ONE search for: [query optimized for current events/news]. Return findings immediately."
})
```

And the plugin tracks/handles post-worker completion and persistence:

```559:580:.opencode/plugins/pai-unified.ts
if (isTaskTool(input.tool)) {
  fileLog("Subagent task completed, capturing output...", "info");
  const agentType = args.subagent_type || "unknown";
  emitAgentComplete({ agent_type: agentType, result_length: resultLength }).catch(() => {});
  const captureResult = await captureAgentOutput(args, result);
  await captureSubagentSession(input.sessionID, input.args, output);
}
```

So control is manager-led delegation, not peer swarm autonomy or graph-state machine transitions.

## 4. Tools & External Integrations

- **OpenCode plugin hooks + custom tools**: registers custom tools (`session_registry`, `session_results`, `code_review`) and intercepts tool/session/message events in one plugin (`.opencode/plugins/pai-unified.ts:355-359`, `.opencode/plugins/pai-unified.ts:780-1241`).
- **Browser automation (Playwright, code-first)**: replaces MCP-heavy browser usage with local TypeScript wrapper and persistent Bun server (`.opencode/skills/Utilities/Browser/index.ts:15-113`, `.opencode/skills/Utilities/Browser/Tools/BrowserSession.ts:142-209`).
- **Shell/terminal environment injection**: plugin injects per-session env into shell calls (`.opencode/plugins/pai-unified.ts:1266-1301`).
- **Web retrieval/search in workflows**: research workflows require URL validation via `curl` + `WebFetch`, and fallback with `WebSearch` (`.opencode/skills/Research/Workflows/StandardResearch.md:66-84`, `.opencode/skills/Research/Workflows/ExtensiveResearch.md:141-159`).
- **Voice notification service**: local HTTP integration for TTS notifications (`http://localhost:8888/notify`) appears in workflows/tools (`.opencode/skills/Agents/SKILL.md:35-41`, `.opencode/skills/Utilities/Browser/Tools/Browse.ts:22-99`).
- **Multi-provider model routing**: provider profile switcher rewrites agent model maps and handles researcher-native providers (`.opencode/tools/switch-provider.ts:134-201`, `.opencode/tools/switch-provider.ts:275-331`).

No concrete vector DB/RAG index implementation is wired in core TypeScript; “RAG-like” behavior is mostly via workflow prompts and external search agents.

## 5. Notable Code Walkthrough

- `.opencode/plugins/pai-unified.ts:338-1308` - central runtime integration; defines hook map, security checks, task/subagent capture, event-driven lifecycle handling, and shell env propagation.
- `opencode.json:23-72` - canonical per-agent model assignments; this is the runtime agent roster used for routing.
- `.opencode/tools/switch-provider.ts:197-331` - operational model router that updates `opencode.json` across provider profiles while preserving custom agent blocks.
- `.opencode/skills/Research/Workflows/StandardResearch.md:30-98` - representative manager-worker template: parallel launch of specialist research subagents, synthesis, and mandatory source verification.
- `.opencode/skills/Utilities/Browser/index.ts:82-905` and `.opencode/skills/Utilities/Browser/Tools/BrowserSession.ts:142-429` - concrete browser/terminal-use implementation via Playwright + Bun HTTP control plane.

## 6. Use-Case Mapping

This repo supports **Browser / Terminal Use** through concrete browser tooling (Playwright wrapper and persistent browser session API) and strong shell/tool orchestration hooks (`.opencode/skills/Utilities/Browser/index.ts:82-113`, `.opencode/plugins/pai-unified.ts:1266-1301`). However, the dominant behavior in-core is broader **workflow-level orchestration**: dispatching specialized agents, coordinating research tiers, applying safety gates, and synthesizing outputs (`.opencode/skills/Research/Workflows/QuickResearch.md:22-40`, `.opencode/skills/Agents/Workflows/SpawnParallelAgents.md:53-81`).  
Given that emphasis, the assigned category is plausible but **best fit is Workflow Automation** (with Browser/Terminal as an important capability subset).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear practical MAS patterns (parallel subagent fan-out + synthesis) encoded in reusable workflows.
  - Strong runtime governance via plugin hooks (security, observability, lifecycle tracking).
  - Flexible multi-provider agent routing with explicit per-agent model mapping.
  - Real browser/terminal tooling integration, not just abstract agent prompts.
  - Rich modular skill taxonomy enabling specialization without hardcoding a single planner.

- **Limitations:**
  - Much orchestration logic lives in Markdown policy files; enforcement depends on assistant compliance.
  - Relies heavily on OpenCode runtime primitives, so portability outside OpenCode is limited.
  - No explicit formal state graph/planner engine (e.g., typed graph transitions) in code.
  - Some workflow docs reference tools/systems that may vary by environment (e.g., TeamCreate semantics).
  - Research quality control is procedural (instructions), not deeply programmatic validation.

- **Research relevance:**
  - Evidence of **prompt-governed multi-agent coordination** in production-style assistant scaffolding.
  - Useful case for studying **hierarchical manager-worker orchestration with parallel subagents**.
  - Illustrates **event-hook augmentation** of agent runtimes (security/memory/observability overlays).
  - Demonstrates **provider-aware role routing** as a cost/quality optimization strategy.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
