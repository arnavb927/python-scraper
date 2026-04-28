---
repo_name: breaking-brake/cc-wf-studio
url: "https://github.com/breaking-brake/cc-wf-studio"
stars: 4884
forks: 543
contributors_count: 5
last_commit_date: "2026-04-19T08:28:22+00:00"
primary_use_case: RAG + Agents
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T13:21:20.660280+00:00"
model: auto
duration_s: 93.2
clone_size_kb: 26174
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`cc-wf-studio` is a VS Code extension for visually designing and running AI-agent workflows, then exporting them into executable agent artifacts (for Claude Code, Codex CLI, Copilot, Gemini, Roo, Cursor, etc.). A user opens the editor command, creates a graph of nodes (sub-agents, prompts, branching, MCP tool calls, skills), and runs or exports that workflow into provider-specific command/skill files. The extension can also launch an AI-editing skill that lets an external agent read and modify workflows through a built-in MCP server. In practice, users get a workflow canvas plus generated runnable agent instructions, not a standalone in-repo agent runtime.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen as a core runtime framework. I found no such imports or dependencies; instead it uses custom TypeScript orchestration plus provider CLIs/APIs (`nano-spawn`, VS Code LM API, MCP SDK) (`package.json:133-141`, `src/extension/services/ai-provider.ts:12-38`).

Architecture-wise, the “intelligence” is split across:  
1) prompt builders for workflow/refinement generation (`src/extension/services/refinement-service.ts:186-227`, `:256-420`),  
2) workflow-to-agent instruction compilers (`src/extension/services/workflow-prompt-generator.ts:593-983`), and  
3) an MCP bridge that lets external agents read/apply workflow JSON (`src/extension/services/mcp-server-service.ts:54-176`, `src/extension/services/mcp-server-tools.ts:33-581`).

The repo models multiple agent roles via workflow node types (`subAgent`, `subAgentFlow`, `mcp`, `codex`, branching nodes), then exports these into provider-native command/skill formats (`src/shared/types/workflow-definition.ts:11-25`, `src/extension/services/export-service.ts:83-153`). So multi-agent behavior is primarily **specified and delegated** to external LLM runtimes rather than executed by an internal graph engine.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker workflow automation** (with graph-shaped control flow).  
- A parent workflow routes work through node transitions (prompt, branch, tool, sub-agent).  
- Sub-agent nodes represent worker delegation, including explicit parallelization guidance for built-in types.

Control-flow evidence (workflow DSL + generated execution guide):

