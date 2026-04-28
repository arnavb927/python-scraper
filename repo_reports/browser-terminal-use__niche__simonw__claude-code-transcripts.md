---
repo_name: simonw/claude-code-transcripts
url: "https://github.com/simonw/claude-code-transcripts"
stars: 1460
forks: 159
contributors_count: 3
last_commit_date: "2026-02-12T20:49:10+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-04-27T15:19:10.712588+00:00"
model: auto
duration_s: 54.6
clone_size_kb: 455
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a Python CLI tool that converts Claude Code session logs (`.json`/`.jsonl`) into browsable HTML transcripts, with pagination, timeline indexing, and optional Gist publishing. Users run commands like `claude-code-transcripts`, `claude-code-transcripts json <file>`, `web`, or `all`, and the tool outputs an `index.html` plus `page-XXX.html` files for reading or sharing (`src/claude_code_transcripts/__init__.py:1473-2225`). It parses session messages, renders markdown/tool blocks, and builds project/session archives from local `~/.claude/projects` data or (historically) Claude web API responses (`src/claude_code_transcripts/__init__.py:451-500`, `161-380`, `1947-2097`). In short, it is a transcript extraction and publishing utility, not an LLM runtime.

## 2. Agent Framework & Architecture

No agent framework is used (no LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex imports), and dependencies are standard CLI/rendering/network libraries (`click`, `jinja2`, `httpx`, `questionary`, `markdown`) (`pyproject.toml:11-18`). The core is custom deterministic Python logic in one module, centered on parsing session records and transforming them into HTML templates (`src/claude_code_transcripts/__init__.py:22-35`, `451-500`, `1298-1470`).

There are also no runtime “agents” defined in code. The code *displays* agent-like artifacts from transcripts (e.g., `tool_use`, `tool_result`, `TodoWrite`, `Bash`, `Edit`) but does not execute or orchestrate those tools itself (`src/claude_code_transcripts/__init__.py:746-840`, `865-906`). CLI commands orchestrate file/API input -> render pipeline -> optional browser open/Gist upload (`src/claude_code_transcripts/__init__.py:1480-2221`).

## 3. Orchestration Pattern

Closest match: **other (single-process ETL/render pipeline)**, not multi-agent orchestration.

Control flow is sequential: load/parse session -> split into conversation chunks -> render paginated pages -> render index/statistics.

```1298:1360:src/claude_code_transcripts/__init__.py
def generate_html(json_path, output_dir, github_repo=None):
    ...
    data = parse_session_file(json_path)
    loglines = data.get("loglines", [])
    ...
    conversations = []
    current_conv = None
    for entry in loglines:
        ...
```

Then each conversation is rendered and written to disk, followed by aggregated timeline/index generation:

```1361:1467:src/claude_code_transcripts/__init__.py
for page_num in range(1, total_pages + 1):
    ...
    (output_dir / f"page-{page_num:03d}.html").write_text(...)

...
index_content = index_template.render(...)
index_path = output_dir / "index.html"
index_path.write_text(index_content, encoding="utf-8")
```

Batch mode (`all`) is also sequential manager-style *file processing* (projects/sessions loop), but still not manager-worker LLM agents (`src/claude_code_transcripts/__init__.py:306-380`, `2135-2201`).

## 4. Tools & External Integrations

- **Claude session files on local filesystem**: scans `~/.claude/projects`, reads `.jsonl`, excludes `agent-*` by default (`src/claude_code_transcripts/__init__.py:161-184`, `245-304`, `1521-1533`).
- **Anthropic web endpoints (unofficial)**: fetches session list/data via `httpx` (`/v1/sessions`, `/v1/session_ingress/session/{id}`) (`src/claude_code_transcripts/__init__.py:568-593`).
- **macOS Keychain**: retrieves Claude token with `security find-generic-password` (`src/claude_code_transcripts/__init__.py:508-539`).
- **Local config integration**: reads `~/.claude.json` for org UUID (`src/claude_code_transcripts/__init__.py:541-556`).
- **GitHub CLI (`gh`)**: creates gists from generated HTML (`src/claude_code_transcripts/__init__.py:1251-1287`).
- **Browser integration**: opens output `index.html` using `webbrowser.open` (`src/claude_code_transcripts/__init__.py:1592-1595`, `1723-1725`, `2094-2096`).
- **Jinja2 templating + markdown rendering**: converts transcript blocks into styled HTML (`src/claude_code_transcripts/__init__.py:22-35`, `701-705`, `746-840`).

