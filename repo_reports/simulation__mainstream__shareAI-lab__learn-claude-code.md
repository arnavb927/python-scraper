---
repo_name: shareAI-lab/learn-claude-code
url: "https://github.com/shareAI-lab/learn-claude-code"
stars: 55792
forks: 9185
contributors_count: 22
last_commit_date: "2026-04-14T16:58:19+00:00"
primary_use_case: Simulation
user_tier: Mainstream
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T09:23:13.420806+00:00"
model: auto
duration_s: 79.1
clone_size_kb: 1905
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a hands-on Python implementation of a Claude Code–style agent harness, where users run scripts like `python agents/s01_agent_loop.py` through `python agents/s12_worktree_task_isolation.py` (or `python agents/s_full.py`) to interact with an LLM that can call tools in a local workspace. The project progressively adds capabilities: shell/file tools, todo planning, subagents, background execution, team coordination, protocol handshakes, autonomous task claiming, and git worktree isolation. In practical use, a user gets a REPL-style coding assistant that can execute workflows end-to-end rather than just chat. The repo is both executable code and a teaching scaffold for “how to build the harness around a model,” not model training itself.

## 2. Agent Framework & Architecture

This is a **custom framework**, not LangGraph/LangChain/CrewAI/AutoGen. The runtime imports `anthropic` directly and builds its own loop/tool protocol (`agents/s01_agent_loop.py:41-91`, `agents/s_full.py:49-59`, `agents/s_full.py:653-707`). There are no imports from common orchestration libraries; control flow is handwritten Python with threads, queues, JSON files, and tool dispatch tables.

Architecture-wise, intelligence is primarily in model calls plus system prompts and tool schemas. The core loop repeatedly calls `client.messages.create(...)`, checks `stop_reason == "tool_use"`, executes handlers, and appends `tool_result` blocks back into messages (`agents/s01_agent_loop.py:80-102`, `agents/s_full.py:672-701`). Capabilities are layered via manager components: `TodoManager`, `TaskManager`, `BackgroundManager`, `MessageBus`, and `TeammateManager` (`agents/s_full.py:122-550`).

For multi-agent behavior, the lead agent can spawn persistent teammate threads and communicate through file-backed inboxes (`.team/inbox/*.jsonl`), while workers can idle, poll, auto-claim tasks, and resume work (`agents/s09_agent_teams.py:123-205`, `agents/s11_autonomous_agents.py:216-304`). So this is a custom manager-plus-workers harness with persistent shared state and asynchronous coordination.

## 3. Orchestration Pattern

Closest match: **Hierarchical (manager-worker) with event-driven messaging**.

- Hierarchical: a lead agent spawns teammates and dispatches/coordinates via explicit tools (`spawn_teammate`, `send_message`, `shutdown_request`, `plan_approval`) (`agents/s10_team_protocols.py:381-395`).
- Event-driven: teammates and lead react to inbox and background notifications (`agents/s09_agent_teams.py:345-379`, `agents/s08_background_tasks.py:188-216`).

Control-flow excerpt 1 (lead loop and tool roundtrip):

```135:144:agents/s01_agent_loop.py
response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
messages.append({"role": "assistant", "content": response.content})
if response.stop_reason != "tool_use":
    return
...
messages.append({"role": "user", "content": results})
```

Control-flow excerpt 2 (team mailbox injection + dispatch):

```345:357:agents/s09_agent_teams.py
inbox = BUS.read_inbox("lead")
if inbox:
    messages.append({
        "role": "user",
        "content": f"<inbox>{json.dumps(inbox, indent=2)}</inbox>",
    })
response = client.messages.create(
    model=MODEL,
    system=SYSTEM,
    messages=messages,
    tools=TOOLS,
```

## 4. Tools & External Integrations

