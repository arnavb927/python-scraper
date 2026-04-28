---
repo_name: HoangNguyen0403/agent-skills-standard
url: "https://github.com/HoangNguyen0403/agent-skills-standard"
stars: 430
forks: 124
contributors_count: 5
last_commit_date: "2026-04-23T02:46:18+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [RAG + Agents]
generated_at: "2026-04-27T16:21:15.074103+00:00"
model: auto
duration_s: 97.6
clone_size_kb: 6296
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a **skill registry + synchronization toolkit** for AI coding assistants, not an end-user chatbot. A user runs the CLI (`agent-skills-standard`) to initialize config, sync skill packs/workflows from GitHub, and wire MCP configs into tools like Cursor/Claude/Copilot (`cli/src/index.ts:15-133`, `cli/src/commands/sync.ts:39-130`). The synced output is local rule content (`SKILL.md`, `_INDEX.md`, `AGENTS.md`, agent-specific bridge files) that downstream AI agents read/use while coding. It also ships an MCP server that serves matching skills on demand (`mcp/src/index.ts:6-20`, `mcp/src/server.ts:99-203`) plus a small feedback API backend that opens GitHub issues for quality feedback (`server/src/feedback/feedback.service.ts:40-55`).

## 2. Agent Framework & Architecture

The codebase uses **custom orchestration + MCP SDK**, not LangGraph/LangChain/CrewAI/AutoGen. The only explicit agent-runtime framework import is Model Context Protocol: `@modelcontextprotocol/sdk` (`mcp/src/index.ts:2`, `mcp/src/server.ts:1`). I found no runtime LLM provider SDK calls (OpenAI/Anthropic/etc.) in core source.

Architecture is split into three parts:
1. **CLI sync/orchestration layer** (`cli/`): fetches skill/workflow artifacts from GitHub, writes them into agent-specific directories, regenerates routing indexes, and configures MCP integration (`cli/src/services/SyncService.ts:21-178`).
2. **MCP serving layer** (`mcp/`): loads local skill metadata/content, matches by file/keyword, and returns skill text to whichever external AI agent connected over stdio (`mcp/src/services/SkillIndex.ts:91-164`, `mcp/src/tools/index.ts:76-223`).
3. **Feedback backend** (`server/`): optional NestJS service that receives feedback and opens GitHub issues (`server/src/feedback/feedback.controller.ts:15-28`, `server/src/feedback/feedback.service.ts:45-51`).

The “intelligence” here is mostly in **routing/matching logic and prompt/rule packaging**, not in autonomous in-repo LLM reasoning. Skill selection is deterministic via file-extension routing, glob/keyword triggers, and composite expansion rules (`mcp/src/services/SkillIndex.ts:100-135`, `:187-226`).

## 3. Orchestration Pattern

Closest match: **sequential workflow automation** (single-controller pipeline), not manager-worker multi-agent runtime.

Control flow in `sync` is linear: load config -> reconcile -> fetch -> write -> index -> MCP phase.

```39:57:cli/src/commands/sync.ts
async run(options: { yes?: boolean } = {}) {
  // 1. Load Config
  const config = await this.configService.loadConfig();
  // 2. Dynamic Update Configuration (Re-detection)
  const projectDeps = await this.detectionService.getProjectDeps();
  const skillsChanged = await this.syncService.reconcileConfig(config, projectDeps);
  const workflowsChanged = await this.syncService.reconcileWorkflows(config);
```

MCP tool execution is also request/response: match files/keywords, then return SKILL.md content and log load events.

```76:85:mcp/src/tools/index.ts
export async function loadSkillsForFiles(
  args: { files: string[] },
  ctx: ToolContext,
): Promise<ToolResult> {
  const empty = maybeEmptyState(ctx);
  if (empty) return empty;

  const matches = ctx.index.matchFiles(args.files);
  return await finalize('load_skills_for_files', args.files, matches, ctx);
}
```

## 4. Tools & External Integrations

