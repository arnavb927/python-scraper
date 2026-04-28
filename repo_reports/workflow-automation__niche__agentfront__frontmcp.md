---
repo_name: agentfront/frontmcp
url: "https://github.com/agentfront/frontmcp"
stars: 142
forks: 7
contributors_count: 5
last_commit_date: "2026-04-21T16:16:42+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 1
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T18:06:53.289045+00:00"
model: auto
duration_s: 142.7
clone_size_kb: 65488
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`agentfront/frontmcp` is a TypeScript framework for building MCP servers that expose tools, resources, prompts, jobs/workflows, and optional LLM-powered agents. In practice, users run `frontmcp` CLI commands (e.g., `create`, `dev`) or embed via SDK `connect*()` helpers, then get an MCP-compatible server/client surface that can be consumed by OpenAI/Claude/LangChain-style tool-calling systems (`libs/cli`, `libs/sdk/src/direct/connect.ts:106-281`). The core value is not a single packaged assistant, but infrastructure: decorators + registries + flows that automate transport, auth/session, plugin hooks, and execution lifecycle (`libs/sdk/src/transport/adapters/transport.local.adapter.ts:173-215`, `libs/sdk/src/agent/flows/call-agent.flow.ts:77-89`). It can host multiple agents and many non-agent automations (jobs/workflows), making it an orchestration framework rather than an end-user chatbot app.

## 2. Agent Framework & Architecture

This repo uses a **custom in-house agent framework** (no LangGraph/LangChain/AutoGen/CrewAI runtime core found). I found no concrete imports of those frameworks in execution paths; agent runtime is implemented in `libs/sdk/src/agent/*` and `libs/sdk/src/common/interfaces/agent.interface.ts`, while LangChain/OpenAI/Claude mentions are integration formats, not orchestration engines (`libs/sdk/src/direct/connect.ts:205-281`, `libs/sdk/src/direct/llm-platform.ts`).

Agents are defined via `@Agent` / `agent()` decorators and normalized into `AgentRecord` entries (`libs/sdk/src/common/decorators/agent.decorator.ts:41-118`, `libs/sdk/src/agent/agent.utils.ts:90-150`). Each `AgentInstance` initializes an LLM adapter (OpenAI/Anthropic/custom), optional private `AgentScope` with tools/plugins/resources/prompts/nested agents, and then optionally exposes the agent itself as a callable tool (`libs/sdk/src/agent/agent.instance.ts:138-150`, `165-195`, `346-374`).

The “intelligence loop” is in `AgentExecutionLoop`: iterative LLM completion -> detect tool calls -> execute tools -> append tool results -> repeat until final text or max iterations (`libs/sdk/src/agent/agent-execution-loop.ts:359-444`). `AgentContext.runAgentLoop()` wires this loop with notifications/progress and output parsing (`libs/sdk/src/common/interfaces/agent.interface.ts:197-297`).

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker tool-loop**, with optional multi-agent registry semantics.

- The manager is the LLM loop inside one `AgentContext`; workers are tool calls (and potentially agent-tools exposed into tool registries).
- Control is stage-driven via flow pipelines (`agents:call-agent` pre/execute/finalize) rather than peer-to-peer swarm messaging (`libs/sdk/src/agent/flows/call-agent.flow.ts:77-89`).

Example control flow (tool-calling loop):

```ts
// libs/sdk/src/agent/agent-execution-loop.ts:387-395
if (completion.finishReason === 'tool_calls' && completion.toolCalls?.length) {
  const assistantMessage: AgentMessage = {
    role: 'assistant',
    content: completion.content,
    toolCalls: completion.toolCalls,
  };
  messages.push(assistantMessage);
```

```ts
// libs/sdk/src/agent/agent-execution-loop.ts:413-425
result = await toolExecutor(toolCall.name, toolCall.arguments);
const toolMessage: AgentMessage = {
  role: 'tool',
  content: typeof result === 'string' ? result : JSON.stringify(result),
  toolCallId: toolCall.id,
  name: toolCall.name,
};
```

Agent invocation itself is orchestrated through an explicit flow:

```ts
// libs/sdk/src/agent/flows/call-agent.flow.ts:331-341
const context = agent.create(input.arguments, { ...ctx, progressToken });
...
this.state.set('agentContext', context);
```

## 4. Tools & External Integrations

