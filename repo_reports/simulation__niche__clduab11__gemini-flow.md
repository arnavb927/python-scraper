---
repo_name: clduab11/gemini-flow
url: "https://github.com/clduab11/gemini-flow"
stars: 380
forks: 71
contributors_count: 4
last_commit_date: "2026-01-29T16:47:49+00:00"
primary_use_case: Simulation
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Simulation]
generated_at: "2026-04-27T17:24:29.029008+00:00"
model: auto
duration_s: 85.7
clone_size_kb: 54783
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`gemini-flow` is a TypeScript CLI platform that tries to provide an “AI development team” abstraction on top of Gemini models, with commands for hive/swarm/agent/task operations. A user primarily runs CLI commands (`gemini-flow ...` via `src/cli/full-index.ts` or `gemini ...` simple mode via `src/cli/gemini-cli.ts`) and gets either direct LLM generations or orchestrated multi-step workflows. The most concrete runtime multi-agent path is a small planner→coder→tester pipeline in `HiveMindManager`, where each role is an LLM-backed agent created from shared definitions and prompts. The repo also contains a much larger set of orchestration modules (A2A, MCP, swarm, GitHub bridge), but many of those are partially implemented or simulation-style scaffolding rather than fully wired production execution.

## 2. Agent Framework & Architecture

This repo uses a **custom framework** (no evidence of LangGraph/CrewAI/AutoGen imports in runtime core). Agent objects are defined in-house (`src/agents/agent.ts`) and instantiated from a large static registry (`src/agents/agent-definitions.ts`) via `AgentFactory` (`src/agents/agent-factory.ts`). LLM calls are abstracted through custom adapters (`BaseModelAdapter` + `GeminiAdapter`) rather than external orchestration frameworks (`src/adapters/base-model-adapter.ts`, `src/adapters/gemini-adapter.ts`).

The concrete “intelligence” is split across:
- **Role prompts/config** in `AGENT_DEFINITIONS` (`systemPrompt`, capabilities, temperatures) (`src/agents/agent-definitions.ts:21-1255`).
- **Per-agent execution wrapper** that builds model requests with role system message (`src/agents/agent.ts:38-57`).
- **Model-selection intelligence** in `ModelRouter` rules/heuristics and `ModelOrchestrator` failover/caching (`src/core/model-router.ts:110-207`, `src/core/model-orchestrator.ts:237-343`).

Architecturally, there are two layers:  
1) a practical small multi-agent pipeline (`HiveMindManager`) that really executes three LLM roles sequentially, and  
2) broader platform modules for swarms/A2A/MCP/GitHub coordination that describe richer MAS behaviors but are often mock/simulated placeholders.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker with sequential stages** (plus some event-driven queueing in A2A modules).

The clearest runtime path is manager-driven staged execution in `HiveMindManager`:
- manager creates specialized agents (`planner`, `coder`, `tester`);
- manager invokes them in order and passes outputs downstream.

Example (sequential delegation):
- `src/core/hive-mind-manager.ts:37-53`
```ts
const planner = AgentFactory.createAgent("planner", adapter);
const coder = AgentFactory.createAgent("coder", adapter);
const tester = AgentFactory.createAgent("tester", adapter);

const plan = await planner.executeTask(`Create a plan for: ${objective}`);
const code = await coder.executeTask(`Implement the following plan: ${plan}`);
const testResult = await tester.executeTask(`Test the following implementation: ${code}`);
```

Each worker agent is an LLM role wrapper:
- `src/agents/agent.ts:44-53`
```ts
const request: ModelRequest = {
  prompt: task,
  context: { priority: 'medium', userTier: 'free', latencyTarget: 10000 },
  systemMessage: this.definition.systemPrompt,
};
const result = await this.adapter.generate(request);
```

There is also a queue-based/event-driven orchestration style in A2A (`messageQueue`, priority insertion, async handler dispatch), but this appears more as protocol infrastructure than the main end-user flow (`src/protocols/a2a/core/a2a-protocol-manager.ts:475-632`).

## 4. Tools & External Integrations

