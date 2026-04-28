---
repo_name: Norbert515/vide_cli
url: "https://github.com/Norbert515/vide_cli"
stars: 105
forks: 13
contributors_count: 5
last_commit_date: "2026-03-08T11:06:13+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-04-27T17:06:52.282276+00:00"
model: auto
duration_s: 110.2
clone_size_kb: 9589
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`vide_cli` is a Dart-based agentic developer assistant that users run as either a terminal UI (`dart run bin/vide.dart`) or a REST/WebSocket server (`packages/vide_server`). It manages a live network of LLM agents (main orchestrator plus spawned specialists) that can delegate work, exchange messages, and report status in real time. The core engine lives in `packages/vide_core` and is shared by both interfaces, so the same multi-agent runtime powers local TUI sessions and remote clients. In practice, a user gives a task, the lead agent spawns role-based subagents (researcher/implementer/QA/etc.), and the system streams messages/tool events while coordinating permissions and lifecycle.

## 2. Agent Framework & Architecture

This is **not** LangGraph/LangChain/CrewAI/AutoGen. It is a **custom multi-agent framework** built on the project’s own abstractions (`agent_sdk`, `vide_core`) and provider/state orchestration (`riverpod`). Agent clients are instantiated through factory layers for Claude and Codex backends (`packages/vide_core/lib/src/claude/claude_client_factory.dart:16-74`, `packages/vide_core/lib/src/claude/codex_client_factory.dart:23-78`), then managed in a shared network manager.

The architecture centers on `AgentNetworkManager`, which creates a session, instantiates the main agent, and supports runtime `spawnAgent`, `sendMessageToAgent`, `broadcastMessage`, `terminateAgent`, and `forkAgent` (`packages/vide_core/lib/src/agent_network/agent_network_manager.dart:192-346`, `:587-707`, `:726-740`). Agent personalities, allowed tools, MCP server lists, and role prompts are defined in team-framework markdown assets compiled into Dart constants (`packages/vide_core/lib/src/team_framework/bundled_team_framework.dart:8-25`, `:1369-1428`, `:1467-1491`) and resolved into concrete `AgentConfiguration` objects (`packages/vide_core/lib/src/team_framework/team_framework_loader.dart:179-270`).

“Intelligence” is therefore distributed across:
- role/team prompt specs in bundled `.md` assets,
- runtime delegation logic in `AgentLifecycleService`,
- event/status/permission handling in `LocalVideSession`,
- trigger rules that can auto-spawn agents on lifecycle milestones.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)** with **event-driven trigger augmentation**.

The main/lead agent delegates to specialized agents via MCP-exposed tools; child agents can message parents asynchronously. Spawning and inter-agent messaging are first-class operations in both MCP and core network manager (`packages/vide_core/lib/src/mcp/agent/agent_mcp_server.dart:48-67`, `:69-166`, `:189-246`; `packages/vide_core/lib/src/agent_network/agent_network_manager.dart:637-666`).

```dart
// packages/vide_core/lib/src/agent_network/agent_network_manager.dart:637-643
void sendMessageToAgent({
  required AgentId targetAgentId,
  required String message,
  required AgentId sentBy,
}) {
```

```dart
// packages/vide_core/lib/src/agent_network/agent_lifecycle_service.dart:100-107
Future<AgentId> spawnAgent({
  required String agentType,
  required String name,
  required String initialPrompt,
  required AgentId spawnedBy,
```

It is also event-driven because lifecycle triggers (`onSessionStart`, `onTaskComplete`, `onAllAgentsIdle`) can automatically spawn configured agents (`packages/vide_core/lib/src/team_framework/trigger_service.dart:15-27`, `:129-202`), adding autonomous behavior beyond direct manager commands.

## 4. Tools & External Integrations