- **MCP protocol/server transport**: core server wiring via `McpServer` and request handlers (`libs/sdk/src/transport/adapters/transport.local.adapter.ts:173-215`).
- **LLM providers**:
  - OpenAI SDK / OpenAI-compatible endpoints (`libs/sdk/src/agent/adapters/openai.adapter.ts:291-319`, `321-368`).
  - Anthropic SDK (`libs/sdk/src/agent/adapters/anthropic.adapter.ts:149-176`, `178-195`).
- **LLM platform formatting adapters** (client-side integration): OpenAI, Claude, LangChain, Vercel AI output schemas via `connect*()` helpers (`libs/sdk/src/direct/connect.ts:157-281`).
- **Vector search for tool retrieval**: CodeCall plugin uses `vectoriadb` (`TFIDFVectoria` / `VectoriaDB`) for semantic-ish tool search (`plugins/plugin-codecall/src/services/tool-search.service.ts:3-5`, `351-365`, `766-771`).
- **Sandboxed script execution**: CodeCall uses `@enclave-vm/core` for AgentScript execution (`plugins/plugin-codecall/src/services/enclave.service.ts:4-5`, `114-125`, `159-163`).
- **Cache/session backends**: Redis and Vercel KV appear in plugin/provider implementations (e.g., cache/remember plugins), though not all are agent-specific.
- **No dedicated browser automation toolchain** (e.g., Playwright-for-agents) is wired as a first-class agent tool in core runtime; Playwright exists mainly for testing.

## 5. Notable Code Walkthrough

- `libs/sdk/src/agent/agent-execution-loop.ts:159-454` - Core iterative agent runtime (LLM call, tool-call extraction/execution, stop conditions). This is the heart of “agentic” behavior.
- `libs/sdk/src/common/interfaces/agent.interface.ts:184-297` - Default `AgentContext.execute()` implementation that runs the loop, emits progress/notifications, and parses model output.
- `libs/sdk/src/agent/agent.instance.ts:165-195` - Builds an isolated per-agent scope (private tools/plugins/resources/prompts/agents), showing encapsulated agent environments.
- `libs/sdk/src/agent/flows/call-agent.flow.ts:114-670` - Production flow pipeline for invoking an agent with validation, authorization, rate/concurrency guards, execution, and MCP-formatted finalize.
- `plugins/plugin-codecall/src/services/tool-search.service.ts:295-377` - Shows advanced orchestration support: indexing/searching tools with TF-IDF or ML embeddings for agent-facing tool discovery.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. This repo operationalizes workflow automation at two layers: (1) explicit DAG job workflows (`libs/sdk/src/workflow/engine/workflow.engine.ts:18-30`, `80-177`) and (2) LLM-driven tool orchestration loops (`libs/sdk/src/agent/agent-execution-loop.ts:163-167`). In other words, it automates multi-step tasks through deterministic workflow engines and agentic tool-calling abstractions in one framework. It is not primarily a code generator or RAG app; those can be built on top, but the shipped core is orchestration infrastructure.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong typed architecture: decorators, schemas, and MCP-typed flows reduce integration ambiguity.
  - Clear agent runtime separation: registry/instance/context/loop responsibilities are modular.
  - Unified lifecycle controls (auth, rate-limit, concurrency, hooks) in agent invocation flow.
  - Practical ecosystem integrations (OpenAI/Anthropic adapters, connect helpers, plugin model).
  - Supports both deterministic DAG workflows and LLM tool loops in same platform.

- **Limitations:**
  - Multi-agent “swarm” appears partially implemented; visibility metadata exists, but direct inter-agent call path is not prominently wired in default loop (`invokeAgent()` base method throws in `AgentContext`).
  - Framework complexity is high; many abstractions/registries increase onboarding burden.
  - Some capabilities are plugin-dependent (e.g., retrieval/search behavior via CodeCall), not core.
  - Runtime behavior quality depends heavily on user-provided agent prompts/system instructions; no built-in planner decomposition strategy.
  - Not a ready-made benchmark app for MAS; mainly infrastructure requiring custom app definitions.

- **Research relevance:**
  - Evidence of **industrial TypeScript design patterns for agent frameworks** (typed flows + DI + protocol boundaries).
  - Useful case for studying **tool-calling loop orchestration** vs. graph-based frameworks.
  - Demonstrates convergence of **agentic loops + deterministic workflow DAGs** in one codebase.
  - Shows how MCP transport/protocol concerns are integrated into agent lifecycle at framework level.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
