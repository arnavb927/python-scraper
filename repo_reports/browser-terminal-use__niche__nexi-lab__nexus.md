---
repo_name: nexi-lab/nexus
url: "https://github.com/nexi-lab/nexus"
stars: 275
forks: 7
contributors_count: 13
last_commit_date: "2026-04-23T05:51:09+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 5
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T14:37:33.704947+00:00"
model: auto
duration_s: 116.1
clone_size_kb: 54578
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`nexi-lab/nexus` is primarily an AI-oriented filesystem/context platform plus daemon (`nexusd`) that exposes RPC/HTTP/MCP interfaces, and a CLI/TUI (`nexus`) for operating workflows, search, and agent tasks. In practice, users run `nexusd` to start the node and then use commands like `nexus acp call ...` to invoke coding-agent CLIs (Claude/Codex/Gemini) or `nexus workflows ...` to run event-driven automations (`src/nexus/daemon/main.py:229-247`, `src/nexus/cli/commands/acp_cli.py:53-99`, `src/nexus/cli/commands/workflows.py:48-66`). The system persists agent configs/results in its VFS and routes many operations through service abstractions (workflow engine, search, sandbox, MCP). It is not just an agent chat app; it is a workflow + tool/runtime substrate that can host agent interactions.

## 2. Agent Framework & Architecture

The core runtime is **custom**, not LangGraph/CrewAI/AutoGen orchestration. The main “agent” path is ACP JSON-RPC over subprocess pipes: `AcpService` spawns external coding-agent CLIs, wraps stdio with `StdioPipeBackend`, runs ACP session lifecycle (`initialize -> session/new|load -> session/prompt`), then stores results (`src/nexus/services/acp/service.py:71-84`, `src/nexus/services/acp/service.py:227-317`, `src/nexus/services/acp/service.py:678-701`). `AcpConnection` extends a generic `AgentLoop` transport and handles ACP-specific messages like permission requests and file I/O (`src/nexus/services/acp/connection.py:53-60`, `src/nexus/services/acp/connection.py:218-239`).

There is also an **optional integration layer** for LangGraph/LangChain tools (`src/nexus/tools/langgraph/nexus_tools.py:30-33`), but that is adapter code, not the core orchestration engine. Likewise, MCP is implemented with FastMCP (`src/nexus/bricks/mcp/server.py:17-18`) as a tool-serving surface.

“Intelligence” is split across:  
- external LLM agents called through ACP (model reasoning lives outside Nexus),  
- workflow definitions/triggers/actions inside Nexus (`src/nexus/bricks/workflows/engine.py:34-55`, `src/nexus/bricks/workflows/triggers.py:160-169`),  
- tool interfaces in MCP and ACP bridges.

## 3. Orchestration Pattern

Closest match: **event-driven workflow orchestration + manager/worker subprocess control**.

- **Event-driven**: file/metadata/schedule/webhook triggers are matched and callbacks fire workflow execution (`src/nexus/bricks/workflows/triggers.py:196-220`), while `WorkflowDispatchService` writes trigger events into a DT_PIPE and a background consumer dispatches to `workflow_engine.fire_event(...)` (`src/nexus/services/lifecycle/workflow_dispatch_service.py:81-83`, `src/nexus/services/lifecycle/workflow_dispatch_service.py:188-213`).
- **Manager/worker-like**: `AcpService` acts as manager; each external coding agent process is a worker process registered/killed through `AgentRegistry` (`src/nexus/services/acp/service.py:199-207`, `src/nexus/services/acp/service.py:362-365`, `src/nexus/services/agents/agent_registry.py:203-216`).

Example control flow excerpts:

```src/nexus/services/acp/service.py:229-236
proc = await asyncio.create_subprocess_exec(
    *cmd,
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    cwd=cwd,
    env=env,
)
```

```src/nexus/bricks/workflows/engine.py:336-352
for i, action_def in enumerate(definition.actions, 1):
    action_class = self.action_registry.get(action_def.type)
    if not action_class:
        raise ValueError(f"Unknown action type: {action_def.type}")
    action = action_class(action_def.name, action_def.config)
    result = await action.execute(context)
```

## 4. Tools & External Integrations

