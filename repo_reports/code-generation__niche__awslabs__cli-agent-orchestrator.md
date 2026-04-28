---
repo_name: awslabs/cli-agent-orchestrator
url: "https://github.com/awslabs/cli-agent-orchestrator"
stars: 494
forks: 91
contributors_count: 22
last_commit_date: "2026-04-22T05:37:00+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, Browser / Terminal Use]
generated_at: "2026-04-27T16:18:07.815828+00:00"
model: auto
duration_s: 93.5
clone_size_kb: 11845
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`awslabs/cli-agent-orchestrator` is a local orchestration runtime that lets a user launch one “conductor” LLM CLI agent and coordinate additional worker agents inside the same tmux-backed session. In practice, users run CLI commands like `cao launch ...`, then the active agent can call MCP tools (`handoff`, `assign`, `send_message`) to create worker terminals, delegate tasks, and collect results via inbox callbacks. The server exposes FastAPI endpoints for terminal/session lifecycle, output capture, and flow scheduling, while provider adapters normalize behavior across Codex, Claude Code, Gemini CLI, Kiro, Q CLI, etc. The result is a multi-agent automation environment for coding and other delegated workflows, not just a single chat interface.

## 2. Agent Framework & Architecture

This repo is **custom orchestration**, not LangGraph/LangChain/AutoGen/CrewAI runtime. The core imports are FastAPI + FastMCP + custom provider/service layers (`fastmcp` in `src/cli_agent_orchestrator/mcp_server/server.py:10`, provider abstractions in `src/cli_agent_orchestrator/providers/base.py:29-155`). I did not find framework-defining imports such as `langgraph`, `langchain`, `autogen`, or `crewai` in the execution path.

Architecture is centered on:
- a **server** managing sessions/terminals and message delivery (`src/cli_agent_orchestrator/api/main.py:301-577`),
- a **provider abstraction** per CLI agent runtime (`src/cli_agent_orchestrator/providers/manager.py:27-121`),
- an **MCP tool surface** that agents call at runtime to coordinate (`src/cli_agent_orchestrator/mcp_server/server.py:383-644`),
- and **agent profiles/prompts** loaded from markdown frontmatter + body (`src/cli_agent_orchestrator/utils/agent_profiles.py:142-198`).

The “intelligence” is mostly in agent prompts and role policies (e.g., `code_supervisor`, `developer`, `reviewer` in `src/cli_agent_orchestrator/agent_store/*.md`) plus tool-mediated control flow in MCP handlers. For example, `code_supervisor.md` explicitly instructs delegation loops (developer -> reviewer -> iterate), while runtime orchestration is implemented by creating child terminals, sending task payloads, and waiting for completion/callbacks (`src/cli_agent_orchestrator/mcp_server/server.py:301-377`, `486-617`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)** with **event-driven inbox delivery**.

Why hierarchical: a supervisor agent delegates to workers via MCP `assign`/`handoff`; workers either return synchronously (handoff) or callback asynchronously (send_message). Control is explicit and top-down (`src/cli_agent_orchestrator/mcp_server/server.py:302-377`, `486-517`).

```301:341:src/cli_agent_orchestrator/mcp_server/server.py
async def _handoff_impl(...):
    terminal_id, provider = _create_terminal(agent_profile, working_directory)
    ...
    _send_direct_input_handoff(terminal_id, provider, message)
    ...
    response = requests.get(
        f"{API_BASE_URL}/terminals/{terminal_id}/output", params={"mode": "last"}
    )
```

```486:517:src/cli_agent_orchestrator/mcp_server/server.py
def _assign_impl(...):
    terminal_id, _ = _create_terminal(agent_profile, working_directory)
    ...
    _send_direct_input_assign(terminal_id, message)
    return {
        "success": True,
        "terminal_id": terminal_id,
        "message": f"Task assigned to {agent_profile} (terminal: {terminal_id})",
    }
```

Why event-driven: queued inbox messages are delivered when receiver terminals become idle, detected via log-file watcher + status check (`src/cli_agent_orchestrator/services/inbox_service.py:135-170`, `75-133`).

## 4. Tools & External Integrations

