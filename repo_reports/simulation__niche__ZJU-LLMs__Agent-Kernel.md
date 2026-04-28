---
repo_name: ZJU-LLMs/Agent-Kernel
url: "https://github.com/ZJU-LLMs/Agent-Kernel"
stars: 352
forks: 36
contributors_count: 8
last_commit_date: "2026-03-18T02:39:20+00:00"
primary_use_case: Simulation
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T17:27:46.097973+00:00"
model: auto
duration_s: 102.5
clone_size_kb: 102134
uses_mas: yes
final_use_case: Simulation
---
## 1. Overview

`Agent-Kernel` is a Python framework for running large-scale LLM-based multi-agent simulations, with both standalone and Ray-distributed runtimes. A user typically runs scenario scripts such as `examples/standalone_test/run_simulation.py` or `demo/OpenHospital/baseline/run_simulation.py`, which build agents from config/templates, execute them tick-by-tick, and persist/record state. The framework provides reusable core modules (agent manager, action/environment proxies, system timer/messager/recorder) while scenario-specific behavior is implemented as plugins. The output is an evolving simulated world (messages, actions, environment updates, trajectories, optional web panel events), not just a one-shot chatbot response.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/AutoGen/CrewAI as its runtime core. It is a **custom MAS framework** (`agentkernel_standalone` / `agentkernel_distributed`) with its own abstractions (`Builder`, `Controller`, `AgentManager`, `Agent`, plugins) and its own model router (`toolkit/models/router.py`). Framework choice is confirmed by internal imports and class wiring in `packages/agentkernel-standalone/agentkernel_standalone/mas/builder.py:6-16` and `packages/agentkernel-distributed/agentkernel_distributed/mas/pod/pod_manager.py:24-41`.

Architecture is microkernel-like and plugin-driven: each agent is composed of ordered components (default: perceive -> plan -> invoke -> state -> reflect) that execute every tick (`packages/agentkernel-standalone/agentkernel_standalone/mas/agent/agent.py:43-44`, `:193-207`). The “intelligence” primarily lives inside scenario plugins (prompt engineering + tool/action selection), e.g., doctor planning in OpenHospital calls the shared `model.chat(...)` repeatedly with staged prompts and JSON action parsing (`demo/OpenHospital/baseline/plugins/agent/plan/DoctorPlannerPlugin.py:369-380`, `:505-523`, `:636-724`).

