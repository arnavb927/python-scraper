---
repo_name: axsaucedo/kaos
url: "https://github.com/axsaucedo/kaos"
stars: 241
forks: 12
contributors_count: 4
last_commit_date: "2026-04-18T11:22:54+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T16:36:00.213753+00:00"
model: auto
duration_s: 73.5
clone_size_kb: 45124
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`axsaucedo/kaos` is a Kubernetes-native system for deploying and coordinating multiple LLM agents as cluster resources (`Agent`, `ModelAPI`, `MCPServer`) rather than as one-off scripts. A user applies CRDs (or sample YAMLs), and the operator creates per-agent deployments/services, injects model/tool/peer wiring via env vars, and exposes OpenAI-compatible chat plus A2A endpoints (`operator/controllers/agent_controller.go:50-355`, `operator/config/samples/3-hierarchical-agents.yaml:67-178`). Each running agent process is powered by the `pydantic-ai-server` runtime, which executes reasoning/tool loops, stores memory, and can delegate work to other agents (`pydantic-ai-server/pais/server.py:99-742`). The result is a runnable multi-agent workflow platform where supervisors, leads, and workers can coordinate tasks over HTTP/A2A and MCP tools in production-like K8s environments.

## 2. Agent Framework & Architecture

The actual agent framework is **PydanticAI** (with `pydantic_graph` under the hood), not CrewAI/LangGraph. This is explicit in imports and model setup: `from pydantic_ai.agent import Agent`, `from pydantic_ai._agent_graph import CallToolsNode`, `from pydantic_graph import End` (`pydantic-ai-server/pais/server.py:17-21`), and dependency declarations include `pydantic-ai>=1.0.0` (`pydantic-ai-server/pyproject.toml:6-10`).

Architecture is split into two layers.  
At runtime, each agent is a FastAPI service (`AgentServer`) wrapping a PydanticAI agent with: model backend resolution, memory backend, MCP toolsets, and optional delegation toolset (`pydantic-ai-server/pais/server.py:663-742`, `pydantic-ai-server/pais/serverutils.py:285-321`). Intelligence mostly lives in: (a) agent instructions configured from CRD/env, (b) the model’s tool-calling behavior, and (c) delegation tools dynamically generated from known peer agents (`pydantic-ai-server/pais/tools.py:55-108`).

Control-plane architecture is Kubernetes operator-driven: the controller reads `Agent` specs, resolves referenced `ModelAPI`/`MCPServer`/peer agents, and renders env vars such as `MODEL_API_URL`, `MCP_SERVERS`, `PEER_AGENTS`, and per-peer card URLs (`operator/controllers/agent_controller.go:464-691`). This turns CRD declarations (e.g., supervisor -> research-lead -> researchers) into concrete multi-agent runtime topology (`operator/config/samples/3-hierarchical-agents.yaml:67-127`).

## 3. Orchestration Pattern

Closest fit: **hierarchical (manager-worker)** with **tool-mediated delegation**, plus optional iterative autonomous loops.  
The hierarchy is declared in `agentNetwork.access` and compiled into peer env vars by the operator (`operator/api/v1alpha1/agent_types.go:36-45`, `operator/controllers/agent_controller.go:644-667`), then exposed as `delegate_to_*` tools inside each agent (`pydantic-ai-server/pais/tools.py:70-91`).

Control flow example 1 (tool creation for each subordinate agent):

```75:86:pydantic-ai-server/pais/tools.py
            tool_name = f"{DELEGATION_TOOL_PREFIX}{name}"
            tools[tool_name] = ToolsetTool(
                toolset=self,
                tool_def=ToolDefinition(
                    name=tool_name,
                    description=desc,
                    parameters_json_schema=_TASK_SCHEMA,
                ),
```

Control flow example 2 (actual delegation call path):

```100:108:pydantic-ai-server/pais/tools.py
        agent_name = name.removeprefix(DELEGATION_TOOL_PREFIX)
        return await execute_delegation(
            agent_name,
            tool_args["task"],
            self._sub_agents[agent_name],
            ctx.deps.session_id,
            ctx.deps.memory,
            self._memory_context_limit,
        )
```

Then `execute_delegation` forwards context + task to the remote agent via A2A/chat (`pydantic-ai-server/pais/tools.py:111-145`, `pydantic-ai-server/pais/serverutils.py:139-226`). This is coordinated multi-agent execution at runtime, not just static config.

## 4. Tools & External Integrations

