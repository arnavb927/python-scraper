---
repo_name: wanshuiyin/Auto-claude-code-research-in-sleep
url: "https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep"
stars: 7256
forks: 681
contributors_count: 52
last_commit_date: "2026-04-21T07:04:09+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T11:23:23.001045+00:00"
model: auto
duration_s: 92.5
clone_size_kb: 34616
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`wanshuiyin/Auto-claude-code-research-in-sleep` (ARIS) is primarily a **Markdown-defined research workflow harness** that users run via slash-style skills (for example `/research-pipeline`, `/auto-review-loop`) inside agent IDEs/CLIs like Claude Code or Codex, rather than a Python app with an internal agent runtime. In practice, a user triggers one command and the skill instructions drive a long pipeline: literature scan, idea generation, experiment execution, external review rounds, and optional paper drafting (`README.md:71-75`, `README.md:188-216`). The repository’s Python code mainly provides helper tools (search/fetch/wiki utilities) and MCP bridge servers that connect to external model backends. The output users get is a structured set of artifacts (`IDEA_REPORT.md`, `AUTO_REVIEW.md`, `NARRATIVE_REPORT.md`, paper drafts), not a packaged service (`AGENT_GUIDE.md:79-97`).

## 2. Agent Framework & Architecture

No LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex framework is used in source code; orchestration is **custom and prompt-driven** through `SKILL.md` files plus MCP tools. A direct repository search finds no framework imports, and the core runtime behavior is specified in skill documents like `skills/auto-review-loop/SKILL.md` and `skills/research-pipeline/SKILL.md`.

Architecture-wise, ARIS is a **two-role cross-model system**: an executor agent (Claude/Codex) performs coding/writing actions, while an external reviewer model (Codex/Gemini/Claude bridge, etc.) critiques and scores results (`AGENT_GUIDE.md:98-105`). The “intelligence” mostly lives in long-form workflow prompts/rules (stop conditions, review parsing, state persistence, escalation modes) in skill files rather than in Python planner classes.

The Python components are integration adapters: MCP servers expose narrow `chat`/`review` APIs (`mcp-servers/llm-chat/server.py:165-233`, `mcp-servers/claude-review/server.py:441-583`), while tool scripts provide deterministic helper operations (arXiv/Exa fetch, DeepXiv wrapper, research wiki ingest), which skills invoke as subprocess commands.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker loop (workflow automation)**, implemented as prompt-level control flow.

- Manager role: the invoking agent follows stage/phase instructions and decides next actions.
- Worker role: external reviewer models return scores/weaknesses; manager applies fixes and iterates.
- Control is sequential with feedback loops and explicit termination criteria (`skills/auto-review-loop/SKILL.md:79-190`).

Example loop control (review -> parse -> stop/continue):

```skills/auto-review-loop/SKILL.md:81-90
#### Phase A: Review
...
mcp__codex__codex:
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    [Round N/MAX_ROUNDS of autonomous review loop]
```

```skills/auto-review-loop/SKILL.md:185-190
- **Score** (numeric 1-10)
- **Verdict** ("ready" / "almost" / "not ready")
...
**STOP CONDITION**: If score >= 6 AND verdict contains "ready" or "almost" → stop loop
```

Concrete cross-agent tool routing appears in MCP bridges, e.g. `review`, `review_reply`, async `review_start`/`review_status` tools (`mcp-servers/claude-review/server.py:441-520`).

## 4. Tools & External Integrations

