---
repo_name: tirth8205/code-review-graph
url: "https://github.com/tirth8205/code-review-graph"
stars: 12606
forks: 1397
contributors_count: 58
last_commit_date: "2026-04-21T16:48:20+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T11:04:05.105146+00:00"
model: auto
duration_s: 71.2
clone_size_kb: 10522
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`code-review-graph` is an MCP server plus CLI that builds a persistent SQLite knowledge graph of a codebase (parsed with Tree-sitter), then exposes analysis tools for review/debug/refactor workflows. A user typically runs `code-review-graph build` (or `update`) and then `code-review-graph serve`, after which an AI coding client (Claude Code/Cursor/Codex/etc.) can call graph tools like `detect_changes`, `query_graph`, and `get_impact_radius`. The output is structured, token-efficient context (risk scores, affected flows, test gaps, architecture summaries), not generated source code. In practice it automates repository intelligence and review assistance by turning static code into queryable graph data.

## 2. Agent Framework & Architecture

This repo does **not** implement LangGraph/LangChain/AutoGen/CrewAI runtime agents. The concrete framework used is **FastMCP** (`fastmcp`) to expose tools/prompts over MCP, confirmed in `code_review_graph/main.py` and dependencies in `pyproject.toml`.

Architecture-wise, this is a **tooling backend for external agents**, not a multi-agent runtime itself. The core intelligence lives in deterministic analysis modules (`changes.py`, `flows.py`, `graph.py`, `tools/*.py`) and MCP prompt templates (`prompts.py`) that instruct an external LLM how to call tools efficiently. The server registers ~30 MCP tools and 5 MCP prompt templates in `main.py`, then delegates work to pure Python functions (graph queries, risk scoring, flow/community detection, embeddings).

LLM usage is limited to (a) external assistant clients consuming these MCP tools, and (b) optional embedding providers for semantic search (OpenAI-compatible, Gemini, MiniMax, or local sentence-transformers) in `embeddings.py`; there is no internal chat/planner loop orchestrating multiple LLM agents.

## 3. Orchestration Pattern

Closest match: **event-driven tool server + sequential workflow prompts** (single-agent client orchestration).  
It is not manager-worker/swarm/graph-of-agents; control is: client invokes MCP tool -> server function executes -> structured result returned.

Control registration in MCP server:

```78:90:code_review_graph/main.py
mcp = FastMCP(
    "code-review-graph",
    instructions=(
        "Persistent incremental knowledge graph for token-efficient, "
        "context-aware code reviews. Parses your codebase with Tree-sitter, "
        "builds a structural graph, and provides smart impact analysis."
    ),
)

@mcp.tool()
async def build_or_update_graph_tool(
```

Prompt-level sequencing (instructions for one external agent to call tools in order):

```32:41:code_review_graph/prompts.py
def review_changes_prompt(base: str = "HEAD~1") -> list[dict]:
    """Pre-commit review workflow.
    ...
    return [
        {
            "role": "user",
            "content": (
```

And within that content, ordered steps like `get_minimal_context -> detect_changes -> query_graph/get_affected_flows` (`code_review_graph/prompts.py:42-60`), i.e., sequential workflow guidance rather than internal multi-agent routing.

## 4. Tools & External Integrations

- **MCP server transport (stdio / streamable-http)**: tool and prompt exposure via FastMCP in `code_review_graph/main.py:78-995`.
- **Git/SVN subprocess integration**: diff/change detection through `git diff`, `git status`, `svn diff` in `code_review_graph/changes.py:33-132` and `code_review_graph/tools/context.py:16-34`.
- **SQLite graph database**: persistent graph and analytics storage in `code_review_graph/graph.py` (core store), consumed across `code_review_graph/tools/*.py`.
- **Tree-sitter parsing pipeline**: code parsing into graph nodes/edges (wired through build/update commands in `code_review_graph/cli.py:809-854` and parser module).
- **Vector embeddings providers**: local sentence-transformers + cloud APIs (Google Gemini, MiniMax, OpenAI-compatible) in `code_review_graph/embeddings.py:58-643`; wired to tool `embed_graph` in `code_review_graph/tools/docs.py:17-83`.
- **IDE/agent ecosystem integration**: installs MCP configs and hooks for Claude/Cursor/Codex/Windsurf/etc. in `code_review_graph/skills.py:34-355` and `code_review_graph/cli.py:175-293`.
- **No browser automation / web-search agent tooling**: no Playwright/Browserbase style runtime agent tool-use found in source.

## 5. Notable Code Walkthrough

- `code_review_graph/main.py:78-909` - Defines the FastMCP server, registers all MCP tools/prompts, and bridges client calls to analysis functions; this is the runtime entrypoint for “agentic” behavior exposed to external assistants.
- `code_review_graph/prompts.py:15-171` - Encodes five workflow prompt templates (review/debug/onboarding/etc.) that teach an external LLM how to call graph tools in low-token sequences.
- `code_review_graph/tools/review.py:24-468` - Implements high-value review APIs (`get_review_context`, `get_affected_flows`, `detect_changes`) that aggregate graph traversal, diff mapping, and risk/test-gap summaries.
- `code_review_graph/changes.py:33-220` - Parses VCS diffs into changed ranges and maps them to graph nodes; this drives change-impact intelligence rather than LLM reasoning.
- `code_review_graph/embeddings.py:253-515` - Implements provider abstractions and robust OpenAI-compatible embedding calls (retry/error handling/vector alignment), enabling semantic search augmentation.

## 6. Use-Case Mapping

The assigned primary use case (`Code Generation`) looks **incorrect** after reading source code. This repository does not generate code artifacts via LLM planning/execution loops; it provides structured codebase analysis, change-risk assessment, and context retrieval tools for coding assistants. The better category is **Workflow Automation** (with some **RAG + Agents** flavor through graph/embedding retrieval), because it automates review/debug/refactor workflows by serving contextual data to a single external assistant.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong MCP-first architecture with broad, practical tooling surface for real coding workflows (`main.py` tool registry).
  - Deterministic risk/impact pipeline (diff ranges -> graph mapping -> test gaps/priorities) gives inspectable outputs (`changes.py`, `tools/review.py`).
  - Good transport/platform integration (stdio/http + multi-IDE install/hook automation) enables real-world adoption (`cli.py`, `skills.py`).
  - Token-efficiency is explicitly designed in prompts and minimal detail modes (`prompts.py`, `tools/context.py`).
  - Embedding layer supports local/private and multiple cloud backends with careful safety checks (`embeddings.py`).

- **Limitations:**
  - No true runtime multi-agent coordination; “agentic” behavior is delegated to whatever external assistant uses MCP.
  - Prompt workflows are static templates, not adaptive planner/router policies learned from outcomes.
  - Heavy dependence on accurate static parsing/graph quality; dynamic runtime behavior is only approximated via structural analysis.
  - Semantic retrieval quality varies by embedding provider availability and environment setup.
  - Large tool surface may increase client prompt/tool selection overhead without strict tool filtering.

- **Research relevance:**
  - Good evidence for **tool-augmented software engineering assistants** where intelligence is split between deterministic backends and LLM clients.
  - Useful case study of **MCP-based retrieval/analysis middleware** rather than monolithic agent design.
  - Demonstrates practical **token-budget-aware orchestration prompts** for agent tool-use.
  - Relevant for studies on **human-in-the-loop code review automation** and graph-based contextual retrieval.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
