---
repo_name: OpenBMB/ChatDev
url: "https://github.com/OpenBMB/ChatDev"
stars: 32824
forks: 4064
contributors_count: 17
last_commit_date: "2026-04-07T05:37:11+00:00"
primary_use_case: Simulation
user_tier: Mainstream
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Simulation]
generated_at: "2026-04-27T09:27:23.032509+00:00"
model: auto
duration_s: 135.7
clone_size_kb: 305854
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`OpenBMB/ChatDev` (in this snapshot branded as `DevAll`/`ChatDev_new`) is a configurable multi-agent workflow engine where users run a YAML-defined graph of nodes (agents, loop controls, literals, subgraphs, etc.) rather than a single chatbot. The main CLI entrypoint (`run.py`) loads a workflow YAML, asks for a task prompt, builds a runtime graph context, and executes the graph end-to-end (`run.py:38-123`). In practical terms, a user provides a task and gets a final synthesized output plus generated workspace artifacts/logs from coordinated agent roles (e.g., programmer, reviewer, tester in `yaml_instance/ChatDev_v1.yaml`). The project solves “structured collaboration” for complex tasks by encoding role prompts, control flow, loop exits, and tool permissions in workflow config instead of hardcoding a single pipeline.

## 2. Agent Framework & Architecture

This repo is **custom orchestration/runtime code**, not LangGraph/LangChain/CrewAI/AutoGen. Framework imports for those are absent, while core orchestration is implemented in internal modules like `workflow/graph.py`, `workflow/graph_manager.py`, `runtime/node/executor/agent_executor.py`, and registry-based node/provider systems (`runtime/node/registry.py`, `runtime/node/agent/providers/base.py`).

Architecture is graph-centric: workflow YAML defines nodes/edges; `GraphManager` instantiates node objects, wires edges with condition managers, computes DAG/cycle execution structure, and determines explicit start nodes (`workflow/graph_manager.py:26-351`). At runtime, `GraphExecutor` builds shared context (tool manager, function managers, token tracker, memory/thinking managers), chooses execution strategy (DAG/cycle/majority-vote), and executes each triggered node while routing outputs via edge conditions (`workflow/graph.py:71-342`, `workflow/runtime/execution_strategy.py:14-149`).

“Intelligence” is distributed across (a) per-agent role prompts and tool bindings in YAML, (b) provider adapters (OpenAI/Gemini) that implement tool-call capable message serialization, and (c) optional memory/thinking hooks (`runtime/node/executor/agent_executor.py:80-157`, `runtime/node/agent/providers/openai_provider.py:53-89`, `runtime/node/agent/providers/gemini_provider.py:50-77`). Agents are runtime-instantiated node executions, not static Python classes per persona.

## 3. Orchestration Pattern

Closest match: **graph-based orchestration with conditional/event-style edge triggering** (primary), including DAG, cycle-aware loops, and optional majority voting.

Control is explicitly strategy-driven:

```599:326:workflow/graph.py
if self.graph.is_majority_voting:
    strategy = MajorityVoteStrategy(...)
elif self.graph.has_cycles:
    strategy = CycleExecutionStrategy(...)
else:
    strategy = DagExecutionStrategy(...)
strategy.run()
```

Edge routing is condition-gated and trigger-propagated (message passing + trigger flags):

```141:176:runtime/edge/conditions/base.py
if edge_link.carry_data:
    payload = self._prepare_payload_for_target(...)
    target_node.append_input(payload)
...
if edge_link.trigger:
    edge_link.triggered = True
```

This is not a simple manager-worker chain; it is a configurable stateful graph where multiple role agents can loop/re-enter based on edge conditions (e.g., keyword-based `<INFO>` exits in `yaml_instance/ChatDev_v1.yaml:715-739` and `:924-950`).

## 4. Tools & External Integrations