- **Model APIs (OpenAI-compatible providers/proxies)**: agents call model endpoints through `OpenAIChatModel` + `OpenAIProvider` or string-mode function model (`pydantic-ai-server/pais/serverutils.py:302-317`, `285-313`).
- **MCP tool servers**: MCP servers are parsed from env and attached as PydanticAI toolsets via `MCPServerStreamableHTTP` (`pydantic-ai-server/pais/server.py:16`, `560-584`, `693-723`).
- **Agent-to-agent protocol (A2A JSON-RPC)**: local routes for `SendMessage/GetTask/CancelTask` and remote calls from `RemoteAgent._send_a2a_message` (`pydantic-ai-server/pais/a2a.py:1016-1023`, `851-857`; `pydantic-ai-server/pais/serverutils.py:158-208`).
- **Memory backends**: in-memory, Redis, or null memory used for conversation/history/tool/delegation events (`pydantic-ai-server/pais/server.py:614-633`; `pydantic-ai-server/pais/memory.py:229-370`, `412-655`).
- **Kubernetes operator integration**: CRDs and reconciler wire model/mcp/peer dependencies into deployments/services (`operator/controllers/agent_controller.go:157-213`, `464-691`).
- **Telemetry**: OpenTelemetry tracing/metrics/log correlation across server/delegation/task execution (`pydantic-ai-server/pais/server.py:643-661`; `pydantic-ai-server/pais/tools.py:120-157`; `pydantic-ai-server/pais/a2a.py:192-215`).
- **Custom MCP runtimes**: `python-string` runtime executes Python function strings as tools; `fastmcp-codemode` aggregates upstream MCP servers with CodeMode transform (`mcp-servers/python-string/server.py:14-24`, `mcp-servers/fastmcp-codemode/server.py:23-49`).

## 5. Notable Code Walkthrough

- `pydantic-ai-server/pais/server.py:663-742` - central assembly of each agent runtime: resolves model, parses MCP/peers, injects delegation toolset, and builds `AgentServer`. This is where multi-agent capability is switched on.
- `pydantic-ai-server/pais/tools.py:55-158` - defines `DelegationToolset` and `execute_delegation`; converts peers into callable tools and forwards tasks with memory context.
- `pydantic-ai-server/pais/serverutils.py:91-226` - `RemoteAgent` client logic: discovers peer card, chooses A2A JSON-RPC path when available, falls back to OpenAI-style `/v1/chat/completions`.
- `operator/controllers/agent_controller.go:464-691` - operator-side env synthesis that materializes topology (`PEER_AGENTS`, `MCP_SERVERS`, model config) into deployed pods.
- `pydantic-ai-server/pais/a2a.py:327-371` and `519-683` - task/autonomous orchestration loop (iterative execution, budgets, cancellation, completion logic), enabling workflow-style long-running agent operations.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. KAOS automates end-to-end execution pipelines where multiple role-specialized agents are deployed, connected, and coordinated by policy/config (CRDs) rather than manual glue code. Its runtime supports delegated sub-tasks, tool invocation, memory-backed context passing, and bounded autonomous loops (`pydantic-ai-server/pais/tools.py:111-145`, `pydantic-ai-server/pais/a2a.py:527-683`), which are classic workflow-automation primitives. It is not primarily code generation or pure RAG; it is orchestration of agent workflows over K8s resources.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear multi-agent runtime semantics via explicit delegation tools (`delegate_to_*`) instead of opaque prompt-only coordination.
  - Strong K8s operationalization: CRDs, reconciler, health/readiness, deterministic env wiring.
  - Interoperability: OpenAI-compatible API + A2A JSON-RPC + MCP tool protocol in one stack.
  - Practical observability/memory instrumentation (OTel + event-level memory for tool/delegation traces).
  - Supports both interactive and autonomous iterative task modes with budget controls.

- **Limitations:**
  - Delegation target selection is mostly prompt/model-driven; no explicit planner/optimizer module beyond tool calls.
  - `python-string` MCP runtime uses `exec`, raising obvious security concerns in less-trusted environments (`mcp-servers/python-string/server.py:17`).
  - Some reliability TODOs remain in core paths (e.g., race-condition notes in memory session creation).
  - Hierarchy and permissions are simple allowlists (`agentNetwork.access`), lacking richer policy/governance.
  - No advanced shared blackboard/consensus mechanism; coordination is primarily RPC + memory context replay.

- **Research relevance:**
  - Good evidence of **production-oriented MAS orchestration** (CRD-defined topology + runtime delegation).
  - Useful case for studying **tool-mediated hierarchical control** versus graph-planner approaches.
  - Useful empirical substrate for **agent observability** research (delegation/tool events, task lifecycle telemetry).
  - Demonstrates integration of **protocol-layer interoperability** (A2A + MCP + OpenAI API compatibility).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
