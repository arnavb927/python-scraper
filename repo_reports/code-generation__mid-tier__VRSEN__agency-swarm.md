---
repo_name: VRSEN/agency-swarm
url: "https://github.com/VRSEN/agency-swarm"
stars: 4229
forks: 1022
contributors_count: 24
last_commit_date: "2026-04-22T16:56:33+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T12:23:05.520563+00:00"
model: auto
duration_s: 104.3
clone_size_kb: 67031
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`agency-swarm` is a Python framework for building multi-agent workflows on top of the OpenAI Agents SDK. A user typically defines several role-specific `Agent` objects, wires allowed communication paths in an `Agency`, then runs `agency.get_response(...)` (or streaming/FastAPI variants) to execute the workflow (`src/agency_swarm/agency/core.py:44-61`, `examples/multi_agent_workflow.py:124-155`). The framework handles agent-to-agent delegation via generated tools (`send_message` / handoffs), shared context, thread history, and runtime tool wiring (`src/agency_swarm/agency/setup.py:178-263`). In practice, users get an orchestrated result from one entry agent, while specialist agents are invoked behind the scenes as tool calls (`src/agency_swarm/tools/send_message.py:312-533`).

## 2. Agent Framework & Architecture

This repo is **not LangGraph/CrewAI/AutoGen**; it is a **custom orchestration layer over OpenAI’s `openai-agents` SDK**. Evidence: dependency `openai-agents==0.9.3` (`pyproject.toml:16-19`), and core imports from `agents` across runtime (`src/agency_swarm/agent/core.py:6-15`, `src/agency_swarm/agency/core.py:10-11`).

Architecture-wise, `Agency` is the top-level coordinator that registers agents, parses communication flows, and initializes per-agent runtime state (`src/agency_swarm/agency/core.py:80-200`, `src/agency_swarm/agency/setup.py:27-124`, `265-269`). Each `Agent` extends `agents.Agent` and delegates actual LLM execution to an internal `Execution` handler while adding framework-specific features (file manager, guardrails wrapping, MCP conversion, runtime send-message tools) (`src/agency_swarm/agent/core.py:63-76`, `230-267`, `377-471`).

The “intelligence routing” mostly lives in:
- prompts/instructions per agent (`examples/multi_agent_workflow.py:85-120`);
- explicit communication graph definitions (`agent1 > agent2` style) parsed into allowed sender→receiver edges (`src/agency_swarm/agency/setup.py:27-93`);
- dynamic inter-agent tool invocation (`SendMessage.on_invoke_tool`) that performs synchronous sub-agent calls and merges results (`src/agency_swarm/tools/send_message.py:312-533`).

## 3. Orchestration Pattern

Closest pattern: **hierarchical manager-worker workflow** with explicit directed edges, plus tool-mediated delegation.

Why:
- Communication is predefined as sender→recipient routes (`communication_flows`), not free swarm chatter (`src/agency_swarm/agency/setup.py:185-213`).
- A sender agent calls a generated `send_message` tool, which executes the recipient agent and returns its output synchronously (`src/agency_swarm/tools/send_message.py:40-49`, `389-405`, `494-505`).

Control flow excerpt 1 (`src/agency_swarm/agency/setup.py:245-253`):
```python
chosen_tool_class = effective_tool_class or SendMessage
...
agent_instance.register_subagent(
    recipient_agent,
    send_message_tool_class=chosen_tool_class,
    runtime_state=runtime_state,
)
```

Control flow excerpt 2 (`src/agency_swarm/tools/send_message.py:499-505`):
```python
response = await self.recipient_agent.get_response(
    message=message_content,
    sender_name=self.sender_agent.name,
    additional_instructions=additional_instructions or None,
    agency_context=recipient_agency_context,
    parent_run_id=tool_call_id,
)
```

## 4. Tools & External Integrations

