---
repo_name: ruvnet/ruflo
url: "https://github.com/ruvnet/ruflo"
stars: 32852
forks: 3704
contributors_count: 21
last_commit_date: "2026-04-11T16:20:01+00:00"
primary_use_case: Simulation
user_tier: Mainstream
total_score: 10
architecture_labels: [LangGraph, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T08:29:27.941573+00:00"
model: auto
duration_s: 115.2
clone_size_kb: 262989
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`ruvnet/ruflo` is a TypeScript-based agent orchestration platform centered on an MCP server plus CLI that manages swarms, agents, tasks, workers, and memory. A user typically runs CLI commands like `claude-flow swarm init`, `agent spawn`, and `mcp start`, which route into MCP tools and coordinator services. The repo provides infrastructure for multi-agent coordination (topology, task assignment, status, scaling) and pluggable LLM backends (Anthropic/OpenAI/Google/etc.) via a provider manager. In practice, much of the “agent intelligence” in this codebase is orchestration and runtime plumbing, while concrete cognitive behavior is often delegated to callbacks, external tools, or provider calls.

## 2. Agent Framework & Architecture

This repo uses a **custom framework**, not LangGraph/AutoGen/CrewAI/LangChain/LlamaIndex. I did not find framework imports for those libraries in source scans; instead, orchestration is implemented in project-native modules like `SwarmCoordinator`, `WorkflowEngine`, MCP tools, and CLI wrappers (`v3/src/coordination/application/SwarmCoordinator.ts`, `v3/src/task-execution/application/WorkflowEngine.ts`, `v3/mcp/tools/*.ts`, `v3/@claude-flow/cli/src/commands/*.ts`).

Architecturally, there are three layers:
1. **Control plane / API surface**: MCP server and tools (`v3/mcp/server.ts`, `v3/mcp/tools/index.ts`) expose operations like `agent/spawn`, `swarm/init`, `tasks/create`, `memory/search`.
2. **Orchestration runtime**: `SwarmCoordinator` handles agent registry/topology/task distribution; `WorkflowEngine` resolves dependencies and executes tasks in order (`v3/src/coordination/application/SwarmCoordinator.ts`, `v3/src/task-execution/application/WorkflowEngine.ts`).
3. **Model access layer**: provider abstraction and concrete adapters for Anthropic/OpenAI/etc. (`v3/@claude-flow/providers/src/provider-manager.ts`, `.../anthropic-provider.ts`, `.../openai-provider.ts`).

Important nuance: core `Agent` execution is lightweight and callback-driven, not a built-in prompt-planning agent loop (`v3/src/agent-lifecycle/domain/Agent.ts`).

## 3. Orchestration Pattern

Closest match: **hierarchical + swarm hybrid** (manager-worker style with optional mesh links), plus task/workflow queue execution.

Control flow from workflow → coordinator → agent:

```43:65:v3/src/task-execution/application/WorkflowEngine.ts
export class WorkflowEngine {
  async executeTask(task: ITask, agentId: string): Promise<TaskResult> {
    // ...memory logging...
    const result = await this.coordinator.executeTask(agentId, task);
    // ...memory logging...
    return result;
  }
}
```

```193:206:v3/src/coordination/application/SwarmCoordinator.ts
async executeTask(agentId: string, task: ITask): Promise<TaskResult> {
  const agent = this.agents.get(agentId);
  if (!agent) return { taskId: task.id, status: 'failed', error: `Agent ${agentId} not found`, agentId };
  const startTime = Date.now();
  const result = await agent.executeTask(task);
  const duration = Date.now() - startTime;
```

Topology switching (hierarchical vs mesh) is explicit in coordinator connection wiring:

```421:440:v3/src/coordination/application/SwarmCoordinator.ts
private updateConnections(agent: Agent): void {
  if (this.topology === 'mesh') {
    // connect to all peers
  } else if (this.topology === 'hierarchical') {
    const leader = this.getLeader();
    if (leader && agent.role !== 'leader') {
      this.connections.push({ from: agent.id, to: leader.id, type: 'leader' });
```

## 4. Tools & External Integrations

- **MCP server + tool ecosystem**: primary external interface for orchestration and automation (`v3/mcp/server.ts`, `v3/mcp/tools/index.ts`).
- **LLM providers/APIs**: Anthropic and OpenAI implemented with direct HTTP `fetch` to provider endpoints; also Google/Cohere/Ollama/RuVector through provider manager (`v3/@claude-flow/providers/src/provider-manager.ts`, `.../anthropic-provider.ts`, `.../openai-provider.ts`).
- **Memory/Vector integration**: MCP memory tools integrate with `@claude-flow/memory` service for semantic/hybrid retrieval (`v3/mcp/tools/memory-tools.ts`).
- **Background worker subsystem**: worker dispatch tools and trigger-based analyzers (`worker/dispatch`, `worker/status`, etc.) wired to swarm worker dispatch service (`v3/mcp/tools/worker-tools.ts`, `v3/@claude-flow/swarm/src/workers/worker-dispatch.ts`).
- **CLI filesystem/session state integration**: CLI commands read/write `.swarm` and related state/metrics files for status and coordination state (`v3/@claude-flow/cli/src/commands/swarm.ts`, `.../agent.ts`).
- **Transport integrations**: stdio/http/websocket transport support in MCP server (`v3/mcp/server.ts`, `v3/mcp/transport/*`).

No concrete browser automation pipeline (e.g., Playwright) was found in these core runtime files.

## 5. Notable Code Walkthrough

- `v3/src/coordination/application/SwarmCoordinator.ts:36-457`  
  Core swarm runtime: agent lifecycle, topology-specific connections, load-balanced task assignment, concurrent execution, and basic consensus simulation.
- `v3/src/task-execution/application/WorkflowEngine.ts:43-489`  
  Workflow DAG/dependency executor over swarm agents with pause/resume/rollback, nested workflows, and memory/event logging.
- `v3/mcp/server.ts:83-792`  
  Production MCP server implementation: session management, request routing (`tools/list`, `tools/call`), transport startup, and built-in tool registration.
- `v3/mcp/tools/agent-tools.ts:33-529`  
  Runtime-facing agent operations (`agent/spawn`, `agent/list`, `agent/status`, `agent/terminate`) with schema validation and coordinator bridging.
- `v3/@claude-flow/providers/src/provider-manager.ts:61-538`  
  Multi-provider LLM router with load balancing, fallback, caching, and unified completion API across Anthropic/OpenAI/etc.

## 6. Use-Case Mapping

The assigned label **Simulation** is not the best fit after inspecting code. This repository primarily implements **Workflow Automation** for multi-agent orchestration: creating agents, assigning tasks, coordinating topologies, managing memory, running MCP tools, and exposing CLI control loops. While there are simulated elements (e.g., random consensus in `SwarmCoordinator`, mocked/stub-like worker execution phases), the core product intent and executable pathways are orchestration/automation pipelines rather than simulation as the primary application domain.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong modular separation: MCP API, orchestration runtime, and provider abstraction are clearly split.
  - Broad operational surface (agent/swarm/task/memory/worker/session tools) with typed schemas (`zod`) and consistent interfaces.
  - Multi-provider LLM strategy (failover, load balancing, caching) is production-oriented.
  - Supports multiple topologies and explicit coordinator-level control for MAS experiments.
  - CLI and MCP layers provide both human and programmatic control paths.

- **Limitations:**
  - Several “agent intelligence” paths are shallow/stubbed (e.g., `Agent.executeTask` minimal overhead; worker executors mostly synthetic progress/data).
  - Core runtime does not show rich built-in planning/reasoning loops per agent; many behaviors rely on callbacks/external orchestration.
  - Consensus in `SwarmCoordinator` is simulated with random voting, limiting real MAS decision fidelity.
  - Some CLI behavior is state-file driven and can diverge from true runtime if external components are unavailable.
  - Heavy feature surface may obscure what is fully operational vs compatibility/scaffolding.

- **Research relevance:**
  - Useful evidence of **engineering patterns for MAS orchestration infrastructure** (tooling, topology management, lifecycle APIs).
  - Good case study for **MCP-based agent control planes** and standardized tool invocation.
  - Illustrates **provider-agnostic LLM routing** in multi-agent contexts.
  - Demonstrates practical tradeoff between orchestration breadth and depth of autonomous agent cognition.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
