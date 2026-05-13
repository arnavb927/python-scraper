---
repo_name: HKUDS/DeepTutor
url: "https://github.com/HKUDS/DeepTutor"
stars: 21038
forks: 2840
contributors_count: 50
last_commit_date: "2026-04-22T12:56:43+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:46:24.422775+00:00"
model: auto
duration_s: 104.6
clone_size_kb: 22560
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`DeepTutor` is an agent-native tutoring system that users can run through a CLI (`deeptutor run ...`, `deeptutor chat`), a unified WebSocket endpoint (`/api/v1/ws`), or SDK-style runtime entry points. In practice, a user asks for chat help, step-by-step problem solving, or quiz generation, and the system routes that request into a capability-specific multi-stage pipeline. The codebase combines LLM orchestration, tool-calling, retrieval over knowledge bases, and streaming event output so responses are traceable in phases (thinking/acting/writing/etc.). Beyond the core tutor flow, it also includes a “TutorBot” runtime with shell/filesystem/web/MCP tools and team/subagent patterns for broader automation tasks.

## 2. Agent Framework & Architecture

The repository is **custom agent architecture**, not LangGraph/CrewAI/AutoGen/LangChain orchestration. I found no framework imports for those stacks, while core orchestration is implemented in first-party classes such as `ChatOrchestrator`, `BaseCapability`, and registry-driven tool/capability loading (`deeptutor/runtime/orchestrator.py:26-144`, `deeptutor/core/capability_protocol.py:33-69`, `deeptutor/runtime/registry/*.py`). LLM access is mostly via OpenAI-compatible clients and internal service wrappers (`deeptutor/agents/chat/agentic_pipeline.py:13-35`).

High-level architecture is two-layer:  
- **Level 1 tools** (RAG, web search, code execution, reason, brainstorm, etc.) registered in a `ToolRegistry` and exposed as function schemas (`deeptutor/runtime/registry/tool_registry.py:21-149`, `deeptutor/tools/builtin/__init__.py:503-521`).  
- **Level 2 capabilities** (chat, deep_solve, deep_question, etc.) that execute multi-step workflows and stream structured events (`deeptutor/runtime/orchestrator.py:36-112`, `deeptutor/capabilities/deep_solve.py:26-291`, `deeptutor/capabilities/deep_question.py:23-194`).

