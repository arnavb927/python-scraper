---
repo_name: dontriskit/awesome-ai-system-prompts
url: "https://github.com/dontriskit/awesome-ai-system-prompts"
stars: 5777
forks: 865
contributors_count: 6
last_commit_date: "2026-02-20T19:10:13+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T12:07:58.039312+00:00"
model: auto
duration_s: 55.0
clone_size_kb: 1636
uses_mas: no
final_use_case: None
---
## 1. Overview

This repository is primarily a curated dataset of system prompts, tool schemas, and prompt-engineering notes for many AI products (ChatGPT, Claude Code, Cline, Manus, v0, etc.), not a runnable agent application. A user does not run a single orchestrator here; instead they browse and reuse prompt files, JSON tool definitions, and a few extraction scripts for collecting prompts from other codebases. The most “executable” pieces are utility scripts for prompt extraction (for example in `Blackbox.ai/extraction-scripts`) and stored prompt templates in `.md`, `.txt`, `.js`, and `.ts` files. In practice, users get reference material for designing their own agents rather than an agent system that runs end-to-end in this repo.

## 2. Agent Framework & Architecture

No concrete runtime agent framework (LangGraph, LangChain, CrewAI, AutoGen, LlamaIndex, etc.) is implemented in this repository. I did not find framework imports or an executable multi-agent runtime; the files largely store prompt text and tool schemas.

The architecture is content-oriented: prompts are organized by product/vendor directories, and many files are snapshots of system prompts or tool descriptions. For example, `Cline/system.ts` exports a large prompt template string (`SYSTEM_PROMPT`) and instruction-merging helper, while `Manus/tools.json` stores function schemas. These define *how an external agent should behave*, but the orchestration engine is outside this repo.

There are a few scripts used for extraction/processing of prompts, such as `Blackbox.ai/extraction-scripts/v4.py`, which parse template literals and filter likely prompts. That script performs regex-based text mining, not LLM-agent execution.

## 3. Orchestration Pattern

Closest match: **other (documentation/prompt corpus, not runtime orchestration)**.

There is no control-flow implementation between agents in code. What exists are *descriptions* of orchestration in prompt text intended for other systems. For example:

- `Cline/system.ts:16-19` describes sequential tool use in plain prompt text:
```16:19:Cline/system.ts
TOOL USE
...
You can use one tool per message, and will receive the result of that tool use in the user's response.
```

- `Manus/AgentLoop.txt` and `README.md` describe an “agent loop” conceptually, but this repo does not implement the loop executor:
```191:200:README.md
<agent_loop>
You are operating in an agent loop, iteratively completing tasks through these steps:
1. Analyze Events...
2. Select Tools...
3. Wait for Execution...
...
</agent_loop>
```

So control flow is documented as prompt instructions, not enforced by code in this repository.

## 4. Tools & External Integrations

This repo does **not** wire tools into a running agent process. It stores schemas/instructions for external tools:

- Tool schema catalog in `Manus/tools.json` (file ops, shell, browser actions, web search, deployment, etc.), e.g. `shell_exec`, `browser_navigate`, `info_search_web`.
- Prompt-level tool specs in `Cline/system.ts` (`execute_command`, `read_file`, `replace_in_file`, optional `browser_action`, optional MCP calls).
- Claude Code prompt fragments in `Claude-Code/*.js` describing subagents and batch execution behavior.
- MCP is only referenced in prompt text (`Cline/system.ts` includes `use_mcp_tool` / `access_mcp_resource` instructions), not connected by executable project code here.
- Extraction utilities (`Blackbox.ai/extraction-scripts/v4.py`) use Python stdlib (`re`, `os`) to mine prompt templates; no LLM API integration is present there.

## 5. Notable Code Walkthrough

- `Cline/system.ts:7-14,16-49,215-240` - Exports a giant system-prompt generator and embeds tool-call syntax/contracts (`execute_command`, `read_file`, completion protocol). This is representative of the repo’s core pattern: storing prompts as code strings.
- `Manus/tools.json:1-614` - Structured JSON function schema list (messaging, filesystem, shell, browser, web search, deployment). It matters because it captures a full agent tool surface in machine-readable form.
- `Claude-Code/AgentTool.js:1-21` - Prompt text for launching a subagent and guidance on when to delegate. Important as an example of multi-agent behavior being documented, not executed.
- `Claude-Code/BatchExecutionTool.js:1-47` - Prompt text describing parallel/batched tool invocation semantics; again, design artifact rather than runtime.
- `Blackbox.ai/extraction-scripts/v4.py:74-186` - Actual executable script that extracts probable prompt templates from JS template literals using heuristics; shows the repo’s practical code use is dataset extraction/curation.

## 6. Use-Case Mapping

The assigned category **Browser / Terminal Use** looks incorrect for this repository itself. While many stored prompts describe browser/shell-capable agents, this repo does not implement and run such an agent runtime.

A better category is **None** (from the provided list), because this is an awesome-list/prompt corpus with light extraction scripts, not an operational agent system. If forced into closest functional behavior, it resembles prompt curation/workflow documentation more than any runtime agent category.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad cross-platform coverage of real-world system prompts across many major AI products.
  - Includes both human-readable prompt docs and machine-readable tool schemas (e.g., `Manus/tools.json`).
  - Captures concrete operational patterns (tool protocols, refusal policies, agent-loop templates) useful for comparative analysis.
  - Contains extraction scripts that make corpus-building reproducible to some degree.

- **Limitations:**
  - No executable multi-agent runtime; cannot validate claimed behaviors end-to-end in this repo.
  - Limited provenance/normalization guarantees for prompt snapshots (version drift and authenticity risks).
  - Minimal test harnessing/CI for verifying prompt schema consistency or behavior.
  - Architecture labels in metadata can be misleading because repository content is mostly static artifacts.

- **Research relevance:**
  - Useful as a qualitative corpus for studying prompt-based governance of tool-using agents.
  - Supports comparative taxonomy work on agent instruction design (tool constraints, safety policies, control-loop phrasing).
  - Serves as evidence of industry prompt conventions, but not of runtime MAS performance or coordination efficacy.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
