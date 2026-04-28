---
repo_name: anthropics/claude-cookbooks
url: "https://github.com/anthropics/claude-cookbooks"
stars: 41368
forks: 4596
contributors_count: 73
last_commit_date: "2026-04-11T00:33:35+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [RAG + Agents]
generated_at: "2026-04-27T10:22:34.441865+00:00"
model: auto
duration_s: 102.6
clone_size_kb: 360044
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`anthropics/claude-cookbooks` is a large collection of runnable notebooks and helper modules that demonstrate how to build Claude-powered applications, including managed agents, tool-using agents, and RAG pipelines. In practice, users run notebooks (especially under `managed_agents/`, `claude_agent_sdk/`, and `patterns/agents/`) to create agents, attach tools/resources, stream execution events, and iterate on workflows like incident response, issue-to-PR automation, or data analysis report generation. The output is usually a completed workflow artifact (e.g., fixes, PR actions, reports, postmortems) plus an event trace showing agent decisions/tool calls. This is not a single production app; it is a cookbook of reference implementations and patterns.

## 2. Agent Framework & Architecture

The codebase is **not** built on CrewAI/LangGraph/AutoGen/LangChain orchestration frameworks in its core implementations. The active runtime patterns are primarily:
- Anthropic APIs (`client.beta.agents.create`, `client.beta.sessions.*`) in `managed_agents/*.ipynb`
- Anthropic’s Python **Claude Agent SDK** (`ClaudeAgentOptions`, `ClaudeSDKClient`) in `claude_agent_sdk/*`
- Lightweight custom orchestration logic in notebook code (`patterns/agents/orchestrator_workers.ipynb` + `patterns/agents/util.py`)

Architecture is mostly “agent configured with tools + session event loop.” For managed agents, notebooks define an agent, create a session/environment, send user events, and consume streaming events until `session.status_idle` (`managed_agents/utilities.py:47-73`, `managed_agents/CMA_iterate_fix_failing_tests.ipynb:188-217`). Intelligence lives in prompts/system instructions, tool schemas, and control-loop logic (especially `requires_action` handling for custom tools) rather than in a graph engine.

Where multi-agent behavior appears, it is explicit manager/delegation style: e.g., the Chief of Staff setup enables `Task` delegation to subagents via project settings (`claude_agent_sdk/chief_of_staff_agent/agent.py:85-107`) and subagent specs in `.claude/agents/*.md` (`financial-analyst`, `recruiter`). Separately, `patterns/agents/orchestrator_workers.ipynb` implements an orchestrator-worker decomposition where one LLM creates subtasks and worker LLM calls execute them.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)**, with some sequential workflow loops.

- In the Chief-of-Staff example, the top-level agent acts as manager and can delegate to specialized subagents through `Task`:
  
```85:94:claude_agent_sdk/chief_of_staff_agent/agent.py
options = ClaudeAgentOptions(
    model="claude-opus-4-6",
    allowed_tools=[
        "Task",  # enables subagent delegation
        "Read",
        "Write",
        "Edit",
        "Bash",
        "WebSearch",
    ],
```

- In managed-agent notebooks, control is event-driven sequential execution: stream events, inspect stop reason, and branch when human/custom-tool action is required (`requires_action`) before resuming (`managed_agents/sre_incident_responder.ipynb:509-545`, `managed_agents/CMA_gate_human_in_the_loop.ipynb:206-266`).

- In the orchestrator-workers pattern, the orchestrator generates task XML, then worker calls are executed over parsed tasks (`patterns/agents/orchestrator_workers.ipynb:157-200`), i.e., manager plans then workers execute (the notebook itself notes workers are sequential in this implementation).

## 4. Tools & External Integrations

- **Anthropic Managed Agents runtime** (`managed_agents/*.ipynb`): `agents.create`, `sessions.create`, `sessions.events.stream/list/send`, `sessions.resources.add` wire core orchestration and resource injection.
- **Claude Agent SDK tools** (`claude_agent_sdk/*/agent.py`): `allowed_tools` include built-ins like `WebSearch`, `Read`, `Bash`, `Write`, `Edit`, `Task`.
- **MCP servers (Model Context Protocol)**:
  - GitHub MCP via Docker in observability agent (`claude_agent_sdk/observability_agent/agent.py:40-64`, `:106-121`)
  - Custom SRE MCP server implementing JSON-RPC `tools/list` and `tools/call` (`claude_agent_sdk/site_reliability_agent/sre_mcp_server.py:57-113`, `:2658-2687`)