“Intelligence” lives in a mix of role-specific agent classes, stage-specific prompts, and runtime routing logic. Example: `deep_solve` explicitly composes `PlannerAgent -> SolverAgent (ReAct loops) -> WriterAgent` with optional replanning (`deeptutor/agents/solve/main_solver.py:33-688`), while chat uses a 4-stage loop (`thinking/acting/observing/responding`) with native tool-calling or ReAct fallback (`deeptutor/agents/chat/agentic_pipeline.py:164-959`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with staged sequential pipelines**, plus event-streaming.  
- `ChatOrchestrator` acts as top-level manager selecting a capability and handling lifecycle/events.  
- Each capability then runs an internal pipeline (often with multiple role agents).

Control flow example (capability routing):

```36:56:deeptutor/runtime/orchestrator.py
async def handle(self, context: UnifiedContext) -> AsyncIterator[StreamEvent]:
    ...
    cap_name = context.active_capability or "chat"
    capability = self._cap_registry.get(cap_name)
```

Control flow example (manager-worker solve pipeline):

```243:269:deeptutor/agents/solve/main_solver.py
self.planner_agent = PlannerAgent(...)
self.solver_agent = SolverAgent(...)
self.writer_agent = WriterAgent(...)
...
plan = await self.planner_agent.process(...)
...
decision = await self.solver_agent.process(...)
...
final_answer = await self.writer_agent.process(...)
```

This is not a graph/state-machine DSL (LangGraph-style), and not peer swarm; it is explicit Python-controlled stage progression with optional loops/replans.

## 4. Tools & External Integrations

- **LLM Providers (OpenAI-compatible, Azure OpenAI, etc.)**: chat pipeline builds `AsyncOpenAI`/`AsyncAzureOpenAI` clients and uses internal LLM streaming wrappers (`deeptutor/agents/chat/agentic_pipeline.py:12-14`, `1025-1044`).
- **RAG / Vector retrieval (LlamaIndex)**: tool wrapper delegates to `RAGService`, and concrete pipeline uses `llama_index` storage/retrieval (`deeptutor/tools/rag_tool.py:39-83`, `deeptutor/services/rag/pipelines/llamaindex/pipeline.py:37-223`).
- **Web search APIs**: provider-backed search abstraction (Brave, Tavily, Jina, SearxNG, DuckDuckGo, Perplexity) via services layer (`deeptutor/tools/web_search.py:20-46`).
- **Code execution sandbox**: `code_execution` tool generates/runs Python code and returns stdout/stderr/artifacts (`deeptutor/tools/builtin/__init__.py:145-233`).
- **arXiv integration**: `paper_search` tool (`deeptutor/tools/builtin/__init__.py:311-388`).
- **TutorBot shell/filesystem/web automation**: base toolset includes read/write/edit/list dir, shell `exec`, web search/fetch (`deeptutor/tutorbot/agent/tools/registry.py:79-110`, `deeptutor/tutorbot/agent/tools/shell.py:14-187`).
- **MCP servers**: dynamic MCP connection and tool wrapping for stdio/SSE/streamable HTTP transports (`deeptutor/tutorbot/agent/tools/mcp.py:74-186`, `deeptutor/tutorbot/agent/loop.py:196-218`).
- **WebSocket runtime streaming**: unified turn/session subscriptions, cancellation, regeneration (`deeptutor/api/routers/unified_ws.py:37-210`).

## 5. Notable Code Walkthrough

- `deeptutor/runtime/orchestrator.py:26-144` - Central turn router; selects capability (`chat` default), runs it, emits stream events, and publishes completion events. This is the runtime entry hub for CLI/WebSocket/API flows.
- `deeptutor/agents/chat/agentic_pipeline.py:164-959` - Core “agentic chat” implementation with explicit thinking/acting/observing/responding stages, optional native function-calling, parallel tool execution (`asyncio.gather`), and fallback ReAct behavior.
- `deeptutor/agents/solve/main_solver.py:33-688` - Canonical multi-agent controller for plan-react-write; coordinates three specialized agents, step loops, replanning, and tool execution traces.
- `deeptutor/agents/question/coordinator.py:28-469` - Question-generation coordinator that batches ideation templates then runs generation per template, with websocket-friendly progress events.
- `deeptutor/tutorbot/agent/loop.py:36-317` - General-purpose autonomous loop for TutorBot: iteratively calls LLM, executes tool calls, supports team/subagent tools, and handles session-level runtime behavior.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only **partially** accurate. The TutorBot subsystem clearly supports terminal-style and automation behavior via shell/filesystem/web/MCP tools (`deeptutor/tutorbot/agent/tools/registry.py:79-110`, `shell.py:14-187`), so that capability exists.

However, the repository’s dominant core is an educational multi-agent workflow engine (chat tutoring, deep solve, deep question) with staged orchestration and RAG support (`deeptutor/runtime/orchestrator.py`, `deeptutor/capabilities/deep_solve.py`, `deeptutor/capabilities/deep_question.py`). Based on code emphasis, **Workflow Automation** is the better top-level category, with strong secondary fit to **RAG + Agents**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear two-level agent architecture (tools vs capabilities) with explicit registries and manifests.
  - Multiple concrete coordinated-agent pipelines (e.g., planner/solver/writer; ideation/generation).
  - Strong runtime observability: staged streaming events, trace metadata, tool-call lifecycle hooks.
  - Practical extensibility: plugin loading for capabilities/tools and MCP dynamic tool import.
  - Supports both educational workflows and broader automation (TutorBot team/subagent modes).

- **Limitations:**
  - Heavy reliance on handcrafted orchestration logic; no declarative graph formalism for verification/optimization.
  - Coordination remains mostly centralized/hierarchical rather than decentralized multi-agent negotiation.
  - “Multi-agent” semantics vary by capability; some paths behave more like staged single-controller pipelines.
  - Error handling is broad in places (`except Exception`) and may hide failure specificity.
  - Tool/result truncation and prompt-template dependence can affect reproducibility across providers.

- **Research relevance:**
  - Good evidence of production-style **manager-worker LLM orchestration** in a real OSS system.
  - Illustrates how to combine **tool-augmented ReAct loops** with domain-specific staged capabilities.
  - Useful case for studying **event-stream tracing** and observability in agent runtime design.
  - Demonstrates hybrid architecture: specialized educational agents plus general automation/team agents in one platform.

## 8. Machine-readable classification

MAS_RELATED: yes  
USES_MAS: yes  
FINAL_USE_CASE: Workflow Automation
