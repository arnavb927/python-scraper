---
repo_name: testdriverai/testdriverai
url: "https://github.com/testdriverai/testdriverai"
stars: 219
forks: 33
contributors_count: 13
last_commit_date: "2026-03-28T03:51:25+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [Custom/Other]
use_case_labels: [RAG + Agents]
generated_at: "2026-04-27T17:44:54.493961+00:00"
model: auto
duration_s: 86.3
clone_size_kb: 42008
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`testdriverai` is a Node.js SDK/CLI for AI-driven end-to-end testing of browser/desktop workflows, where users run commands like `testdriverai run` or call SDK methods such as `testdriver.act(...)` inside Vitest tests. The core flow is: capture current UI state (screenshots + system context), send task/assertion/find requests to TestDriver’s API, receive structured instructions, and execute them in a remote sandbox. It can run tests from YAML scripts, generate tests, or let an external coding agent use its MCP server tools (`find`, `click`, `assert`, etc.) to iteratively build test code. The primary output is executable test steps plus run artifacts (screenshots, logs, summaries, and cloud run URLs).

## 2. Agent Framework & Architecture

This repo uses a **custom agent framework** (not LangGraph/LangChain/AutoGen/CrewAI). The runtime core is `TestDriverAgent` in `agent/index.js`, with custom modules for parsing AI output, command routing, sandbox I/O, and API transport (`agent/lib/parser.js`, `agent/lib/commands.js`, `agent/lib/sdk.js`). There are no imports of mainstream agent orchestration frameworks in the runtime path.

Architecture is centered on a **single orchestrator agent** that loops: prompt API → parse YAML code blocks → execute commands → optionally run a “check” pass and recurse. The “intelligence” largely lives server-side in API endpoints invoked by `sdk.req("input"|"check"|"error"|"summarize"|...)`, while local code handles execution control, retries/healing, and tool invocation (`agent/index.js:921-939`, `agent/index.js:670-748`, `agent/lib/sdk.js:335-523`).

There is also an MCP server (`mcp-server/src/server.ts`) that exposes many action tools. However, that is primarily a **tool adapter** for an external host LLM agent (e.g., Claude/Copilot), not an internal multi-agent runtime. The `.md` agent file under `ai/agents/testdriver.md` is a prompt/config artifact for external IDE agent systems, not coordinated in-process agents (`ai/agents/testdriver.md:1-15`).

## 3. Orchestration Pattern

Closest match: **sequential looped controller (single-agent), i.e., “other”**.

Control flow is linear and recursive: one agent gets AI markdown, extracts YAML blocks, executes each command, then does a completion check and may recurse if more commands are returned.

Example 1 (loop orchestration in agent):
- `aiExecute()` executes markdown, then runs `check()`, parses returned codeblocks, and recursively calls itself if more work is needed (`agent/index.js:673-747`).

Example 2 (markdown-to-command execution pipeline):
- `actOnMarkdown()` → `executeCodeBlocks()` → `executeCommands()` → `runCommand()`, where YAML commands map to concrete command handlers (`agent/index.js:1070-1104`, `agent/index.js:616-667`, `agent/index.js:558-611`, `agent/index.js:468-555`).

This is not manager-worker or graph-state-machine orchestration; there is no runtime coordination among multiple distinct LLM agents.

## 4. Tools & External Integrations

