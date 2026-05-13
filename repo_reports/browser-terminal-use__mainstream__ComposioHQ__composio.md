---
repo_name: ComposioHQ/composio
url: "https://github.com/ComposioHQ/composio"
stars: 27874
forks: 4531
contributors_count: 48
last_commit_date: "2026-04-22T08:59:03+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 8
architecture_labels: [LangGraph, LangChain, AutoGen, CrewAI]
use_case_labels: [Browser / Terminal Use]
generated_at: "2026-05-05T06:46:54.444482+00:00"
model: auto
duration_s: 119.0
clone_size_kb: 170613
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

Composio is an agent tooling SDK/platform that lets developers plug LLM applications into a very large catalog of external tools (GitHub, Gmail, etc.) with auth, execution, and routing handled by Composio services. In practice, users initialize `Composio`, fetch provider-wrapped tools (for OpenAI/LangChain/LangGraph/CrewAI/AutoGen/etc.), and run tool-calling agents against those tools. The codebase includes both TypeScript and Python SDKs, plus a CLI that can execute scripts with helper functions and spawn sub-agents. What users get is a unified interface for tool discovery, execution, session-scoped routing (including MCP), and optional local custom tools mixed with remote APIs.

## 2. Agent Framework & Architecture

This repo is **framework-integrator + orchestration infrastructure**, not a single in-house LLM agent framework. It has concrete adapters for multiple ecosystems: LangGraph, LangChain, AutoGen, CrewAI, OpenAI Agents, Claude Agent SDK, etc., confirmed by provider packages and imports like `from langgraph.graph import END, StateGraph` (`python/providers/langgraph/langgraph_demo.py:9`), `from autogen import AssistantAgent, UserProxyAgent` (`python/providers/autogen/autogen_demo.py:4`), and `from crewai import Agent, Crew, Task` (`python/providers/crewai/crewai_demo.py:6`).

The architectural core is Composio’s provider abstraction: `AgenticProvider` defines `wrap_tool(s)` contracts (`python/composio/core/provider/agentic.py:25-48`), and `Tools` injects execution callbacks so framework-native tool objects call back into Composio execution/auth/routing (`python/composio/core/models/tools.py:365-374`, `423-439`). This means most “intelligence” (planning/reasoning) remains in external LLM frameworks; Composio focuses on tool brokering, schema shaping, and execution pipelines.

A second orchestration layer appears in Tool Router sessions and CLI subagent runtime: `ToolRouterSession` can split `COMPOSIO_MULTI_EXECUTE_TOOL` requests into local custom tools vs backend tools, execute in parallel, and merge results (`ts/packages/core/src/models/ToolRouterSession.ts:396-527`, mirrored in Python at `python/composio/core/models/tool_router_session.py:265-410`). The CLI also implements an `experimental_subAgent` flow that spawns ACP adapters (Codex/Claude), manages permissions, and enforces structured output (`ts/packages/cli/src/services/run-subagent-acp.ts:505-733`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) + graph/event-style hybrids**.

- **Manager-worker in session routing:** a coordinator intercepts one meta-call (`COMPOSIO_MULTI_EXECUTE_TOOL`), partitions work into local vs remote workers, runs them concurrently, then merges.
- **Graph style in examples:** LangGraph demo explicitly builds a state graph with conditional edge agent->tool->agent loop.
- **Event-driven stream handling in CLI subagent:** ACP session updates (`agent_message_chunk`, `tool_call_update`, `plan`) are processed as events.

Control-flow excerpt (manager-worker partitioning):

```ts
// ts/packages/core/src/models/ToolRouterSession.ts:417-425
for (let i = 0; i < parsed.length; i++) {
  const entry = findCustomTool(this.customToolsMap, parsed[i].tool_slug);
  if (entry) {
    localItems.push({ index: i, entry });
  } else {
    remoteIndices.push(i);
  }
}
```

Parallel execution + merge:

```ts
// ts/packages/core/src/models/ToolRouterSession.ts:458-466
const [localResults, remoteResult] = await Promise.all([
  Promise.all(localPromises),
  remotePromise,
]);

if (remoteIndices.length === 0 && localResults.length === 1) {
  return localResults[0].result;
}
```

## 4. Tools & External Integrations