- **OpenAI Agents SDK tools** (WebSearch, FileSearch, CodeInterpreter, Computer, LocalShell, image generation, Hosted MCP) are re-exported and wired through the framework (`src/agency_swarm/tools/__init__.py:1-18`, `57-88`).
- **Inter-agent delegation tools**: custom `SendMessage` and `Handoff` abstractions for agent-to-agent calls (`src/agency_swarm/tools/send_message.py:38-49`, `564-635`).
- **MCP servers**: persistent MCP manager, loop-affine proxying, conversion from MCP servers to callable tools (`src/agency_swarm/tools/mcp_manager.py:14-19`, `327-360`, `402-434`).
- **OpenAPI/custom HTTP tool import** via `ToolFactory` utilities and schema importer/exporter (`src/agency_swarm/tools/tool_factory_utils/openapi_importer.py:24-104`, `openapi_exporter.py:40-94`).
- **File + vector store RAG plumbing** with OpenAI files/vector stores and automatic `FileSearchTool`/`CodeInterpreterTool` setup (`src/agency_swarm/agent/file_manager.py:212-287`, `295-367`).
- **Shell/terminal execution** via built-in persistent shell tool (`src/agency_swarm/tools/built_in/PersistentShellTool.py:11-18`, `48-66`).
- **FastAPI serving + OpenClaw gateway proxy** for responses API compatibility (`src/agency_swarm/integrations/openclaw.py:1111-1201`, `1204-1265`).

## 5. Notable Code Walkthrough

- `src/agency_swarm/agency/core.py:80-200` - Constructs the agency graph, registers agents/entry points, initializes runtime state, and applies shared resources; this is the root orchestration container.
- `src/agency_swarm/agency/setup.py:27-124` - Parses communication flow declarations (including `agent1 > agent2` chains) into concrete directed edges and optional per-edge tool classes.
- `src/agency_swarm/tools/send_message.py:312-533` - Core delegation engine: validates recipient, prevents concurrent duplicate sends, executes recipient agent (streaming or non-streaming), and returns delegated output.
- `src/agency_swarm/agent/core.py:243-267` - Agent initialization pipeline that loads tools/schemas/files/MCP wiring and applies guardrail/tool wrappers before runtime use.
- `src/agency_swarm/agent/file_manager.py:212-317` - RAG-oriented file ingestion: auto-create/reuse vector stores, upload files, and attach `FileSearchTool` for retrieval-enabled agent behavior.

## 6. Use-Case Mapping

Although the repository can support code-producing agents, the primary implementation emphasis is broader **multi-agent workflow orchestration** rather than a dedicated code-generation system. The architecture centers on defining role-based agents, controlling delegation edges, and coordinating specialized tools/services (`src/agency_swarm/agency/setup.py:178-263`, `examples/multi_agent_workflow.py:8-15`, `124-131`). So the upstream assignment “Code Generation” is only partially true; the better category is **Workflow Automation** because the framework is domain-agnostic and mainly automates structured multi-step, multi-agent task flows.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Explicit, auditable agent communication graph instead of implicit hidden routing (`src/agency_swarm/agency/setup.py:185-213`).
  - Clean runtime integration with OpenAI Agents SDK primitives rather than reinventing the model loop (`src/agency_swarm/agent/core.py:63-76`, `377-425`).
  - Strong integration surface: MCP, OpenAPI-imported tools, file/vector-store retrieval, FastAPI deployment (`src/agency_swarm/tools/mcp_manager.py:402-434`, `agent/file_manager.py:212-317`).
  - Delegation supports both streaming and non-streaming sub-calls with merged event/result handling (`src/agency_swarm/tools/send_message.py:400-493`).
  - Practical developer UX via templates, examples, CLI, and visualization/TUI hooks (`src/agency_swarm/cli/main.py:12-33`, `examples/multi_agent_workflow.py:14-15`).

- **Limitations:**
  - Routing is mostly static edge configuration; there is no sophisticated learned planner or graph-state policy engine like LangGraph-style conditional state transitions.
  - Heavy coupling to OpenAI ecosystem/tool semantics (OpenAI files/vector stores/responses models), which may reduce backend portability (`agent/file_manager.py:106-170`, `integrations/openclaw_model.py` usage patterns).
  - Complexity is spread across many integration layers (FastAPI, MCP persistence, OpenClaw proxy), increasing operational/debug burden.
  - Safety/quality of cross-agent decomposition largely depends on prompt design; no central symbolic task planner or verifier loop is apparent.
  - Some advanced integrations (OpenClaw, optional deps) introduce extra runtime prerequisites and environment sensitivity (`src/agency_swarm/integrations/openclaw.py:464-541`).

- **Research relevance:**
  - Evidence of a production-oriented **manager-worker MAS pattern** implemented through tool-based delegation.
  - Useful case study of **typed tool mediation** and constrained inter-agent communication channels.
  - Demonstrates practical **MAS + external tool ecosystem** integration (MCP, retrieval, shell, HTTP).
  - Illustrates how modern LLM orchestration frameworks build on a vendor SDK while adding policy/runtime layers.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
