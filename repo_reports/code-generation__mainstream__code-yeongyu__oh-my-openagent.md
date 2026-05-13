---
repo_name: code-yeongyu/oh-my-openagent
url: "https://github.com/code-yeongyu/oh-my-openagent"
stars: 53537
forks: 4321
contributors_count: 200
last_commit_date: "2026-04-22T03:56:20+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, Browser / Terminal Use]
generated_at: "2026-05-05T07:18:10.259786+00:00"
model: auto
duration_s: 171.6
clone_size_kb: 44903
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
I’ve now traced the runtime path from plugin init → agent registration → `task`/`call_omo_agent` delegation → background manager execution and notifications, plus MCP/tool integrations. I’m compiling the final Markdown report in your exact 8-section structure next.## 1. Overview

`oh-my-openagent` is a Bun/TypeScript plugin that extends OpenCode/Claude Code into a multi-agent orchestration layer rather than a single assistant. In practice, users run OpenCode/Claude Code with this plugin enabled and get a router-style primary agent (notably Sisyphus) plus a set of specialist subagents (explore, librarian, oracle, metis, atlas, etc.), category-based delegation, and background task execution. The plugin dynamically builds agent configs, tools, hooks, and MCP servers at startup, then injects them into the host runtime (`src/index.ts:22-117`, `src/plugin-handlers/agent-config-handler.ts:51-406`). The result is an “agent harness” for delegating coding/research/planning work across multiple coordinated sessions with retries, notifications, and model fallback (`src/features/background-agent/manager.ts:374-537`).

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph, CrewAI, AutoGen, or LangChain as its runtime framework. The concrete framework usage is custom orchestration on top of OpenCode SDK/plugin APIs (`@opencode-ai/plugin`, `@opencode-ai/sdk`) as seen in imports and tool definitions (`src/index.ts:2`, `src/agents/builtin-agents.ts:1`, `src/tools/delegate-task/tools.ts:1`).

Architecture is plugin-centric: startup loads config, creates managers (background tasks, tmux sessions, skill MCP manager), registers tools, and composes hooks into the OpenCode plugin interface (`src/index.ts:64-97`, `src/create-managers.ts:46-132`, `src/plugin-interface.ts:33-82`). Agent definitions are assembled in `createBuiltinAgents`, mixing built-in personas with user/project/plugin agent sources and model-resolution logic (`src/agents/builtin-agents.ts:61-182`, `src/plugin-handlers/agent-config-handler.ts:161-333`).