- **Composio backend tool APIs** (tool list/retrieve/execute/proxy) wired in `Tools` classes: `python/composio/core/models/tools.py:614-623`, `775-798`; `ts/packages/core/src/models/Tools.ts:843-867`, `1133-1172`.
- **Tool Router session API** (session tools/search/execute/link/toolkits/proxy): `python/composio/core/models/tool_router_session.py:427-539`, `576-582`; `ts/packages/core/src/models/ToolRouterSession.ts:202-370`.
- **MCP server integration** via session metadata and framework clients: e.g., OpenAI Hosted MCP tool and Claude Agent SDK MCP server configs in `python/examples/tool_router/openai_agents.py:12-26` and `python/examples/tool_router/claude_agent.py:15-24`; TS example in `ts/examples/tool-router/src/claude-agent-sdk.ts:14-19`.
- **External LLM agent frameworks** via provider adapters:
  - CrewAI wrapper: `python/providers/crewai/composio_crewai/providers.py:12-50`
  - AutoGen usage: `python/providers/autogen/autogen_demo.py:20-47`
  - LangGraph usage: `python/providers/langgraph/langgraph_demo.py:69-87`
- **CLI subagent ACP adapters** for Codex/Claude (`@agentclientprotocol/sdk`, spawned adapter processes): `ts/packages/cli/src/services/run-subagent-acp.ts:7`, `66-124`, `533-543`.
- **Filesystem + local execution path for custom tools** inside sessions (in-process local tool execution): `python/composio/core/models/tool_router_session.py:566-575`; `ts/packages/core/src/models/ToolRouterSession.ts:309-318`.

## 5. Notable Code Walkthrough

- `python/composio/core/models/tools.py:306-374,423-552`  
  Central SDK engine: fetches raw tool schemas, applies modifiers, wraps tools for agentic/non-agentic providers, and constructs execution callbacks that power framework tool calls.

- `ts/packages/core/src/models/ToolRouterSession.ts:103-142,396-527`  
  Most representative orchestration code: session-scoped tool wrapping plus `routeMultiExecute` that partitions local/remote tool calls, parallelizes execution, and returns unified result envelopes.

- `ts/packages/cli/src/services/run-subagent-acp.ts:505-733`  
  Implements subagent runtime over ACP: spawn adapter, initialize session, stream updates, request permissions, prompt/repair structured output, return normalized subagent response.

- `python/providers/crewai/composio_crewai/providers.py:12-50`  
  Shows provider adapter pattern clearly: wraps Composio tool schemas as framework-native `BaseTool` objects and delegates execution through Composio callback.

- `python/providers/langgraph/langgraph_demo.py:69-87`  
  Concrete agent-graph loop example (`StateGraph`) showing how Composio tools are inserted into a LangGraph state machine.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially accurate. This repo’s primary implementation is broader **Workflow Automation**: it standardizes authenticated tool execution across many SaaS/toolkits and agent frameworks, with routing/session abstractions and tool-search APIs (`tools.get`, `tool_router.session.search/execute`) for business/task automation. Terminal use exists (CLI `run`, subagents, local tool execution), but it is a delivery surface rather than the core domain. Best fit category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong cross-framework interoperability via provider wrappers instead of locking into one agent runtime.
  - Practical hybrid orchestration (local custom tools + remote APIs) with parallel merge logic in Tool Router sessions.
  - Mature operational concerns: auth flows, account linking, proxy execution, schema modifiers, file upload/download mediation.
  - Supports both SDK embedding and CLI agent workflows, including subagent invocation and structured-output repair.

- **Limitations:**
  - Core “agent intelligence” (planning, memory, reasoning strategies) mostly delegated to external frameworks; limited native planning logic.
  - Multi-agent coordination is present but fragmented (CLI subagent runtime, framework demos) rather than a unified MAS runtime API.
  - Heavy reliance on hosted backend behavior (tool router/offload/auth) makes some orchestration semantics opaque from OSS code alone.
  - Example coverage includes many single-agent tool-calling flows; fewer canonical end-to-end multi-agent benchmark scenarios.

- **Research relevance:**
  - Good evidence for **agent tooling middleware** patterns (schema normalization, tool wrapping, execution callbacks).
  - Useful reference for **hybrid orchestration** of local and remote tools under a unified session protocol.
  - Demonstrates practical **multi-framework agent portability** (same tool substrate across LangGraph/LangChain/AutoGen/CrewAI/OpenAI Agents).
  - Shows production-oriented concerns in agent systems (permissions, structured output enforcement, auth/session lifecycle).

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