- **TestDriver cloud API (LLM + task endpoints)**: local agent calls API routes for auth and task types like `input`, `check`, `assert`, `find`, `error`, etc. (`agent/lib/sdk.js:187-235`, `agent/lib/sdk.js:335-523`, `agent/index.js:921-927`, `agent/index.js:453-458`).
- **Sandbox/remote execution backend**: connects/authenticates to sandbox service and sends command events (`create`, `connect`, `direct`, shell run, mouse/keyboard ops) (`agent/index.js:2127-2233`, `agent/lib/commands.js:573-591`, `agent/lib/commands.js:1580-1585`).
- **MCP integration**: full MCP server built with `@modelcontextprotocol/sdk` and ext-apps, exposing tools like `session_start`, `find`, `click`, `check`, `exec` (`mcp-server/src/server.ts:12-16`, `mcp-server/src/server.ts:495-777`, `mcp-server/src/server.ts:846-1880`).
- **IDE/agent ecosystem integration**: agent profile and setup wiring for Claude/Cursor-style agent installs and MCP config generation (`ai/agents/testdriver.md:1-15`, `interfaces/cli/commands/setup.js:46-121`, `lib/init-project.js:413-453`).
- **Telemetry/observability**: Sentry integrated in MCP and core runtime (`mcp-server/src/server.ts:17`, `mcp-server/src/server.ts:72-129`; `agent/index.js:111-114`).
- **Storage/upload optimization**: large screenshots uploaded via presigned URL instead of inline payload (`agent/lib/sdk.js:345-412`).
- **No vector DB / retrieval store pipeline in runtime**: no Chroma/Pinecone/pgvector-style retrieval path found in agent execution code.

## 5. Notable Code Walkthrough

- `agent/index.js:40-2463`  
  Main orchestrator (`TestDriverAgent`): owns lifecycle, recursive AI execution, error-healing loop, YAML file execution, sandbox provisioning, and command dispatch.

- `agent/lib/sdk.js:117-615`  
  API transport layer with auth, retries/backoff, streaming JSONL handling, and request shaping (including screenshot offload to S3-like presigned uploads).

- `agent/lib/commands.js:95-1700`  
  Concrete action implementations (click/type/scroll/assert/exec/find helpers), redraw waiting, and interaction tracking; this is where “tool execution” happens.

- `sdk.js:1418-1610` and `sdk.js:4246-4337`  
  Public SDK wrapper that instantiates one underlying `TestDriverAgent`, then exposes user-facing methods including `act()/ai()` for natural-language task execution.

- `mcp-server/src/server.ts:495-2410`  
  MCP tool surface enabling external coding agents to drive TestDriver sessions and generate test code iteratively.

## 6. Use-Case Mapping

The upstream label `RAG + Agents` appears **misclassified** for this repository’s runtime. The code does implement agentic behavior, but it is primarily **computer-use workflow automation** (UI actions, assertions, sandbox orchestration), not a retrieval-augmented generation pipeline with document indexing/retrieval. There is no central runtime RAG stack (vector store retriever + grounding loop) in the core execution path. A better category is **Workflow Automation** (with strong Browser/Terminal-use characteristics).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong end-to-end agent execution loop with self-check and error-recovery (`agent/index.js:279-415`, `agent/index.js:673-747`).
  - Rich action/tooling surface across UI, shell, assertions, and screenshot evidence (`agent/lib/commands.js:774-1700`, `mcp-server/src/server.ts:846-1880`).
  - Practical production concerns: retries/backoff, typed schemas, telemetry, session management (`agent/lib/sdk.js:11-115`, `mcp-server/src/server.ts:291-334`).
  - Good interoperability: SDK + CLI + MCP + IDE agent scaffolding (`package.json:32-35`, `mcp-server/src/server.ts:12-16`, `lib/init-project.js:413-453`).

- **Limitations:**
  - Not a true multi-agent system at runtime; mostly one controller agent plus external tool adapters (`agent/index.js:40-103`, `sdk.js:1458-1466`).
  - AI reasoning is largely remote/opaque in API backend; local repo provides limited transparency into model policy/planning internals (`agent/index.js:921-927`, `agent/lib/sdk.js:418-421`).
  - Tight coupling to proprietary TestDriver API/sandbox infrastructure may hinder reproducibility offline.
  - Markdown/YAML command extraction is regex/parser driven and can be brittle under malformed model output (`agent/lib/parser.js:29-37`, `agent/lib/parser.js:159-195`).

- **Research relevance:**
  - Useful evidence for **single-agent tool-using autonomous UI testing loops** with iterative validation.
  - Demonstrates practical **LLM-to-action translation** via intermediate DSL (YAML command blocks) and execution engine.
  - Good case study for **agent reliability engineering** (retry, healing, loop limits, telemetry) in applied QA automation.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