- **MCP tooling (`fastmcp`)**: registers agent-callable tools `handoff`, `assign`, `send_message`, `load_skill` in `src/cli_agent_orchestrator/mcp_server/server.py:383-644`.
- **CLI LLM providers**: Codex, Claude Code, Q CLI, Kiro, Gemini, Kimi, Copilot, OpenCode are instantiated through provider manager (`src/cli_agent_orchestrator/providers/manager.py:41-116`), each with custom startup/status parsing.
- **tmux terminal automation**: all agent execution is via tmux sessions/windows, input injection, output capture (`src/cli_agent_orchestrator/services/terminal_service.py:80-214`, `288-436`; tmux client module referenced there).
- **FastAPI orchestration API**: endpoints for sessions, terminals, inbox, flows (`src/cli_agent_orchestrator/api/main.py:301-903`).
- **HTTP internal service calls (`requests`)**: MCP server talks back to CAO API for terminal creation/input/output (`src/cli_agent_orchestrator/mcp_server/server.py:123-176`, `194-203`, `354-363`).
- **Filesystem + DB-backed inbox**: pending/delivered message queue and status updates (`src/cli_agent_orchestrator/services/inbox_service.py:31-37`, `89-132`).
- **Watchdog polling observer**: event loop for idle-triggered inbox delivery (`src/cli_agent_orchestrator/api/main.py:141-146`, `src/cli_agent_orchestrator/services/inbox_service.py:135-173`).
- **Scheduled flow automation**: cron-like flow execution using `apscheduler` + markdown frontmatter-defined prompts/scripts (`src/cli_agent_orchestrator/services/flow_service.py:10-12`, `155-227`).
- **Skill retrieval/injection**: server exposes `/skills/{name}` and MCP `load_skill`; skill text can be appended into system prompts (`src/cli_agent_orchestrator/api/main.py:272-299`, `src/cli_agent_orchestrator/mcp_server/server.py:639-644`, `src/cli_agent_orchestrator/providers/base.py:168-183`).

No vector DB/RAG stack (e.g., Chroma/Pinecone/pgvector) is wired in core runtime.

## 5. Notable Code Walkthrough

- `src/cli_agent_orchestrator/mcp_server/server.py:55-654`  
  Defines the multi-agent control plane tools. It creates child terminals, handles blocking handoff vs async assign, queues inter-agent messages, and fetches worker outputs.

- `src/cli_agent_orchestrator/services/terminal_service.py:80-214`  
  Core lifecycle orchestration: creates tmux windows, persists metadata, resolves profile/tool permissions, instantiates provider adapters, and starts log piping for downstream inbox/event logic.

- `src/cli_agent_orchestrator/services/inbox_service.py:75-173`  
  Implements asynchronous inter-agent messaging: checks pending queue, verifies terminal readiness, delivers queued messages, and marks delivered/failed states; file-watch events trigger delivery attempts.

- `src/cli_agent_orchestrator/providers/codex.py:130-213`  
  Representative provider adapter showing how agent profile prompt, MCP server config, model, env forwarding (`CAO_TERMINAL_ID`), and tool-timeout settings are injected into the concrete CLI command.

- `src/cli_agent_orchestrator/agent_store/code_supervisor.md:15-61`  
  Encodes supervisor behavior policy (delegate coding to developer, review loop through reviewer) and is a key place where role-level orchestration strategy is authored.

## 6. Use-Case Mapping

Although the upstream assignment says **Code Generation**, the implemented system is broader and best categorized as **Workflow Automation** with strong coding support. The runtime’s primary value is orchestrating multi-agent task delegation across CLI agents (handoff/assign/send_message, terminal lifecycle, inbox scheduling), regardless of domain (`src/cli_agent_orchestrator/mcp_server/server.py:302-377`, `486-637`; `src/cli_agent_orchestrator/services/inbox_service.py:75-173`; `src/cli_agent_orchestrator/services/flow_service.py:155-227`).  

Code generation is definitely a first-class scenario (developer/reviewer/supervisor profiles and coding workflow prompts), but architecturally the repo is a general-purpose orchestration substrate for delegated agent workflows, including scheduled flows and cross-provider automation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Cross-provider abstraction is practical and explicit; one orchestration API drives many CLI agents (`providers/manager.py` + per-provider adapters).
  - Real multi-agent runtime semantics (blocking handoff + non-blocking assign + callback inbox) are concretely implemented, not just described.
  - Strong operational engineering around terminal state detection and retries for flaky TUIs (`terminal_service.py`, provider `get_status()` logic).
  - Agent profiles externalize role prompts, MCP config, and tool constraints, enabling configurable MAS behavior without code edits.
  - Includes end-to-end multi-agent orchestration tests across providers (`test/e2e/test_supervisor_orchestration.py`).

- **Limitations:**
  - Heavy dependence on tmux and CLI output regex parsing makes behavior brittle to upstream UI changes in provider CLIs.
  - No formal task graph/state-machine abstraction; orchestration logic is scattered across MCP handlers, inbox watcher, and provider status heuristics.
  - Security/tool restriction enforcement is inconsistent by provider (hard blocking for some, soft prompt constraints for others).
  - Limited built-in conflict resolution/planning sophistication; coordination intelligence is mostly prompt-driven supervisor behavior.
  - Localhost-first architecture (WebSocket/API trust assumptions) is not designed for secure multi-tenant remote deployment.

- **Research relevance:**
  - Useful evidence of **practical manager-worker MAS** built on heterogeneous commercial agent CLIs.
  - Demonstrates **hybrid sync/async orchestration** (blocking delegation + event-driven callback queues) in production-style tooling.
  - Illustrates how **role prompts + tool affordances** shape emergent multi-agent behavior more than formal planners.
  - Provides a realistic benchmark for studying robustness issues in agent orchestration under noisy terminal/TUI interfaces.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
