---
repo_name: Community-Access/accessibility-agents
url: "https://github.com/Community-Access/accessibility-agents"
stars: 241
forks: 25
contributors_count: 9
last_commit_date: "2026-04-16T17:53:38+00:00"
primary_use_case: Simulation
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T17:43:27.876537+00:00"
model: auto
duration_s: 64.8
clone_size_kb: 11311
uses_mas: unknown
final_use_case: unknown
---
## 1. Overview

This repository is an agent pack plus runtime glue for accessibility auditing across Claude Code, GitHub Copilot, and MCP clients. A user typically installs the agent definitions and (optionally) runs the included MCP server to expose accessibility tools like WCAG checks, document scans, and Playwright-based runtime audits. The main output is not a standalone app UI; it is structured agent behavior (specialist prompts, delegation rules, and reports such as `ACCESSIBILITY-AUDIT.md`). In practice, users invoke orchestrator agents (for web/doc audits), which then coordinate specialist roles and produce prioritized findings/fix guidance. It solves a concrete problem: preventing AI coding workflows from shipping inaccessible code/content.

## 2. Agent Framework & Architecture

No LangChain/LangGraph/AutoGen/CrewAI runtime was found in source imports. The executable framework pieces are:
- **Custom prompt-orchestration layer** via markdown agent specs (`.github/agents/*.agent.md`, `.claude/agents/*.md`)
- **VS Code extension routing layer** (`vscode-extension/src/*.ts`)
- **MCP server** built on `@modelcontextprotocol/sdk` (`mcp-server/server-core.js`, `server.js`, `stdio.js`)

The architecture is mostly **configuration-driven multi-agent orchestration**: each agent file declares capabilities (`tools`), allowed subagents (`agents`), and explicit handoff options (`handoffs`). For example, `accessibility-lead`, `web-accessibility-wizard`, and `document-accessibility-wizard` are manager/orchestrator roles, while many specialists are domain workers.

Intelligence primarily lives in long-form system prompts and decision matrices inside agent markdown, with lightweight routing logic in code. The VS Code extension loads `.agent.md` files, parses frontmatter (including handoffs), routes prompts by command/tag/keyword, and builds composite prompts for the selected model