- **Infrastructure/ops integrations** in SRE MCP server:
  - Prometheus via HTTP queries (`sre_mcp_server.py:629-717`, `:772-914`)
  - Docker/docker-compose command execution (allowlisted) (`sre_mcp_server.py:2321-2407`, `:2425-2494`)
  - Config file read/edit tools (`sre_mcp_server.py:2214-2314`)
- **Incident-management APIs** (conditional):
  - PagerDuty REST integration (`sre_mcp_server.py:1574-1855`)
  - Confluence REST integration (`sre_mcp_server.py:1958-2208`)
- **RAG/vector integrations** exist in separate cookbooks (e.g., Pinecone, MongoDB, LlamaIndex notebooks under `third_party/`), but they are examples rather than one unified agent runtime.

## 5. Notable Code Walkthrough

- `claude_agent_sdk/chief_of_staff_agent/agent.py:41-129`  
  Wraps a full SDK agent turn with configurable permission mode, filesystem-backed settings, and `Task` delegation support; this is the clearest runtime multi-agent entrypoint in Python code.

- `claude_agent_sdk/chief_of_staff_agent/.claude/agents/financial-analyst.md:1-82` and `.../recruiter.md:1-89`  
  Define specialized subagent roles, tool permissions, and domain instructions used by the manager agent for delegated analysis.

- `managed_agents/utilities.py:47-73`  
  Canonical event-stream loop used across managed-agent notebooks: prints tool usage and exits on `session.status_idle` with `end_turn`; foundational for orchestrating long-running sessions.

- `managed_agents/sre_incident_responder.ipynb:509-545`  
  Shows the critical `requires_action` custom-tool roundtrip: detect custom tool event IDs, run external logic/human gate, send `user.custom_tool_result`, resume run.

- `claude_agent_sdk/site_reliability_agent/sre_mcp_server.py:2547-2641` and `:2658-2687`  
  Implements MCP tool routing and JSON-RPC server loop; this is the bridge that turns external systems (metrics, shell, PagerDuty/Confluence) into callable agent tools.

## 6. Use-Case Mapping

The assigned label **RAG + Agents** is only partially accurate for this repository as a whole. There are RAG-focused notebooks (e.g., `capabilities/retrieval_augmented_generation/`, Pinecone/MongoDB/LlamaIndex examples), but the strongest and most complete multi-agent implementations are workflow-centric: incident response, issue-to-PR orchestration, human approval gates, and delegated specialist subagents (`managed_agents/*`, `claude_agent_sdk/chief_of_staff_agent/*`). So for this repo’s agentic core behavior, **Workflow Automation** is the better primary category.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Real, inspectable runtime loops (session events, custom tool handoffs, MCP calls), not just conceptual diagrams.
  - Strong coverage of operational patterns: HITL gating, approval pauses, rollback/versioning, observability.
  - Demonstrates both hosted managed-agent APIs and local SDK orchestration, useful for comparative study.
  - External tool integration is concrete and broad (GitHub MCP, Prometheus, Docker, PagerDuty, Confluence).
  - Includes role-specialized subagent configs and manager delegation in a reproducible setup.

- **Limitations:**
  - Implementations are spread across notebooks, making large-scale static analysis and reuse harder than a cohesive package.
  - Multi-agent coordination is demonstrated in select areas; much of the repo is single-agent or capability-specific recipes.
  - Some “orchestrator-workers” code is illustrative and sequential rather than production-grade parallel scheduling.
  - Evaluation/benchmarking of multi-agent quality is limited; mostly tutorial success-path demonstrations.
  - Architecture consistency varies across subdirectories (managed API style vs SDK style vs notebook-only prototypes).

- **Research relevance:**
  - Evidence for practical **manager-worker** LLM orchestration with explicit delegation and specialized roles.
  - Evidence for **human-in-the-loop interrupt/resume** control in agent runs (`requires_action` pattern).
  - Evidence for **tool-augmented autonomous workflows** where LLMs operate over real external systems via MCP.
  - Useful case study of how prompt/instruction artifacts (`.claude/agents`, system prompts, hooks) shape agent behavior.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