- **Agent-network MCP tools** (`spawnAgent`, `sendMessageToAgent`, `setAgentStatus`, `terminateAgent`, task naming): wired in `packages/vide_core/lib/src/mcp/agent/agent_mcp_server.dart:48-67`.
- **Knowledge MCP server** for persistent docs in `.claude/knowledge` (`readKnowledge`, `writeKnowledge`, `searchKnowledge`, etc.): `packages/vide_core/lib/src/mcp/knowledge/knowledge_mcp_server.dart:35-58`.
- **Ask-user interaction MCP** (structured question flow) exists as a built-in server type: `packages/vide_core/lib/src/mcp/mcp_server_type.dart:13-23` and provider wiring in `packages/vide_core/lib/src/mcp/mcp_provider.dart:54-73`.
- **Flutter runtime MCP** for app lifecycle + UI automation (`flutterStart`, `flutterReload`, `flutterStop`, `flutterScreenshot`, `flutterAct`): server tool registration in `packages/flutter_runtime_mcp/lib/src/flutter_runtime_server.dart:69-78`, `:100`, `:282`, `:405`, `:675`, `:735`.
- **LLM backends**: Claude SDK and Codex SDK via factory registry (`packages/vide_core/lib/src/agent_network/agent_network_manager.dart:62-99`, `packages/vide_core/lib/src/claude/claude_client_factory.dart:199-206`, `packages/vide_core/lib/src/claude/codex_client_factory.dart:68-77`).
- **REST + WebSocket streaming API** for remote clients, including history replay and multiplexed agent events: `packages/vide_server/lib/routes/session_routes.dart:292-367`, `packages/vide_server/lib/services/session_broadcaster.dart:18-45`.
- **Permissions + human approvals** integrated at tool-call time: `packages/vide_core/lib/src/api/vide_session.dart:887-1018`.

No vector database (Chroma/Pinecone/pgvector) or classic RAG pipeline is implemented; knowledge is file-backed markdown.

## 5. Notable Code Walkthrough

- `packages/vide_core/lib/src/agent_network/agent_network_manager.dart:48-113,192-346,587-707`  
  Central orchestration state machine: creates sessions, registers main agent clients, exposes spawn/message/broadcast/terminate/fork operations, and synchronizes runtime status.

- `packages/vide_core/lib/src/agent_network/agent_lifecycle_service.dart:90-195,197-270`  
  Implements concrete lifecycle transitions (spawn/add/terminate/fork), validates team-defined agent types, builds metadata, and injects system reminders into spawned prompts.

- `packages/vide_core/lib/src/team_framework/team_framework_loader.dart:147-177,179-270,272-310`  
  Converts markdown team/agent definitions into executable agent configs (prompt assembly, include resolution, MCP server parsing, allowed/disallowed tools, harness settings).

- `packages/vide_core/lib/src/team_framework/bundled_team_framework.dart:8-25,1369-1428,1467-1491`  
  Embedded agent/team “policy” corpus: declares role prompts, available subagent types, models, and MCP access (e.g., `enterprise-lead`, `researcher`, lifecycle trigger settings).

- `packages/vide_core/lib/src/api/vide_session.dart:252-298,385-427,887-1018,1308-1344,1599-1660`  
  Runtime glue that streams agent/tool events, handles permission requests and human responses, tracks conversation state, and emits spawn/terminate events for clients.

## 6. Use-Case Mapping

This repo clearly supports **Browser / Terminal Use** through terminal-first agent operation, shell/tool invocation, and interactive control loops. Users run a TUI or connect via WebSocket; agents execute developer workflows by coordinating tool calls, file/code operations, and runtime checks, while the system exposes live event streams and permission gating (`packages/vide_server/lib/routes/session_routes.dart:703-741`, `packages/vide_core/lib/src/api/vide_session.dart:1599-1660`).

That said, the dominant practical behavior is broader **Workflow Automation for software engineering** (multi-role planning, implementation, QA cycles, triggers, coordination), not browser automation specifically. A better single label is therefore **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Explicit multi-agent runtime with spawn/message/terminate/fork primitives, not just prompt role-play.
  - Strong separation of orchestration core (`vide_core`) from interfaces (TUI and REST server).
  - Prompt/team definitions externalized as composable markdown assets, enabling role customization without code changes.
  - Real-time, replayable event stream architecture (`seq` + history broadcaster) for robust client synchronization.
  - Built-in permission mediation and human-in-the-loop controls at tool invocation boundaries.

- **Limitations:**
  - Considerable orchestration complexity and many moving parts (providers, lifecycle services, triggers), increasing operational/debug burden.
  - Tool/server parsing appears partly opinionated around known MCP names, which may constrain plug-and-play external MCP diversity.
  - Knowledge system is file-based markdown; no semantic retrieval/indexing layer for large-scale memory.
  - Heavy dependence on external model CLIs/SDK behaviors (Claude/Codex), so reproducibility may vary by backend availability.
  - Prompt-heavy role behavior means quality is sensitive to authored markdown policies rather than formal planner guarantees.

- **Research relevance:**
  - Concrete example of production-style hierarchical MAS with asynchronous inter-agent messaging.
  - Useful case for studying event-sourced observability in multi-agent developer systems.
  - Demonstrates hybrid orchestration: manager-worker delegation plus trigger-based autonomous spawning.
  - Illustrates practical human-governance mechanisms (permissions, approvals, plan gates) in agentic software workflows.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