```664:716:src/extension/services/workflow-prompt-generator.ts
// Sub-Agent node details
if (subAgentNodes.length > 0) {
  // ...
  sections.push(`#### ${nodeId}(Sub-Agent: ${agentName})`);
  // ...
  if (node.data.builtInType) {
    sections.push('**Parallel Execution**: enabled');
    sections.push('If so, launch multiple agents of the same subagent_type in parallel ...');
    sections.push('- Wait for all agents to complete before proceeding to the next node');
  }
}
```

```207:255:src/extension/services/workflow-prompt-generator.ts
for (const conn of connections) {
  const fromId = sanitizeNodeId(conn.from);
  const toId = sanitizeNodeId(conn.to);
  // branch/ifElse/switch labels determine routing
  lines.push(`    ${fromId} -->|${escapeLabel(branch.label)}| ${toId}`);
}
```

## 4. Tools & External Integrations

- **MCP server (built-in, localhost HTTP):** exposes workflow CRUD/edit tools to external agents (`get_current_workflow`, `apply_workflow`, `update_nodes`, etc.) in `src/extension/services/mcp-server-service.ts:54-176` and `src/extension/services/mcp-server-tools.ts:33-581`.
- **External LLM runtimes:** Claude Code CLI, Codex CLI, Copilot (VS Code LM API), routed by `src/extension/services/ai-provider.ts:99-218`; concrete adapters in `claude-code-service.ts` and `codex-cli-service.ts`.
- **Terminal execution:** runs generated workflows as slash commands/skills (`claude "/workflow"`, `codex "$skill"`, `copilot -i ":skill ..."`) in `src/extension/services/terminal-execution-service.ts:43-197`.
- **Provider-specific skill launch/export:** writes skill files and launches agent environments (Claude/Copilot/Codex/Roo/Gemini/Cursor/Antigravity) in `src/extension/services/ai-editing-skill-service.ts:32-199`.
- **Slack integration:** share/import workflows through Slack API in command handlers wired from `open-editor.ts` (e.g., `src/extension/commands/open-editor.ts:1330-1456`).
- **Filesystem workflow store:** `.vscode/workflows/*.json` and generated `.claude/.codex/.github/...` artifacts via export/file services (`src/extension/services/export-service.ts:91-153`).

No vector DB or semantic retrieval stack (e.g., Pinecone/Chroma/pgvector) appears in code.

## 5. Notable Code Walkthrough

- `src/extension/commands/open-editor.ts:279-2203` — central message router for the webview; orchestrates save/load/export/run actions, AI refinement requests, MCP server lifecycle, and provider-specific execution paths.
- `src/extension/services/refinement-service.ts:256-772` — main AI refinement pipeline: load schema + skills, build prompt, call provider, parse structured JSON response, validate, and reconcile workflow metadata.
- `src/extension/services/workflow-prompt-generator.ts:593-983` — compiles node graph into executable textual instructions (including sub-agent behavior, MCP tool modes, branching semantics, codex command snippets).
- `src/extension/services/mcp-server-tools.ts:33-581` — defines MCP tools external agents use to inspect and mutate the live canvas safely with validation and optional user review.
- `src/extension/services/export-service.ts:83-153` — exports visual workflows into concrete runnable files (`.claude/agents`, `.claude/commands`) and sub-agent-flow agent files.

## 6. Use-Case Mapping

The assigned label `RAG + Agents` looks **partially wrong**. The repository clearly supports agents (including multi-agent delegation via sub-agent nodes), but I did not find a typical RAG pipeline (no embedding store/retriever/vector index orchestration). Instead, it is best categorized as **Workflow Automation**: a visual system for designing, validating, exporting, and running agent workflows across multiple AI runtimes (`open-editor.ts:475-997`, `export-service.ts:389-469`, `terminal-execution-service.ts:43-69`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Multi-provider portability: same workflow model targets Claude, Codex, Copilot, Gemini, Roo, Cursor (`open-editor.ts:590-997`).
  - Strong MCP-based live editing loop for external agents with conflict/review handling (`mcp-server-tools.ts:153-256`, `mcp-server-service.ts:293-370`).
  - Clear typed workflow schema with explicit agent/tool/branch node semantics (`workflow-definition.ts:11-602`).
  - Practical execution bridge from design-time graph to runnable CLI commands (`export-service.ts:389-469`, `terminal-execution-service.ts:43-197`).
  - Built-in support for sub-agent decomposition and parallel delegation guidance (`workflow-prompt-generator.ts:665-717`).

- **Limitations:**
  - No native in-process agent runtime/graph executor; execution semantics are offloaded to external model tooling.
  - “Parallel execution” is instruction-level policy text, not enforced scheduler logic in this codebase.
  - Heavy reliance on external CLI behavior and availability (Claude/Codex/Copilot differences can affect consistency).
  - Limited direct observability of real agent internals beyond streamed text/tool events.
  - RAG-specific retrieval components are not implemented as first-class primitives.

- **Research relevance:**
  - Good evidence of **human-in-the-loop agent orchestration tooling** (visual design + AI-assisted refinement + review-before-apply).
  - Useful case of **cross-agent interoperability via MCP** for live artifact editing.
  - Shows a practical **specification-to-execution** pattern where workflows compile into provider-specific agent instructions.
  - Demonstrates multi-agent decomposition as a UX/runtime contract rather than embedded MAS framework code.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