- **OpenAI-compatible LLM APIs via MCP bridge**: generic `chat` tool calling `/chat/completions` (`mcp-servers/llm-chat/server.py:77-130`, `mcp-servers/llm-chat/server.py:165-228`).
- **MiniMax API via MCP**: dedicated `minimax_chat` tool (`mcp-servers/minimax-chat/server.py:87-121`, `mcp-servers/minimax-chat/server.py:160-231`).
- **Claude CLI as reviewer backend**: subprocess bridge exposing `review*` tools including async jobs (`mcp-servers/claude-review/server.py:175-258`, `mcp-servers/claude-review/server.py:261-383`).
- **Gemini API/CLI reviewer bridge**: backend auto-resolution and job/thread state (`mcp-servers/gemini-review/server.py:34-53`, `mcp-servers/gemini-review/server.py:198-209`).
- **Codex image generation bridge**: async job-based MCP server for generated PNG artifacts under constrained output paths (`mcp-servers/codex-image2/server.py:213-235`, `mcp-servers/codex-image2/server.py:283-300`).
- **Feishu/Lark messaging bridge**: HTTP service for send/poll/reply human checkpoints (`mcp-servers/feishu-bridge/server.py:3-19`, `mcp-servers/feishu-bridge/server.py:175-210`).
- **Web and paper retrieval tools**: Exa search (`tools/exa_search.py:70-87`, `tools/exa_search.py:140-191`), arXiv search/download (`tools/arxiv_fetch.py:60-76`, `tools/arxiv_fetch.py:115-166`), DeepXiv CLI adapter (`tools/deepxiv_fetch.py:17-36`, `tools/deepxiv_fetch.py:129-180`).
- **File-system knowledge base (lightweight RAG-like memory)**: research wiki init/ingest/index/graph utilities (`tools/research_wiki.py:3-20`, `tools/research_wiki.py:61-87`, `tools/research_wiki.py:90-129`).

## 5. Notable Code Walkthrough

- `skills/research-pipeline/SKILL.md:25-33,36-47,124-139`  
  Defines the end-to-end controller pipeline (`idea-discovery -> implement -> run-experiment -> auto-review-loop -> optional paper-writing`), including stage gating and parameter pass-through.

- `skills/auto-review-loop/SKILL.md:16-27,79-109,182-190,350-417`  
  Encodes the multi-round external-review improvement loop, reviewer difficulty modes, stop condition, and persistent state (`REVIEW_STATE.json`) that make the process resumable and autonomous.

- `mcp-servers/claude-review/server.py:175-258,441-583`  
  Implements runtime reviewer calls and MCP tool surface (`review`, `review_reply`, async job start/status), bridging from the executor environment into Claude CLI sessions.

- `mcp-servers/llm-chat/server.py:77-130,165-228`  
  Provides a generic OpenAI-compatible MCP `chat` tool with retries/fallback model behavior; this is the core pluggable reviewer path for non-Claude setups.

- `tools/research_wiki.py:18-30,61-87,131-220`  
  Supplies canonical wiki ingest/index/query-pack helpers that skills use for persistent cross-run memory and structured relationship tracking between papers/ideas/claims.

## 6. Use-Case Mapping

The assigned primary use case (`Code Generation`) is only partially correct. ARIS does include code-writing/experiment-implementation steps, but the repository’s implemented center of gravity is **automating a multi-stage research workflow** with checkpoints, review loops, and artifact handoffs (`skills/research-pipeline/SKILL.md:25-33`, `AGENT_GUIDE.md:81-97`). The most accurate final category is **Workflow Automation**: code generation is one stage inside a broader orchestrated process.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, inspectable orchestration logic in plain Markdown skills (easy to audit/port) (`skills/auto-review-loop/SKILL.md`).
  - Strong separation of executor vs reviewer model families as an explicit protocol (`AGENT_GUIDE.md:98-105`).
  - Practical interoperability through multiple MCP bridges (Claude/Gemini/OpenAI-compatible/MiniMax).
  - Persistent artifact contracts between stages enable long-horizon workflows (`AGENT_GUIDE.md:79-97`).
  - Lightweight architecture with minimal framework lock-in.

- **Limitations:**
  - Critical control logic is prompt text, so behavior consistency depends heavily on model adherence.
  - Limited formal runtime guarantees: no centralized typed state machine or transactional orchestrator.
  - Many integrations are external-process/API wrappers; reliability shifts to environment/config quality.
  - Evaluation/benchmarking of orchestration quality is mostly procedural, not programmatically enforced end-to-end.
  - Safety and correctness checks are distributed across docs/skills/scripts, increasing maintenance complexity.

- **Research relevance:**
  - Useful evidence for **prompt-native multi-agent orchestration** without heavy frameworks.
  - Demonstrates a real-world **cross-model adversarial review loop** pattern for quality improvement.
  - Shows how artifact-based coordination can substitute for explicit agent graph runtimes.
  - Illustrates MCP/tool-bridge ecosystems as infrastructure for heterogeneous agent collaboration.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