- **Anthropic Messages API**: Core LLM backend via `Anthropic(...).messages.create(...)` in all agent scripts (`agents/s01_agent_loop.py:41-50`, `agents/s_full.py:57-59`, `agents/s_full.py:672-675`).
- **Shell/terminal execution**: `bash` tool backed by `subprocess.run(...)` for command execution (`agents/s02_tool_use.py:48-59`, `agents/s12_worktree_task_isolation.py:485-502`).
- **Filesystem read/write/edit**: `read_file`, `write_file`, `edit_file` tools with workspace path checks (`agents/s02_tool_use.py:41-45`, `agents/s02_tool_use.py:61-91`).
- **Subagent delegation**: `task` tool spawns isolated child message loops (fresh context) (`agents/s04_subagent.py:117-137`, `agents/s_full.py:160-195`).
- **Background task execution**: threaded async runner and notification queue (`agents/s08_background_tasks.py:50-109`, `agents/s_full.py:327-361`).
- **Team messaging bus**: JSONL inbox files per teammate (`.team/inbox`) for async inter-agent communication (`agents/s09_agent_teams.py:77-120`).
- **Protocol/state coordination**: shutdown and plan approval request tracking keyed by `request_id` (`agents/s10_team_protocols.py:81-85`, `agents/s10_team_protocols.py:350-374`).
- **Task board persistence**: file-based tasks in `.tasks/task_*.json` with claim/update/dependency workflow (`agents/s11_autonomous_agents.py:126-157`, `agents/s_full.py:261-325`).
- **Git worktree integration**: creates/runs/removes isolated worktrees via git CLI; lifecycle events logged to `.worktrees/events.jsonl` (`agents/s12_worktree_task_isolation.py:224-336`, `agents/s12_worktree_task_isolation.py:394-447`).
- **No MCP/browser/vector DB/RAG pipeline wiring** in runtime code. README mentions omitted full MCP runtime (`README.md:219-230`).

## 5. Notable Code Walkthrough

- `agents/s01_agent_loop.py:80-102` — Minimal canonical agent loop showing the core `tool_use` feedback cycle; everything else in the repo builds on this.
- `agents/s04_subagent.py:117-168` — Implements delegated subagents with isolated context and summary-only return to parent, a key anti-context-bloat pattern.
- `agents/s09_agent_teams.py:77-120` — Defines JSONL `MessageBus` (append + drain semantics), which is the backbone of multi-agent communication.
- `agents/s11_autonomous_agents.py:267-304` — Idle polling + auto-claim logic; teammates resume work without explicit lead assignment, enabling autonomy.
- `agents/s12_worktree_task_isolation.py:224-327` — `WorktreeManager.create()` binds tasks to isolated git worktrees, enabling safe parallel execution lanes.

## 6. Use-Case Mapping

The upstream “Simulation” label is understandable because the repo is pedagogical and decomposed into staged scenarios (`s01`–`s12`). However, the executable behavior is not just simulation: it actually runs real shell commands, edits files, creates tasks, spawns persistent agent teammates, and manages worktree-based parallel coding workflows (`agents/s_full.py`, `agents/s12_worktree_task_isolation.py`). That maps more directly to **Workflow Automation** (especially coding/dev workflow orchestration) than to pure simulation. So the better final category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Clear progressive decomposition from single-agent loop to multi-agent coordination, with runnable code at each step (`agents/s01_*.py` to `agents/s12_*.py`).
- Runtime multi-agent coordination is concrete (threads + inbox bus + shared task board), not just conceptual (`agents/s09_agent_teams.py`, `agents/s11_autonomous_agents.py`).
- Strong harness transparency: tool schemas and handlers are explicit and easy to audit (`agents/s_full.py:576-650`).
- Includes practical context-management mechanisms (microcompact, auto-compaction, identity re-injection) for long sessions (`agents/s_full.py:226-259`, `agents/s_full.py:518-523`).
- Adds isolation/parallelism with git worktrees and event logs, which is unusually operational for an educational repo (`agents/s12_worktree_task_isolation.py`).

- **Limitations:**
- Safety controls are basic string filters around shell commands; no robust sandbox/permission model (`agents/s02_tool_use.py:48-51`).
- Shared mutable state uses local files and in-process threads; no distributed reliability, transactional guarantees, or recovery protocols.
- Protocol logic is heuristic and partially ad hoc (e.g., request trackers in memory, teammate loop limits), so fault tolerance is limited (`agents/s10_team_protocols.py:81-85`, `agents/s10_team_protocols.py:185-220`).
- Tests are lightweight (mostly compile checks plus one background behavior unit test), leaving major multi-agent behaviors under-tested (`tests/test_agents_smoke.py`, `tests/test_s_full_background.py`).
- Tight coupling to Anthropic API and single model config; no abstraction for multi-provider execution.

- **Research relevance:**
- Good evidence of a lightweight, code-first **manager-worker MAS pattern** using LLM tool calls and shared external state.
- Demonstrates practical mailbox-based communication and protocol handshakes between LLM agents in local execution environments.
- Useful case study for autonomy mechanisms (idle polling + task auto-claim) without complex graph frameworks.
- Relevant for studying trade-offs between simplicity and robustness in agent orchestration infrastructures.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
