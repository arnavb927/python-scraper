---
repo_name: IQAIcom/adk-ts
url: "https://github.com/IQAIcom/adk-ts"
stars: 117
forks: 19
contributors_count: 18
last_commit_date: "2026-04-16T14:12:59+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T18:00:01.597785+00:00"
model: auto
duration_s: 117.1
clone_size_kb: 21615
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`IQAIcom/adk-ts` is a TypeScript agent framework for building and running LLM-powered agents with tools, memory, sessions, and orchestration patterns (single-agent, sequential, parallel, loop, and graph-style). A user typically instantiates agents via `AgentBuilder`, attaches tools/sub-agents, and executes through a `Runner` (or `ask()` convenience), which streams/stores events in session state (`packages/adk/src/agents/agent-builder.ts:759-840`, `packages/adk/src/runners.ts:220-335`). The framework includes built-in tool modules (web, file, shell, MCP) and pluggable memory/session backends for production use. In practice, this gives developers an SDK to automate multi-step workflows where LLMs can call tools, transfer between specialized agents, and persist state across runs.

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework** (not LangChain/CrewAI/AutoGen/LlamaIndex runtime). The core agent classes (`LlmAgent`, `SequentialAgent`, `ParallelAgent`, `LoopAgent`, `LangGraphAgent`) are implemented internally and selected by `AgentBuilder` (`packages/adk/src/agents/agent-builder.ts:141-147`, `:846-959`). I did not find imports of external orchestration frameworks; even “LangGraphAgent” is an in-house implementation (`packages/adk/src/agents/lang-graph-agent.ts:64-125`).

Architecture is centered on:  
1) agent definitions (`packages/adk/src/agents/*`),  
2) flow logic for LLM/tool/transfer behavior (`packages/adk/src/flows/llm-flows/auto-flow.ts:1-30`, `packages/adk/src/agents/llm-agent.ts:603-700`), and  
3) runtime execution + persistence (`packages/adk/src/runners.ts:220-335`, session services under `packages/adk/src/sessions/`).  
The “intelligence” lives in model prompts/instructions (`LlmAgent.instruction`), model/tool callbacks, and flow processors that allow agent transfer as a tool-mediated control decision (`packages/adk/src/tools/common/transfer-to-agent-tool.ts:8-55`).

## 3. Orchestration Pattern

Closest match: **other (hybrid orchestration)** with strong **sequential**, **parallel**, and **graph/state-machine** options, plus LLM-driven transfer routing.

- **Sequential:** executes sub-agents in order (`packages/adk/src/agents/sequential-agent.ts:44-51`).
- **Parallel:** launches sub-agents concurrently and merges yielded events (`packages/adk/src/agents/parallel-agent.ts:154-163`).
- **Graph:** node queue with conditional edges (`packages/adk/src/agents/lang-graph-agent.ts:227-264`).
- **LLM transfer routing:** `AutoFlow` injects transfer processing, and transfer tool sets `actions.transferToAgent` (`packages/adk/src/flows/llm-flows/auto-flow.ts:25-27`, `packages/adk/src/tools/common/transfer-to-agent-tool.ts:47-55`).

Control-flow excerpts:

Source: `packages/adk/src/agents/sequential-agent.ts:47-50`
```ts
for (const subAgent of this.subAgents) {
	for await (const event of subAgent.runAsync(ctx)) {
		yield event;
	}
}
```

Source: `packages/adk/src/agents/parallel-agent.ts:157-163`
```ts
const agentRuns = this.subAgents.map((subAgent) =>
	subAgent.runAsync(createBranchContextForSubAgent(this, subAgent, ctx)),
);

for await (const event of mergeAgentRun(agentRuns)) {
	yield event;
}
```

## 4. Tools & External Integrations