- **ACP coding-agent CLIs (Claude/Codex/Gemini/etc.)**: subprocess execution + ACP protocol lifecycle in `AcpService`/`AcpConnection` (`src/nexus/services/acp/service.py:3-5`, `src/nexus/services/acp/service.py:666-676`, `src/nexus/services/acp/connection.py:92-110`).
- **Filesystem + process I/O as VFS objects**: DT_PIPE registration for agent stdio and workflow pipes (`src/nexus/services/acp/service.py:271-279`, `src/nexus/services/lifecycle/workflow_dispatch_service.py:151-156`).
- **MCP server (FastMCP)** exposing file/search/workflow/sandbox tools to LLM clients (`src/nexus/bricks/mcp/server.py:87-97`, `src/nexus/bricks/mcp/server.py:389-398`, `src/nexus/bricks/mcp/server.py:1417-1433`).
- **Sandbox execution** (Python/Bash) via sandbox manager RPC (`src/nexus/bricks/mcp/server.py:1429-1451`, `src/nexus/bricks/workflows/actions.py:337-351`).
- **Search stack** (glob/grep/semantic) with ReBAC filtering exposed via MCP (`src/nexus/bricks/mcp/server.py:811-820`, `src/nexus/bricks/mcp/server.py:943-956`, `src/nexus/bricks/mcp/server.py:1132-1141`).
- **Webhook HTTP integration** in workflow actions via `aiohttp` with SSRF checks (`src/nexus/bricks/workflows/actions.py:232-245`, `src/nexus/bricks/workflows/actions.py:262-276`).
- **Optional LangGraph/LangChain tool adapter** for external agents (`src/nexus/tools/langgraph/nexus_tools.py:30-33`, `src/nexus/tools/langgraph/nexus_tools.py:103-122`).

## 5. Notable Code Walkthrough

- `src/nexus/services/acp/service.py:71-84,139-156,227-317,678-701`  
  Core ACP runtime: spawns external coding-agent subprocesses, performs ACP session RPC, maps/records outputs, and persists results to VFS.

- `src/nexus/services/acp/connection.py:53-60,218-251,263-295`  
  Protocol adapter over generic JSON-RPC pipe loop; handles ACP permissions, `session/update` observation, and filesystem read/write requests from agent side.

- `src/nexus/bricks/workflows/engine.py:34-55,276-313,336-391`  
  Workflow engine: maintains trigger/action registries, creates execution contexts, and runs actions sequentially with status tracking/persistence.

- `src/nexus/bricks/workflows/actions.py:222-290,292-331,389-425`  
  Action implementations for webhooks and sandboxed Python/Bash execution with security controls (SSRF validation, fail-closed sandbox requirement).

- `src/nexus/bricks/mcp/server.py:87-97,389-510,811-933,1132-1244`  
  Full MCP surface exposing file/search/workflow/sandbox tools; this is the key integration layer for agent tool-use from MCP-compatible clients.

## 6. Use-Case Mapping

The repository does include **terminal-like agent execution** via ACP subprocess control and bash/python sandbox execution, so it partially matches `Browser / Terminal Use` (`src/nexus/services/acp/service.py:229-236`, `src/nexus/bricks/mcp/server.py:1436-1451`).  
However, the dominant implemented pattern is **Workflow Automation**: trigger-driven pipelines, action registries, dispatch queues/pipes, and workflow lifecycle management (`src/nexus/bricks/workflows/engine.py:406-420`, `src/nexus/services/lifecycle/workflow_dispatch_service.py:188-213`, `src/nexus/cli/commands/workflows.py:48-66`).  
I would categorize it as **Workflow Automation** first, with terminal-agent execution as a major capability.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong separation of concerns: transport (`AgentLoop`), ACP protocol (`AcpConnection`), process lifecycle (`AgentRegistry`), and workflow engine are modular.
  - Practical agent interoperability by calling real external coding-agent CLIs over ACP.
  - Rich tool surface via MCP (files/search/sandbox/workflow/context operations) with auth/ReBAC-aware filtering.
  - Event-driven automation path (triggers + actions + dispatch pipe) is explicit and production-oriented.
  - Security hardening appears deliberate (SSRF checks, prompt sanitization, sandbox fail-closed behavior).

- **Limitations:**
  - Multi-agent “coordination intelligence” is limited; most reasoning is delegated to single external agents per call, not an internal planner/society.
  - No first-class browser automation stack (e.g., Playwright/Browserbase) in the inspected core runtime.
  - LangGraph integration exists as adapters, but core orchestration is not graph-native LLM planning.
  - Workflow actions shown are mostly deterministic ops/sandbox/webhook; LLM action appears referenced in CLI help text but not in built-in action registry shown.
  - Complexity is high and cross-cutting, which may raise onboarding and operability costs.

- **Research relevance:**
  - Good example of **agent runtime infrastructure** (process, IPC, permissioned file I/O) rather than purely prompt-level agent design.
  - Useful case for studying **event-driven automation + agent tooling convergence** (workflow engine + MCP + ACP).
  - Illustrates architectural pattern where LLM cognition is externalized while platform handles governance, context, and tool mediation.
  - Evidence for secure tool-augmented agent systems using layered auth/ReBAC and sandbox constraints.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