- **Google Gemini API**: Direct model calls via `@google/generative-ai` in both simple CLI and adapter paths (`src/cli/gemini-cli.ts:386-409`, `src/adapters/gemini-adapter.ts:247-262`).
- **Model routing/orchestration across Gemini variants**: custom router + orchestrator with tier/latency/cost heuristics (`src/core/model-router.ts`, `src/core/model-orchestrator.ts`).
- **MCP client integration**: stdio MCP connections using `@modelcontextprotocol/sdk` and `.mcp-config.json` server specs (`src/mcp/mcp-client-wrapper.ts:1-43`).
- **MCP web research adapter**: tool facade exists, but implementations are simulated/example data (not live providers) (`src/mcp/web-research-adapter.ts:176-205`, `210-300`).
- **Tool execution/discovery layer**: dynamic tool loading/invocation with retry+timeout (`src/core/tool-executor.ts:28-87`) and metadata registry with SQLite persistence (`src/core/tool-registry.ts:41-85`).
- **A2A protocol stack**: JSON-RPC style agent-to-agent manager with queueing, priorities, retry policies, security checks (`src/protocols/a2a/core/a2a-protocol-manager.ts:64-224`, `475-756`).
- **GitHub/A2A bridge**: integration layer for PR/issue/release workflows via agent coordination plans; many operations are scaffold-level (`src/core/github-a2a-bridge.ts:74-125`, `324-387`).

## 5. Notable Code Walkthrough

- `src/core/hive-mind-manager.ts:22-60` — Most concrete MAS workflow: initializes adapter, creates role agents, and runs planner→coder→tester orchestration.
- `src/agents/agent.ts:13-69` — Core runtime agent abstraction; applies role prompt/context and executes one LLM task via adapter.
- `src/agents/agent-definitions.ts:21-1255` — Large catalog of specialized agent identities/capabilities/prompts; this is where role specialization is encoded.
- `src/adapters/gemini-adapter.ts:55-136` — Real Gemini API request/response path including model setup, usage extraction, safety settings, and error mapping.
- `src/core/model-router.ts:110-342` — Central “routing intelligence” for selecting models based on rules, cached decisions, complexity scoring, and fallbacks.

## 6. Use-Case Mapping

The assigned label **Simulation** is partly understandable because many CLI surfaces simulate swarm behavior and metrics (e.g., timed delays, placeholder statuses in swarm/hive commands). However, the repo’s strongest implemented behavior is **Workflow Automation**: it orchestrates role-based LLM steps (planner/coder/tester), provides task-oriented CLI operations, and includes integration scaffolding for GitHub, MCP tools, and A2A coordination of development workflows. So Simulation is not the best primary fit; **Workflow Automation** is more accurate for what users can practically execute.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear custom agent abstraction with reusable role definitions and prompts (`src/agents/*`).
  - Concrete multi-agent execution path exists (not just docs) via `HiveMindManager`.
  - Strong modular decomposition (agents, adapters, router, A2A, MCP, CLI command modules).
  - Sophisticated model-routing heuristics (latency/cost/tier/complexity) for LLM selection.
  - Broad integration intent (MCP, A2A, GitHub workflow coordination, tool execution stack).

- **Limitations:**
  - Large portions of swarm/hive/agent command UX are placeholder or simulated behavior rather than backed runtime state.
  - Several advanced modules contain “mock”/“TODO” implementations (e.g., Vertex execution, many coordination internals).
  - Inconsistency between marketed scale (many agent types) and concretely wired execution paths.
  - Some example paths reference external tooling abstractions without showing full end-to-end production wiring.
  - Operational guarantees (fault tolerance, Byzantine resilience) are mostly architectural intent, not fully demonstrated runtime proofs.

- **Research relevance:**
  - Useful as a case of **hybrid practical + aspirational MAS architecture** in open-source agent engineering.
  - Shows how role-based agent definitions and LLM adapters can be combined into lightweight orchestration.
  - Demonstrates design patterns for integrating **model routing** and **protocol layers (A2A/MCP)** in one codebase.
  - Good evidence for studying the gap between “agentic platform claims” and implemented orchestration maturity.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