No MCP servers, vector stores, browser automation frameworks (Playwright/Browserbase), or tool-execution sandbox are wired here.

## 5. Notable Code Walkthrough

- `src/claude_code_transcripts/__init__.py:1298-1470` - Core transcript renderer (`generate_html`): parses loglines, segments conversations, renders paginated HTML pages, computes timeline stats (tool counts/commits), and writes `index.html`.
- `src/claude_code_transcripts/__init__.py:746-840` - Content block renderer: interprets session content types (`text`, `thinking`, `tool_use`, `tool_result`, images) into HTML components; this is where transcript semantics become UI.
- `src/claude_code_transcripts/__init__.py:1947-2097` - `web` command pipeline: resolves credentials, fetches sessions/session payloads via API, optionally filters by repo, then renders HTML output.
- `src/claude_code_transcripts/__init__.py:245-380` - Archive/batch conversion logic (`find_all_sessions`, `generate_batch_html`): groups sessions by project and generates a browsable multi-project archive.
- `tests/test_generate_html.py:61-176` and `tests/test_all.py:167-241` - High-value behavioral tests that validate renderer outputs, pagination/index generation, and archive statistics/failure handling.

## 6. Use-Case Mapping

The assigned primary use case **Browser / Terminal Use** is not the best fit after reading the code. The tool does not operate a browser or terminal agent; instead it automates a document-processing workflow: ingest session records, transform them, and publish/share HTML artifacts.

A better category is **Workflow Automation**. Evidence: end-to-end conversion commands (`local/json/web/all`), batch archive generation, and optional automatic Gist publication (`src/claude_code_transcripts/__init__.py:1480-2221`, `1251-1287`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Solid end-to-end transcript publishing workflow (local, file, API, batch) in one CLI (`src/claude_code_transcripts/__init__.py:1480-2221`).
  - Robust normalization for both JSON and JSONL transcript formats (`src/claude_code_transcripts/__init__.py:451-500`).
  - Rich rendering of tool-centric transcript structure (tool calls/results, commits, images, long-text summaries) (`src/claude_code_transcripts/__init__.py:746-906`).
  - Good practical sharing path via Gist plus hosted-preview URL rewriting (`src/claude_code_transcripts/__init__.py:1144-1249`, `1251-1287`).
  - Broad test coverage around CLI behavior and rendering regressions (`tests/test_generate_html.py`, `tests/test_all.py`).

- **Limitations:**
  - No multi-agent runtime; only post-hoc rendering of agent transcripts (not MAS execution).
  - Core implementation is monolithic in a single large module, which raises maintenance complexity (`src/claude_code_transcripts/__init__.py`).
  - `web` API path is acknowledged as currently broken due to upstream API changes (`README.md:14-17`).
  - Security/privacy controls are minimal when handling potentially sensitive transcript content (no redaction pipeline observed).
  - Dependency on external `gh` CLI for gist publishing adds setup and failure surface (`src/claude_code_transcripts/__init__.py:1280-1286`).

- **Research relevance:**
  - Useful evidence for **agent trace observability tooling**: parsing and visualizing tool-use trajectories from recorded sessions.
  - Demonstrates practical **workflow automation around LLM-generated artifacts**, including indexing, pagination, and publication.
  - Can support studies on **post-hoc analysis of agent behavior** (tool frequency, commit extraction), but not on multi-agent coordination algorithms.
  - Relevant as infrastructure around agent ecosystems rather than an agent framework itself.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