- **MCP runtime integration** via `@modelcontextprotocol/sdk`, serving tools like `load_skills_for_files`, `get_skill`, and `audit_session_compliance` (`mcp/src/server.ts:115-200`, `mcp/src/index.ts:17-19`).
- **GitHub REST/raw endpoints** for registry sync (`api.github.com`, `raw.githubusercontent.com`) in `GithubService` (`cli/src/services/GithubService.ts:10-12`, `:32-45`, `:59-70`).
- **File-system integration** (`fs-extra`, path writes) for installing skills/workflows and bridge configs (`cli/src/services/WorkflowSyncService.ts:150-193`, `cli/src/services/AgentBridgeService.ts:88-147`).
- **Agent tool config writing** for Cursor/Claude/Gemini/Windsurf/etc. via MCP config service/commands (`cli/src/commands/mcp.ts:12-23`, `:185-225`; also referenced in `sync.ts:128-207`).
- **Feedback API -> GitHub Issues** using Octokit (`server/src/feedback/feedback.service.ts:22-24`, `:45-51`).
- **No vector DB / embeddings / retrieval pipeline** (no Chroma/Pinecone/pgvector-style integration found in runtime code).

## 5. Notable Code Walkthrough

- `mcp/src/server.ts:51-203`  
  Defines server-wide agent instructions and registers the five MCP tools. This is the core runtime surface external AI agents actually call.

- `mcp/src/services/SkillIndex.ts:91-164`  
  Implements deterministic skill matching (`matchFiles`, `matchKeywords`) with broad-glob demotion and category routing from metadata; this is the repo’s key “policy selection engine.”

- `mcp/src/tools/index.ts:227-319`  
  `finalize()` and no-match guidance shape what the agent receives, including full `SKILL.md` bodies and actionable fallback hints; also records compliance events.

- `cli/src/commands/sync.ts:39-130`  
  Main end-user command pipeline for syncing skills/workflows and then wiring MCP support; this is what users run most often.

- `cli/src/services/WorkflowSyncService.ts:129-205`  
  Converts shared workflow markdown into agent-specific formats/locations (rules, prompts, TOML commands), showing the repository’s multi-platform automation focus.

## 6. Use-Case Mapping

Assigned label was **RAG + Agents**, but after reading code, this is better categorized as **Workflow Automation**.

Why: the repo does not implement a runtime multi-agent reasoning system (no planner/executor loops, no inter-agent message passing, no LLM-call graph). Instead, it automates **skill distribution, rule routing, and MCP/tooling configuration** for *other* agents. There is “retrieval-like” behavior (loading relevant SKILL.md by file/keyword), but it is deterministic local rule lookup rather than a full RAG pipeline with embeddings/vector search/generation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong cross-agent interoperability strategy (Cursor/Claude/Copilot/Gemini/etc.) with concrete config writers.
  - Clear deterministic routing model (file extension -> category -> triggers) plus composite skill expansion.
  - Good operational UX: setup guidance, no-match guidance, and compliance audit trail in MCP tools.
  - Practical security hardening in sync/write paths (path safety checks, config/validation structure).
  - Separation of concerns across CLI sync, MCP serving, and feedback API.

- **Limitations:**
  - No in-repo LLM execution or autonomous coordination; intelligence is mostly static rules + routing.
  - No semantic retrieval stack (no embeddings/vector store), so matching quality depends on trigger curation.
  - Session tracking is in-memory per MCP process; no durable cross-session audit history.
  - Heavy reliance on external GitHub availability for registry sync.
  - Large skill corpus may create maintenance complexity despite indexing/tiering.

- **Research relevance:**
  - Useful evidence for **agent governance infrastructure** (policy injection, compliance logging) rather than MAS behavior.
  - Demonstrates a practical design for **tool-mediated rule retrieval** in coding assistants.
  - Shows how to standardize prompt/rule surfaces across heterogeneous AI tooling ecosystems.
  - Relevant to studies on **operational control layers around agents**, not emergent multi-agent coordination.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