- **MCP servers/tooling:** full MCP toolset client, conversion to ADK tools, and many wrappers (CoinGecko, Playwright MCP, Notion MCP, filesystem MCP, various IQAI MCPs) in `packages/adk/src/tools/mcp/index.ts:33-193` and `packages/adk/src/tools/mcp/servers.ts:148-590`.
- **Web search APIs:** Tavily-based `web_search` (`packages/adk/src/tools/defaults/web-search-tool.ts:15-178`) and Google Custom Search (`packages/adk/src/tools/common/google-search-tool.ts:99-147`).
- **Generic HTTP API calls:** `http_request` tool using `fetch` with URL validation (`packages/adk/src/tools/common/http-request-tool.ts:15-142`).
- **Filesystem operations:** read/write/list/delete/mkdir with path-safety checks (`packages/adk/src/tools/common/file-operations-tool.ts:15-199`).
- **Shell/terminal execution:** configurable `BashTool` with whitelist/sandboxed/unrestricted modes and dangerous-pattern blocking (`packages/adk/src/tools/defaults/bash-tool.ts:25-357`).
- **Vector stores / memory:** pluggable vector abstraction and Qdrant adapter (`packages/adk/src/memory/storage/vector-storage-provider.ts:10-471`, `packages/adk/src/memory/storage/qdrant-vector-store.ts:119-449`).
- **Session persistence DB:** Kysely-backed database session/event storage (`packages/adk/src/sessions/database-session-service.ts:76-173`, `:523-649`).
- **LLM providers:** built-in registry for Google, Anthropic, OpenAI (`packages/adk/src/models/registry.ts:9-17`).

## 5. Notable Code Walkthrough

- `packages/adk/src/agents/agent-builder.ts:759-1077` — central fluent API that builds agent topologies and exposes a simplified `ask()` runner wrapper; this is the main developer entry point.
- `packages/adk/src/agents/llm-agent.ts:603-700` — core LLM agent execution path; chooses flow (`SingleFlow` vs `AutoFlow`) and streams events, including tool/transfer behavior.
- `packages/adk/src/runners.ts:220-335` — runtime orchestrator that loads session state, appends user messages, executes agents with plugin callbacks, and persists emitted events.
- `packages/adk/src/agents/lang-graph-agent.ts:187-304` — directed-graph orchestration engine with conditional node transitions and bounded step execution.
- `packages/adk/src/tools/mcp/index.ts:132-181` — MCP integration layer that fetches remote/local MCP tool schemas and converts them into executable framework tools.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. The framework is explicitly designed to coordinate multi-step tasks across specialized agents, tools, and persistent state (e.g., sub-agent delegation, graph node routing, resumable workflows, and session-backed execution) (`packages/adk/src/agents/parallel-agent.ts:154-163`, `packages/adk/src/workflows/workflow.ts:80-193`). Example code demonstrates practical multi-agent task flows such as a restaurant order system with specialized sub-agents and state handoffs (`apps/examples/src/03-multi-agent-systems/agents/agent.ts:16-20`). This is broader than a single chatbot and clearly workflow-oriented orchestration infrastructure.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Multiple orchestration primitives in one SDK (sequential/parallel/loop/graph + transfer) (`packages/adk/src/agents/agent-builder.ts:533-635`).
  - Strong integration surface: MCP, web APIs, shell, filesystem, memory, sessions (`packages/adk/src/tools/**/*`, `packages/adk/src/memory/**/*`).
  - Event/session persistence and rewind support for reproducible agent runs (`packages/adk/src/runners.ts:602-766`).
  - Provider-agnostic LLM architecture with registry + AI SDK adapter (`packages/adk/src/agents/llm-agent.ts:434-460`, `packages/adk/src/models/registry.ts:9-17`).
  - Practical examples for multi-agent and suspend/resume workflow execution (`apps/examples/src/03-multi-agent-systems/*`, `apps/examples/src/10-workflow-suspend-resume/agents/workflows.ts`).

- **Limitations:**
  - “LangGraph” is custom and relatively lightweight (e.g., no full cycle-detection; TODO noted) (`packages/adk/src/agents/lang-graph-agent.ts:144-145`).
  - Parallel live-mode not implemented (`packages/adk/src/agents/parallel-agent.ts:170-174`).
  - Security for powerful tools depends on configuration; unsafe modes exist (`packages/adk/src/tools/defaults/bash-tool.ts:130-136`).
  - Framework breadth may increase operational complexity (many optional services and plugin hooks to configure consistently).
  - Some persistence code paths appear complex and error-prone to reason about at scale (large state/event merge logic in `database-session-service.ts`).

- **Research relevance:**
  - Good evidence of **production-oriented multi-agent orchestration patterns** beyond toy planner-worker setups.
  - Useful case for studying **tool-mediated agent transfer** and event-sourced agent execution.
  - Supports analysis of **stateful agent systems** with memory/session persistence and rewind.
  - Relevant for empirical comparisons of **orchestration topologies** (sequential vs parallel vs graph) within one codebase.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
