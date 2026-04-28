---
repo_name: kagent-dev/kagent
url: "https://github.com/kagent-dev/kagent"
stars: 2622
forks: 523
contributors_count: 127
last_commit_date: "2026-04-22T21:08:15+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 6
architecture_labels: [AutoGen, CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T12:38:53.376108+00:00"
model: auto
duration_s: 87.8
clone_size_kb: 14370
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`kagent` is a Kubernetes-native platform for deploying and operating AI agents behind a unified Agent-to-Agent (A2A) API, with a Go control plane plus Python runtimes. A user typically creates an Agent CRD (or runs packaged sample agents), and the system exposes runnable agent endpoints while persisting sessions, tasks, and execution state. The repository is not a single bot implementation; it is an orchestration layer that supports multiple agent engines (Google ADK, LangGraph, CrewAI, OpenAI Agents SDK) behind consistent server contracts. In practice, users get managed agent execution with tool integration (MCP, remote subagents, memory, approvals/HITL), plus Kubernetes deployment and UI/API surfaces (`go/core/internal/httpserver/server.go:25-313`, `python/packages/kagent-adk/src/kagent/adk/cli.py:53-210`).

## 2. Agent Framework & Architecture

The upstream “AutoGen/CrewAI” label is incomplete. The code clearly shows a **multi-runtime architecture** using:
- **Google ADK** (`google.adk.*`) in `kagent-adk` (`python/packages/kagent-adk/src/kagent/adk/_a2a.py:15-34`, `_agent_executor.py:24-36`)
- **LangGraph** in `kagent-langgraph` (`python/packages/kagent-langgraph/src/kagent/langgraph/_executor.py:61-64`)
- **CrewAI** in `kagent-crewai` (`python/packages/kagent-crewai/src/kagent/crewai/_executor.py:33-35`)
- **OpenAI Agents SDK** in `kagent-openai` (`python/packages/kagent-openai/src/kagent/openai/_agent_executor.py:42-44`)
- all confirmed by package dependencies (`python/packages/kagent-*/pyproject.toml`).

High-level architecture: the Go server provides API routes, persistence, and routing (`/api/a2a`, `/api/langgraph/checkpoints`, `/api/crewai/*`) while Python executors run agent logic and emit A2A task events (`go/core/internal/httpserver/server.go:286-301`). “Intelligence” lives in the selected runtime’s agent/graph/crew definitions plus model/tool config generated into `AgentConfig` (`python/packages/kagent-adk/src/kagent/adk/types.py:283-433`).  

This repo supports both single-agent and multi-agent execution; multi-agent behavior appears in CrewAI crews (multiple roles/tasks) and ADK remote-agent tool chaining (an agent can call another agent as a tool with HITL propagation) (`python/samples/crewai/research-crew/src/research_crew/crew.py:17-55`, `python/packages/kagent-adk/src/kagent/adk/_remote_a2a_tool.py:133-421`).

## 3. Orchestration Pattern

Closest fit: **hierarchical (manager-worker) with event-driven state updates**.

- In ADK mode, a parent agent can invoke remote subagents as tools (`remote_agents`), forwarding approvals/rejections and resuming child tasks. That is manager→subagent orchestration (`python/packages/kagent-adk/src/kagent/adk/types.py:336-405`, `_remote_a2a_tool.py:209-421`).
- In CrewAI mode, multiple role agents execute task pipelines (`Process.sequential`), i.e., coordinated multi-agent workflow (`python/samples/crewai/research-crew/src/research_crew/crew.py:45-52`).
- Control/status is event-driven through A2A task events (`submitted/working/input_required/completed/failed`) in all executors.

```356:374:python/packages/kagent-adk/src/kagent/adk/types.py
if self.remote_agents:
    for remote_agent in self.remote_agents:
        ...
        tools.append(
            KAgentRemoteA2AToolset(
                name=remote_agent.name,
                description=remote_agent.description,
                agent_card_url=f"{remote_agent.url}{AGENT_CARD_WELL_KNOWN_PATH}",
                httpx_client=client,
            )
        )
```

```263:276:python/packages/kagent-adk/src/kagent/adk/_remote_a2a_tool.py
if state == TaskState.input_required:
    return self._handle_input_required(task, tool_context)

if state == TaskState.failed:
    error_text = _extract_text_from_task(task)
    return error_text or f"Remote agent '{self.name}' failed."
```

## 4. Tools & External Integrations

- **MCP tool servers (HTTP/SSE)**: agent config maps MCP endpoints into ADK toolsets, with header forwarding and per-tool approval lists (`python/packages/kagent-adk/src/kagent/adk/types.py:143-155`, `:304-335`).
- **Remote A2A subagents**: other agents become callable tools; includes session continuity, user propagation, and HITL resume (`python/packages/kagent-adk/src/kagent/adk/_remote_a2a_tool.py:133-193`, `:317-421`).
- **Model providers**: OpenAI, Azure OpenAI, Anthropic, Gemini, Ollama, Bedrock, SAP AI Core wired in model factory (`python/packages/kagent-adk/src/kagent/adk/types.py:491-586`).
- **Code execution tooling**: optional sandboxed local code execution (`execute_code`) via `SandboxedLocalCodeExecutor` (`python/packages/kagent-adk/src/kagent/adk/types.py:24`, `:407`).
- **Memory services**: ADK memory tools and auto-save callbacks; CrewAI long-term memory backed by Go API (`python/packages/kagent-adk/src/kagent/adk/types.py:429-488`, `python/packages/kagent-crewai/src/kagent/crewai/_memory.py`, `go/core/internal/httpserver/handlers/crewai.go:50-300`).
- **LangGraph persistence**: checkpoints/writes persisted through Go endpoints (`go/core/internal/httpserver/handlers/checkpoints.go:71-282`).
- **External search/web tools in examples**: CrewAI sample uses `SerperDevTool` for web search (`python/samples/crewai/research-crew/src/research_crew/crew.py:7`, `:22`).

## 5. Notable Code Walkthrough

- `python/packages/kagent-adk/src/kagent/adk/types.py:283-433`  
  Central runtime config schema; builds ADK agent with MCP tools, remote-agent tools, approvals, ask-user tool, optional code executor, and memory wiring. This is the main “assembly point” for agent capabilities.

- `python/packages/kagent-adk/src/kagent/adk/_agent_executor.py:96-279`  
  Core A2A executor for ADK agents: per-request runner lifecycle, event conversion, streaming task status/artifact publishing, and cleanup logic for MCP sessions.

- `python/packages/kagent-adk/src/kagent/adk/_remote_a2a_tool.py:209-421`  
  Implements subagent-as-tool execution with two-phase HITL (initial call + resume), enabling parent/child agent coordination at runtime.

- `python/packages/kagent-langgraph/src/kagent/langgraph/_executor.py:136-227`  
  Streams LangGraph events into A2A updates, aggregates outputs, and handles interrupt/resume for approvals using `Command(resume=...)`.

- `go/core/internal/httpserver/server.go:286-301`  
  Exposes backend APIs that make these runtimes stateful in production (`/api/langgraph/checkpoints`, `/api/crewai/*`, `/api/a2a/*`), tying Kubernetes/control-plane persistence to runtime agents.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. This repo is built to automate multi-step operational workflows by orchestrating agents, tools, memory, and subagent delegation behind a stable API and Kubernetes control plane. Concrete automation patterns include sequential CrewAI task pipelines (`researcher` → `analyst`), graph-based step execution with resumable interrupts in LangGraph, and parent-agent delegation to remote A2A subagents with approval gates (`python/samples/crewai/research-crew/src/research_crew/crew.py:45-52`, `python/packages/kagent-langgraph/src/kagent/langgraph/_executor.py:345-464`, `python/packages/kagent-adk/src/kagent/adk/_remote_a2a_tool.py:317-421`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Multi-framework interoperability (ADK, LangGraph, CrewAI, OpenAI Agents) under one A2A contract.
  - Strong human-in-the-loop semantics across direct tools and nested subagents.
  - Practical production concerns addressed: session/task persistence, tracing, auth propagation, cleanup robustness.
  - Native tool extensibility via MCP and remote agents; supports composable agent ecosystems.
  - Kubernetes-first deployment model suitable for enterprise workflow automation.

- **Limitations:**
  - Architectural complexity is high; behavior differs by runtime package, increasing integration/testing burden.
  - Cancellation is explicitly unimplemented in multiple executors (`NotImplementedError`).
  - Multi-agent capability is partly configuration/sample-driven rather than one unified planner runtime.
  - Error handling has many transport/runtime-specific branches, suggesting fragile edges across dependencies.
  - Cross-runtime semantics (e.g., memory/checkpoint behavior) are not perfectly uniform.

- **Research relevance:**
  - Evidence of real-world hierarchical multi-agent orchestration with nested HITL control loops.
  - Useful case for studying protocol-level standardization (A2A) across heterogeneous agent frameworks.
  - Demonstrates production integration of MCP tools with resilience patterns (connection-safe wrappers).
  - Illustrates how stateful workflow automation combines LLM reasoning with durable backend state.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
