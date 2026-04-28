---
repo_name: imran-siddique/agent-os
url: "https://github.com/imran-siddique/agent-os"
stars: 69
forks: 20
contributors_count: 16
last_commit_date: "2026-03-03T17:48:03+00:00"
primary_use_case: Simulation
user_tier: Niche
total_score: 3
architecture_labels: [LangGraph, LangChain, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T17:10:48.154976+00:00"
model: auto
duration_s: 90.9
clone_size_kb: 17315
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`agent-os` is a governance kernel for AI agents rather than a single end-user agent app. In practice, users run it by wrapping existing agent runtimes (e.g., OpenAI Assistants, AutoGen, CrewAI, LangChain) or by calling the stateless kernel API (`StatelessKernel.execute`) and optional HTTP/MCP servers. What they get is policy-enforced execution: tool calls, messages, and actions are checked against allow/deny rules, token/tool budgets, and blocked patterns before or during execution. The repo also includes infrastructure for audit logging, MCP exposure, and inter-agent components (message bus, trust protocol, “face/hands” handshake). So the core deliverable is controlled agent execution workflows, not a domain simulator.

## 2. Agent Framework & Architecture

Framework usage is **custom core + adapters**. The main runtime logic is in custom code (`src/agent_os/stateless.py`, `src/agent_os/integrations/base.py`), while framework-specific wrappers exist for external ecosystems (e.g., `LangChainKernel`, `AutoGenKernel`, `CrewAIKernel`, `OpenAIKernel`, `OpenAIAgentsKernel`) in `src/agent_os/integrations/*.py`. I did not find LangGraph graph definitions or a native LangGraph state machine implementation in this repo.

High-level architecture: a governance layer intercepts calls around host agents/chains. In `BaseIntegration`, `pre_execute()` and `post_execute()` enforce limits and emit governance events (`src/agent_os/integrations/base.py:848-959`). Adapters then monkey-patch or proxy framework methods (e.g., AutoGen’s `initiate_chat/generate_reply/receive`, CrewAI kickoff/tool execution, OpenAI run lifecycle) to route control through that governance layer (`src/agent_os/integrations/autogen_adapter.py:77-276`, `src/agent_os/integrations/crewai_adapter.py:68-193`, `src/agent_os/integrations/openai_adapter.py:448-665`).

There are also multi-agent-oriented subsystems: AMB message bus (`modules/amb/amb_core/bus.py`) and a “Mute Agent” split between reasoning and execution roles coordinated by a handshake protocol (`modules/mute-agent/mute_agent/core/reasoning_agent.py`, `.../execution_agent.py`, `.../handshake_protocol.py`). This puts the “intelligence” mostly in policy/interception logic and role protocol, not in centralized planner prompts.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with governance wrappers**.

The clearest native orchestration is in Mute Agent’s Face/Hands pattern: Reasoning proposes, protocol validates, Execution executes only accepted proposals (`modules/mute-agent/mute_agent/core/handshake_protocol.py:71-125`, `.../execution_agent.py:34-89`). That is a constrained manager-worker flow.

```python
# modules/mute-agent/mute_agent/core/handshake_protocol.py:71-79
def initiate_handshake(self, proposal: ActionProposal) -> HandshakeSession:
    session_id = self._generate_session_id()
    session = HandshakeSession(
        session_id=session_id,
        state=HandshakeState.INITIATED,
        proposal=proposal
    )
```

```python
# modules/mute-agent/mute_agent/core/execution_agent.py:44-58
if session.state != HandshakeState.ACCEPTED:
    raise ValueError(...)
self.protocol.start_execution(session_id)
result = self._execute_action(
    session.proposal.action_id,
    session.proposal.parameters,
    session.proposal.context
)
```

Separately, adapter-level orchestration wraps existing framework control flow, e.g., AutoGen multi-agent conversations are intercepted at each hop (`src/agent_os/integrations/autogen_adapter.py:117-223`), but Agent OS itself is not a peer-to-peer swarm runtime.

## 4. Tools & External Integrations

- **OpenAI Assistants API**: governed assistant/thread/run lifecycle, tool-call handling, token budget enforcement in `src/agent_os/integrations/openai_adapter.py:129-665`.
- **OpenAI Agents SDK**: wrapped runner + tool guards + guardrail object in `src/agent_os/integrations/openai_agents_sdk.py:106-350`.
- **LangChain**: wrapper for `invoke/ainvoke/run/batch/stream` in `src/agent_os/integrations/langchain_adapter.py:26-305`.
- **AutoGen**: monkey-patches multi-agent chat methods in `src/agent_os/integrations/autogen_adapter.py:77-276`.
- **CrewAI**: wraps crew kickoff, agent task execution, and individual tool `_run` calls in `src/agent_os/integrations/crewai_adapter.py:48-193`.
- **MCP protocol/server**: tool/resource/prompt endpoints via MCP server in `modules/mcp-kernel-server/src/mcp_kernel_server/server.py:160-499`.
- **MCP security gateway**: tool allow/deny lists, pattern sanitization, approval workflow, rate limiting in `src/agent_os/mcp_gateway.py:85-295`.
- **FastAPI service**: governance API endpoints (`/execute`, injection detection, metrics) in `src/agent_os/server/app.py:78-274`.
- **State backends**: in-memory and Redis for stateless kernel context/state in `src/agent_os/stateless.py:124-271`.
- **Inter-agent message bus**: pub/sub, request/reply, DLQ, persistence in `modules/amb/amb_core/bus.py:15-476`.

## 5. Notable Code Walkthrough

- `src/agent_os/integrations/base.py:62-1010` — Defines core governance primitives (`GovernancePolicy`, `ExecutionContext`, interceptors, pre/post checks, drift detection). This is the policy engine used by most adapters.
- `src/agent_os/integrations/autogen_adapter.py:77-325` — Shows concrete multi-agent interception by wrapping AutoGen conversation methods across multiple agents, making it central evidence for runtime MAS governance.
- `src/agent_os/integrations/openai_adapter.py:448-665` — Implements governed OpenAI Assistant runs, including tool-call budget checks and cancellation (`SIGKILL`-style) on violations.
- `modules/mute-agent/mute_agent/core/reasoning_agent.py:61-179` — Encodes the “Reasoning Agent” that proposes actions and validates them against graph constraints before execution.
- `modules/mute-agent/mute_agent/core/handshake_protocol.py:58-199` — Implements explicit negotiation state transitions (`INITIATED -> VALIDATED -> ACCEPTED -> EXECUTING -> COMPLETED/FAILED`), giving the repo a structured hierarchical control protocol.

## 6. Use-Case Mapping

The upstream label **Simulation** is only partially supported. There is a simulation-oriented component (`modules/scak/agent_kernel/simulator.py:153-447`) with shadow/counterfactual path simulation, but the dominant codebase focus is governance and controlled execution of agent workflows across frameworks, APIs, and tools. Most runnable paths are policy enforcement wrappers, MCP/HTTP governance services, and safe tool orchestration. A better primary category is **Workflow Automation**: this repo operationalizes policy-constrained agent workflows rather than building simulation-first agent environments.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong cross-framework governance abstraction via shared base + adapters (`src/agent_os/integrations/base.py`, `.../autogen_adapter.py`, `.../openai_adapter.py`).
  - Practical enforcement points at runtime (tool calls, run loops, message ingress), not just prompt-level rules.
  - Broad integration surface (MCP gateway/server, FastAPI, Redis-backed stateless kernel, message bus).
  - Clear auditability and policy metadata patterns in multiple layers.

- **Limitations:**
  - Many “agentic” subsystems are governance wrappers around external frameworks, not an end-to-end native MAS planner runtime.
  - Some modules contain simulated/stubbed behavior (e.g., stateless action execution stub in `src/agent_os/stateless.py:602-615`; simulator’s mocked execution in `modules/scak/agent_kernel/simulator.py:53-131`).
  - Adapter implementations rely heavily on monkey-patching/proxy patterns, which can be brittle across upstream SDK changes.
  - Architectural sprawl: multiple partially overlapping policy/context classes across modules can complicate consistency.

- **Research relevance:**
  - Good evidence for **middleware governance patterns** for LLM agents across heterogeneous frameworks.
  - Useful case study in **policy interception + auditability** for agent tool use (OWASP-style controls).
  - Demonstrates a **hierarchical dual-agent protocol** (reasoning vs execution) with explicit handshake states.
  - Illustrates practical tradeoffs between generic governance kernels and framework-specific adapters.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