In distributed mode, pods are Ray actors managed by a pod manager; each pod hosts an agent manager + controller + action/environment proxies. This allows many agents to run concurrently while sharing system services (timer/messager/recorder) and adapters (`packages/agentkernel-distributed/agentkernel_distributed/mas/pod/mas_pod.py:30-33`, `:99-130`; `.../pod/pod_manager.py:118-159`, `:271-297`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with tick-based event/message dispatch**.

- A top-level runner drives simulation ticks, then calls agent stepping and queued message dispatch:
  - `examples/standalone_test/run_simulation.py:48-50`
  - `demo/OpenHospital/baseline/run_simulation.py:518-522`
- The controller delegates to agent manager; agent manager runs all agents concurrently for the tick:
  - `packages/agentkernel-standalone/agentkernel_standalone/mas/controller/controller.py:58-69`
  - `packages/agentkernel-standalone/agentkernel_standalone/mas/agent/agent_manager.py:114-124`

Short control-flow excerpt:
- `controller.step_agent()` -> `agent_manager.run_tick(current_tick)` (`.../controller.py:67-68`)
- Per tick, each `Agent.run()` executes ordered components (`.../agent.py:201-207`)
- Messages are queued then dispatched by system messager (`.../system/components/messager.py:137-169`)

So this is not a graph state machine (LangGraph-style). It is manager-orchestrated, synchronous tick loop + asynchronous intra-tick fanout + message-queue mediation.

## 4. Tools & External Integrations

- **LLM APIs (OpenAI-compatible endpoints)**: via custom `AsyncModelRouter` + `OpenAIProvider` HTTP calls (`packages/agentkernel-standalone/agentkernel_standalone/toolkit/models/async_router.py:104-167`; `.../api/openai.py:53-97`).
- **Ray distributed actors**: pod manager and pods are Ray actors in distributed runtime (`packages/agentkernel-distributed/agentkernel_distributed/mas/pod/pod_manager.py:534-538`; `.../mas_pod.py:30-33`).
- **Redis KV + Redis Graph**: used for state/data/checkpoints and relationship graph loading in OpenHospital (`demo/OpenHospital/baseline/run_simulation.py:163-169`, `:259-273`, `:323-337`; adapter registration in `demo/OpenHospital/baseline/registry.py:104-111`).
- **Milvus vector DB**: used for medical knowledge retrieval and examination selection (`demo/OpenHospital/baseline/plugins/action/tools/tools_plugin.py:329-360`; `.../DoctorPlannerPlugin.py:1299-1322`; adapter map `registry.py:107-110`).
- **FastAPI/websocket event backend (scenario layer)**: OpenHospital starts local API service and publishes events through Redis (`demo/OpenHospital/baseline/run_simulation.py:474-489`; `demo/OpenHospital/baseline/custom_controller.py:203-227`).
- **MCP dependency present**: `fastmcp` is a dependency (`packages/agentkernel-standalone/pyproject.toml:16`; distributed `.../pyproject.toml:16`), but I did not find first-class MCP server orchestration in the core control loop shown above.

## 5. Notable Code Walkthrough

- `packages/agentkernel-standalone/agentkernel_standalone/mas/builder.py:190-250`  
  Initializes the full standalone runtime pipeline (model router, system, adapters, environment, action, agents, controller), then wires dependencies in `post_init`. This is the assembly heart of the framework.

- `packages/agentkernel-standalone/agentkernel_standalone/mas/agent/agent.py:193-207`  
  Defines the per-agent execution kernel: every tick, components run in configured order. This is the minimal “agent runtime contract.”

- `packages/agentkernel-standalone/agentkernel_standalone/mas/system/components/messager.py:137-169`  
  Implements inter-agent communication routing/filtering. It converts queued messages into concrete deliveries through the controller, enabling social interaction dynamics.

- `demo/OpenHospital/baseline/plugins/agent/plan/DoctorPlannerPlugin.py:369-380` and `:505-526`  
  Shows realistic multi-step LLM planning: stage-based prompt design, structured JSON action outputs, and branching into consultation/exam/diagnosis subflows.

- `demo/OpenHospital/baseline/plugins/action/tools/tools_plugin.py:329-403`  
  Exposes concrete agent tools (e.g., semantic medical knowledge search) that planner/invoker can call, bridging LLM decisions to environment-backed operations.

## 6. Use-Case Mapping

The assigned use case `Simulation` is accurate. The runtime is explicitly tick-based, multi-agent, environment-coupled, and designed for scenario worlds where agents perceive, plan, act, message, and evolve over time (`examples/standalone_test/run_simulation.py:37-61`; `demo/OpenHospital/baseline/run_simulation.py:510-533`). OpenHospital further demonstrates role-specific social simulation (doctor/patient agents, consultations, treatment trajectories), not generic enterprise workflow orchestration. While it includes workflow-like action pipelines, those pipelines are embedded inside a broader social simulation engine.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clean separation of kernel vs scenario plugins enables reuse across domains (`builder`, `registry`, plugin maps).
  - Supports both local and distributed execution with similar abstractions (`standalone` vs `distributed` packages).
  - Strong runtime mechanics for MAS research: dynamic add/remove agents, message interception, state persistence, snapshots/rollback hooks.
  - Realistic tool grounding in demos (Redis graph/KV + Milvus retrieval + environment APIs).
  - Explicit tick loop and component order make behavior traceable and experimentally controllable.

- **Limitations:**
  - Heavy behavior quality depends on prompt engineering in plugins; limited centralized planning formalism.
  - No built-in formal policy learning/planning algorithm; mostly LLM prompt + JSON parsing heuristics.
  - Reliability guardrails are scenario-specific (e.g., retry/mapping logic) rather than universally enforced in core.
  - Framework complexity is high; many moving parts (controllers, pods, adapters, plugins) increase setup/debug burden.
  - MCP appears as dependency but not deeply integrated as a first-class orchestration mechanism in inspected flow.

- **Research relevance:**
  - Useful evidence of a modular microkernel design for scalable LLM-agent social simulation.
  - Demonstrates practical manager-worker + message-queue orchestration at multi-agent runtime scale.
  - Shows how retrieval tools and environment APIs can be embedded in agent decision loops for domain simulations.
  - Provides a concrete case of distributed MAS execution (Ray actors/pods) with persistent simulation state.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Simulation