The “intelligence” is primarily prompt/policy engineering plus runtime routing logic: Sisyphus prompt builders encode delegation rules and orchestration behavior (`src/agents/sisyphus/default.ts:138-540`), while tools like `task` and `call_omo_agent` decide when/how to spawn subagents, choose model/fallback chain, and run sync vs background sessions (`src/tools/delegate-task/tools.ts:34-162`, `src/tools/call-omo-agent/tools.ts:97-205`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with event-driven background execution**.

- A parent agent invokes `task`/`call_omo_agent`, which validates target subagent, resolves model/fallback config, and dispatches a child session (`src/tools/call-omo-agent/tools.ts:137-204`, `src/tools/delegate-task/tools.ts:97-162`).
- `BackgroundManager` queues and runs child sessions, tracks state, retries with fallback models, and injects completion notifications back to the parent session (`src/features/background-agent/manager.ts:374-460`, `src/features/background-agent/manager.ts:1993-2136`).

Example control flow excerpt:

```118:132:src/tools/delegate-task/background-task.ts
const task = await manager.launch({
  description: args.description,
  prompt: effectivePrompt,
  agent: normalizedAgent,
  parentSessionId: parentContext.sessionID,
  ...
  model: categoryModel,
  fallbackChain,
})
```

```533:567:src/features/background-agent/manager.ts
private async startTask(item: QueueItem): Promise<void> {
  const { task, input } = item
  ...
  const createResult = await this.client.session.create({
    body: { parentID: input.parentSessionId, title: `${input.description} (@${input.agent} subagent)` },
    query: { directory: parentDirectory },
  })
```

## 4. Tools & External Integrations

- **OpenCode session/tool APIs**: Core execution backend for agent spawn, prompting, polling (`src/features/background-agent/manager.ts:545-565`, `src/features/background-agent/manager.ts:2125-2135`).
- **Delegation tools (`task`, `call_omo_agent`)**: Primary agent-to-agent invocation surface (`src/plugin/tool-registry.ts:271-276`, `src/tools/delegate-task/tools.ts:34-164`, `src/tools/call-omo-agent/tools.ts:97-205`).
- **MCP (three-tier merge)**:
  - Built-in remote MCP servers: `websearch`, `context7`, `grep_app` (`src/mcp/index.ts:16-35`).
  - Claude `.mcp.json` loader + user MCP merge (`src/plugin-handlers/mcp-config-handler.ts:37-54`).
  - Skill-embedded MCP via `skill_mcp` tool (`src/tools/skill-mcp/tools.ts:98-182`).
- **Browser automation providers** for skills (`playwright`, `agent-browser`, `dev-browser`, `playwright-cli`) (`src/config/schema/browser-automation.ts:3-19`).
- **Terminal/tmux integration** for subagent sessions and interactive bash tooling (`src/create-managers.ts:60-92`, `src/tools/interactive-bash/index.ts:1-4`).
- **OpenClaw notifications/integration hooks** for runtime events (`src/create-managers.ts:93-103`, `src/plugin/tool-registry.ts:213-223`).

## 5. Notable Code Walkthrough

- `src/index.ts:22-117` - Main plugin entrypoint: bootstraps config, managers, tools, hooks, and returns hook handlers. This is the top-level runtime composition point.
- `src/plugin-handlers/agent-config-handler.ts:161-333` - Builds final runtime agent map from built-ins + discovered/user/project/plugin agents, including default-agent behavior and protected override rules.
- `src/tools/delegate-task/tools.ts:34-162` - Core delegation tool logic: validates args, resolves category/subagent routing, builds system content with skills, then executes sync/background task flows.
- `src/features/background-agent/manager.ts:374-537` - Task queueing and spawn lifecycle (`pending -> running`) with spawn-depth enforcement and concurrency controls.
- `src/features/background-agent/manager.ts:1561-1605` - Model fallback retry loop for background tasks, showing robust fault-tolerance mechanics beyond simple one-shot delegation.

## 6. Use-Case Mapping

Although it supports coding agents, this repository is best categorized as **Workflow Automation** rather than pure Code Generation. The core value is orchestrating many specialized LLM agents, tools, retries, and session workflows (sync/background, notification, continuation, policy hooks), not just generating code text (`src/tools/delegate-task/tools.ts:34-162`, `src/features/background-agent/manager.ts:1993-2136`). It does enable code-generation tasks through specialists like Hephaestus/Sisyphus and file-edit/search tools, but architecturally it is an agent workflow harness first (`src/agents/builtin-agents.ts:61-182`, `src/plugin/tool-registry.ts:264-279`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Strong multi-agent orchestration primitives (delegation, parent-child sessions, continuation IDs).
- Production-like runtime controls: spawn depth limits, concurrency manager, circuit breakers, fallback retries.
- Rich extensibility via merged agent sources, dynamic prompts, and three-tier MCP integration.
- Clear separation of concerns (plugin handlers, tools, background manager, agent factories).
- Practical event-driven completion notifications back into parent sessions.

- **Limitations:**
- Very prompt-policy heavy; behavior quality depends heavily on long system prompts rather than explicit planning graphs.
- Large code surface with high complexity may increase maintenance burden and debugging cost.
- Tight coupling to OpenCode/Claude Code plugin/session APIs limits portability to other agent runtimes.
- Few explicit formal guarantees for global task correctness across many concurrent subagents.
- Risk of config complexity and emergent interactions (multiple agent and MCP source merges).

- **Research relevance:**
- Good real-world example of hierarchical multi-agent orchestration in developer tooling.
- Useful case study for fallback/retry, concurrency, and lifecycle management in agentic systems.
- Illustrates practical integration of MCP tool ecosystems into delegated agent workflows.
- Demonstrates event-driven coordination patterns between parent and child LLM sessions.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
