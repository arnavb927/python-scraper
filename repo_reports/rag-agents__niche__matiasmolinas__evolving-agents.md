---
repo_name: matiasmolinas/evolving-agents
url: "https://github.com/matiasmolinas/evolving-agents"
stars: 450
forks: 35
contributors_count: 4
last_commit_date: "2025-11-24T12:29:05+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T17:18:25.579912+00:00"
model: auto
duration_s: 74.9
clone_size_kb: 7337
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`evolving-agents` is a Python toolkit for building an “agent ecosystem” where a central orchestrator can discover, reuse, create, and execute agent/tool components stored in a shared library. In practice, a user runs demo scripts (for example the invoice-processing demo) that boot a `SystemAgent`, `Architect-Zero`, and memory/review agents, then submit a high-level task prompt; the system plans a workflow, optionally routes it through human-in-the-loop review, and executes it. The output is typically structured task results (e.g., JSON extraction/verification) plus persisted metadata in MongoDB collections. The project also includes component evolution and multi-framework execution support (BeeAI-native agents plus OpenAI Agents SDK adapters).  

## 2. Agent Framework & Architecture

The primary runtime framework is **BeeAI** (`beeai-framework==0.1.4` in `requirements.txt:1`), confirmed by pervasive `ReActAgent`, BeeAI `Tool`, `TokenMemory`, and BeeAI `ChatModel` imports (e.g., `evolving_agents/core/system_agent.py:8-11`, `evolving_agents/agents/architect_zero.py:8-13`). It is **not** CrewAI/LangGraph/LangChain-based; no substantive imports for those frameworks appear in core code. A secondary integration path exists for **OpenAI Agents SDK** (`openai-agents==0.0.4`, `requirements.txt:3`) via provider/adapters and tools (`evolving_agents/tools/openai_agents/execute_openai_agent_tool.py:18-20`).

High-level architecture is a **multi-agent orchestration stack**:  
- `SystemAgent` is the central ReAct orchestrator with a large toolset for library search/evolution, workflow generation/processing, intent review, and memory context (`evolving_agents/core/system_agent.py:158-164`).  
- `Architect-Zero` is a separate ReAct agent focused on requirement analysis and solution design JSON (`evolving_agents/agents/architect_zero.py:51-61`, `109-117`).  
- `MemoryManagerAgent` handles experience storage/search/summarization via internal tools (`evolving_agents/agents/memory_manager_agent.py:32-36`).  
- Optional `IntentReviewAgent` performs design/component/plan gating before execution (`evolving_agents/agents/intent_review_agent.py:65-74`).

The “intelligence” is distributed across (a) ReAct policies in BeeAI agents, (b) tool prompts that generate designs/workflows, and (c) retrieval over SmartLibrary embeddings. Planning is partly textual (LLM-generated YAML/JSON), then formalized as executable workflow steps or intent plans (`evolving_agents/workflow/generate_workflow_tool.py:42-49`, `evolving_agents/workflow/process_workflow_tool.py:44-50`).

## 3. Orchestration Pattern

Closest fit: **Hierarchical (manager-worker) with tool-mediated workflow execution**.

`SystemAgent` is the manager/orchestrator; it delegates to specialized tools and other agents (via agent bus), while `Architect-Zero` and `MemoryManagerAgent` act as specialized workers. Control flow is not a graph state machine like LangGraph; it is an orchestrator calling tools/agents through explicit method calls and capability requests.

Example 1 (`evolving_agents/core/system_agent.py:158-164`): manager loads heterogeneous toolchain.
```python
tools = [
    contextual_search_tool, task_context_tool, search_tool, create_tool, evolve_tool,
    register_tool, request_tool, discover_tool,
    generate_workflow_tool, process_workflow_tool,
    workflow_design_review_tool, component_selection_review_tool, approve_plan_tool,
    experience_recorder_tool, context_builder_tool,
]
```

Example 2 (`evolving_agents/agent_bus/smart_agent_bus.py:657-713`): bus-mediated delegation to discovered/specified agent capability.
```python
result_data = await asyncio.wait_for(
    self._execute_agent_task(agent_to_use_doc, task=content), timeout=timeout
)
response = {
    "status": "success",
    "agent_id": agent_id_to_use,
    "agent_name": agent_to_use_doc.get("name"),
    "capability_executed": capability,
    "content": result_data,
}
```

## 4. Tools & External Integrations