- **LLM providers (OpenAI, Gemini)**: provider registry and adapters in `runtime/node/agent/providers/builtin_providers.py:5-25`, `openai_provider.py`, `gemini_provider.py`.
- **Function tools (local Python tools loaded dynamically)**: `ToolManager` routes `type: function` to `functions/function_calling` via `FunctionManager` (`runtime/node/agent/tool/tool_manager.py:147-174`, `utils/function_manager.py:42-82`).
- **MCP integration (remote HTTP + local stdio MCP servers)**: tool specs/execution for `mcp_remote` and `mcp_local` in `tool_manager.py:193-239` and `:279-307`; config schemas in `entity/configs/node/tooling.py:310-582`; YAML demo in `yaml_instance/demo_mcp.yaml:19-22`.
- **Filesystem/workspace operations**: read/write/edit/search/list/delete tools in `functions/function_calling/file.py` (e.g., `save_file`, `apply_text_edits`, `search_in_files`).
- **Python environment and command execution via uv**: install/init/run in `functions/function_calling/uv_related.py:200-313`.
- **Web retrieval/search APIs**: Serper Google API and Jina Reader proxy in `functions/function_calling/web.py:20-39` and `:129-168`.
- **Human-in-the-loop prompt channel**: `call_user` tool invokes runtime human prompt service (`functions/function_calling/user.py:1-17`; service injection in `workflow/graph.py:240-253`).
- **Memory backends**: simple/file/mem0/blackboard memory modules exist and are attached per node (`runtime/node/agent/memory/*`, manager setup in `workflow/graph.py:150-209`).

## 5. Notable Code Walkthrough

- `workflow/graph.py:53-342` - Core runtime executor: builds runtime context, initializes memories/thinking, selects DAG/cycle/majority strategy, executes nodes, archives final artifacts.
- `runtime/node/executor/agent_executor.py:43-166` - Per-agent execution pipeline: prepares conversation, retrieves memory, invokes provider, handles iterative tool calls, applies post-processing and memory updates.
- `runtime/node/agent/tool/tool_manager.py:97-174` - Unified tooling backend: resolves tool schemas and dispatches execution across local function tools and MCP (local/remote) transports.
- `workflow/graph_manager.py:118-239` - Compiles graph structure from config: node/edge instantiation, condition+processor binding, cycle detection/topology layering.
- `yaml_instance/ChatDev_v1.yaml:38-505` - Representative multi-role workflow definition showing concrete agent personas, prompts, tool scopes, loops, and edge-driven control policy.

## 6. Use-Case Mapping

The assigned label **Simulation** is understandable historically (role-played “company” personas), but in this codebase the dominant implemented behavior is **automated workflow execution for real tasks** (especially code authoring/review/testing loops with filesystem and command tools). `ChatDev_v1` is effectively an operational workflow: agents edit files, run tests, gate transitions via conditions, and iterate until completion (`yaml_instance/ChatDev_v1.yaml:429-505`, `:667-739`). So the better fit is **Workflow Automation** (with strong Code Generation sub-behavior), not pure simulation sandboxing.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Declarative multi-agent orchestration via YAML graphs enables reproducible experimentable workflows (`entity/configs/graph.py`, `workflow/graph_manager.py`).
  - Rich control flow beyond linear chains: cycles, dynamic edge processing, majority voting modes (`workflow/runtime/execution_strategy.py`, `workflow/topology_builder.py`).
  - Practical tool ecosystem (filesystem, uv execution, web, MCP, human prompt) integrated at runtime tool-call loop level.
  - Provider abstraction cleanly separates model backends while preserving tool semantics (`providers/base.py`, `openai_provider.py`, `gemini_provider.py`).
  - Memory/thinking extension points are first-class per-node capabilities (`workflow/graph.py:143-209`, `agent_executor.py`).

- **Limitations:**
  - Behavior quality heavily depends on verbose YAML prompt engineering; little centralized planning/verification policy outside prompts.
  - Safety boundaries for tool execution rely on tool implementations; some tools invoke subprocess/network directly, increasing operational risk if misconfigured.
  - Limited built-in evaluation harness for agent outcome quality (runtime logging exists, but task-level correctness metrics are sparse).
  - Default start-node requirement and complex graph semantics may raise configuration complexity for users.
  - Some examples/configs are broad and can blur separation between framework runtime and specific task templates.

- **Research relevance:**
  - Evidence of a production-style **graph MAS runtime** where role-specialized LLM agents coordinate via condition-triggered message passing.
  - Useful case study for comparing DAG vs cycle vs majority-vote orchestration in multi-agent systems.
  - Demonstrates tool-mediated agency (filesystem/command/MCP) in multi-agent workflows rather than chat-only collaboration.
  - Supports studying prompt-role decomposition as organizational control in LLM agent teams.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