- **MongoDB / Motor (primary persistence + registry + logs + intent plans)**: SmartLibrary components, agent registry, bus logs, LLM cache, intent plans (`evolving_agents/smart_library/smart_library.py:29-33`, `evolving_agents/agent_bus/smart_agent_bus.py:86-90`, `evolving_agents/workflow/process_workflow_tool.py:81-83`, `evolving_agents/core/llm_service.py:41-50`).
- **MongoDB Atlas Vector Search + fallback text/regex search** for semantic retrieval of components and agent descriptions (`evolving_agents/smart_library/smart_library.py:49-52`, `268-305`, `330-333`; `evolving_agents/agent_bus/smart_agent_bus.py:603-628`).
- **OpenAI API** for chat + embeddings in `LLMService` (`evolving_agents/core/llm_service.py:258-267`, `395-403`).
- **Ollama** embedding/chat option (`evolving_agents/core/llm_service.py:312-319`, `404-413`).
- **BeeAI tools runtime** (`Tool`, `RunContext`, `Emitter`) across workflow/context/review/memory tools (e.g., `evolving_agents/workflow/generate_workflow_tool.py:14-16`).
- **OpenAI Agents SDK integration** (agent execution, tool adapters, guardrail/tracing adapters): `evolving_agents/tools/openai_agents/execute_openai_agent_tool.py:18-20`, `evolving_agents/adapters/openai_tool_adapter.py`, `evolving_agents/adapters/openai_guardrails_adapter.py`.
- **YAML workflow generation/parsing** as orchestration artifact (`evolving_agents/workflow/generate_workflow_tool.py:187-236`, `evolving_agents/workflow/process_workflow_tool.py:120-154`).

No browser automation or shell-control agent tooling is wired in core runtime.

## 5. Notable Code Walkthrough

- `evolving_agents/core/system_agent.py:50-227` - Defines the central `SystemAgentFactory`; wires >10 tools spanning retrieval, creation/evolution, workflow generation/processing, review, and memory context. This is the main orchestrator assembly point.
- `evolving_agents/agents/architect_zero.py:51-209` - Builds `Architect-Zero` ReAct agent and its design-oriented tools (`AnalyzeRequirementsTool`, `DesignSolutionTool`, `ComponentSpecificationTool`) that transform natural-language task goals into structured solution design JSON.
- `evolving_agents/smart_library/smart_library.py:268-417` - Implements dual-embedding semantic retrieval with Atlas Vector Search and score fusion (content vs applicability), which is the repository’s key RAG substrate for component reuse decisions.
- `evolving_agents/agent_bus/smart_agent_bus.py:482-554, 657-743, 809-900` - Registers agents with embeddings, discovers by capability/vector similarity, and executes delegated tasks with timeout/circuit-breaker/logging; this is the runtime coordination backbone.
- `evolving_agents/workflow/process_workflow_tool.py:44-50, 172-260, 306-419` - Converts generated YAML workflows into validated executable steps or into persisted `IntentPlan` objects for review-first execution mode.

## 6. Use-Case Mapping

The repo does implement **RAG + Agents** in a concrete way: `SmartLibrary.semantic_search()` retrieves semantically relevant agent/tool components via embeddings and vector search (`evolving_agents/smart_library/smart_library.py:268-305`), and those retrieved components inform downstream planning, creation, and execution (`evolving_agents/agents/architect_zero.py:268-286`, `evolving_agents/tools/context/context_builder_tool.py:198-216`). So retrieval is not just document QA; it is retrieval of executable components and prior experiences to guide agent orchestration.

That said, the dominant end-to-end behavior is arguably **Workflow Automation** (generate/validate workflow, optional intent approval, execute steps, log outcomes) (`evolving_agents/workflow/generate_workflow_tool.py:42-49`, `evolving_agents/workflow/process_workflow_tool.py:44-50`). The assigned label “RAG + Agents” is directionally valid, but “Workflow Automation” is a better primary category for observed runtime behavior.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Clear multi-agent separation of roles (orchestrator, architect, memory manager, reviewer) with explicit factories and tool boundaries.
- Practical memory/retrieval substrate using MongoDB + embeddings + vector search + fallback search.
- Supports governance via review gates (`design`, `components`, `intent plan`) instead of pure autonomous execution.
- Cross-framework extensibility: BeeAI-native runtime with OpenAI Agents provider/adapters.
- Strong operational scaffolding: registry, logs, circuit breakers, health checks, usage metrics.

- **Limitations:**
- Heavy dependence on LLM-generated YAML/JSON parsing introduces fragility and cleanup heuristics.
- Many flows are demo-driven and imperative; limited formal tests for full orchestration safety/regression.
- Atlas vector index setup is manual; behavior degrades to fallback search if infra is misconfigured.
- Execution policy is mostly centralized in one large `SystemAgent` toolset, which can become hard to reason about.
- Some code quality inconsistencies (defensive patches, mixed patterns, broad exception handling) suggest evolving architecture.

- **Research relevance:**
- Useful evidence of a **production-style multi-agent orchestration architecture** (manager + specialist agents + shared bus + memory).
- Demonstrates **component-level RAG for agent/tool reuse**, not only text QA retrieval.
- Shows integration of **human-in-the-loop review checkpoints** inside an autonomous workflow pipeline.
- Illustrates practical resilience patterns in MAS systems (circuit breakers, logging, status sync, dynamic instantiation).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
