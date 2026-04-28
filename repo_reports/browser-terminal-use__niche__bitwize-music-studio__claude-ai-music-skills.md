---
repo_name: bitwize-music-studio/claude-ai-music-skills
url: "https://github.com/bitwize-music-studio/claude-ai-music-skills"
stars: 118
forks: 23
contributors_count: 4
last_commit_date: "2026-04-10T15:06:55+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T17:00:21.157098+00:00"
model: auto
duration_s: 85.9
clone_size_kb: 16235
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a Claude Code plugin that encodes an end-to-end music-production workflow around Suno, with skills for concept planning, research, lyric writing, quality checks, mastering, and release prep. A user runs slash commands like `/bitwize-music:researcher`, `/bitwize-music:lyric-writer`, and `/bitwize-music:mastering-engineer`, while the plugin uses an MCP server to query/update project state and trigger tooling (`.claude-plugin/plugin.json:1-13`, `servers/bitwize-music-server/server.py:106-353`). The output is not a standalone app UI; it is a structured terminal-native workflow where the LLM agent(s) guide and execute tasks against markdown project files and local audio assets. In practice, users get guided album/track production with gate checks (e.g., source verification before generation) and automation for media/post-production tasks (`CLAUDE.md:132-171`, `servers/bitwize-music-server/handlers/core.py:945-1007`).

## 2. Agent Framework & Architecture

This is **not** CrewAI/LangGraph/LangChain code. The runtime is a **custom agent architecture built on Claude Code skills + MCP tools**: skill definitions in markdown frontmatter and instructions (`skills/*/SKILL.md`), global routing and policy in `CLAUDE.md`, and a Python `FastMCP` server exposing tool functions (`servers/bitwize-music-server/server.py:66-107`, `:319-353`). The only imported agent framework in code is MCP (`from mcp.server.fastmcp import FastMCP`), not multi-agent libraries.

The architecture is split across:
1) **Behavior layer**: dozens of role-specific skills (research lead, legal researcher, lyric writer, verifier, etc.) that define model tier, allowed tools, and role instructions (`skills/researcher/SKILL.md:1-17`, `skills/researchers-legal/SKILL.md:1-16`).
2) **Control/routing layer**: `CLAUDE.md` and skill docs describe when to route to which skill and required handoffs (`CLAUDE.md:138-157`, `skills/lyric-writer/SKILL.md:486-499`).
3) **Execution/data layer**: MCP tools for state cache, track mutation, path resolution, gating, audio/promo processing, DB operations (`servers/bitwize-music-server/server.py:338-353`, `handlers/core.py:854-1143`).

The “intelligence” largely lives in prompt-like skill instructions and role decomposition, while Python primarily provides deterministic tool APIs and validators.

## 3. Orchestration Pattern

Closest pattern: **hierarchical (manager-worker) workflow orchestration** with staged gates.

- The `researcher` skill acts as coordinator and explicitly delegates to specialized non-user-invocable researcher agents, then hands to a verifier before human review (`skills/researcher/SKILL.md:241-259`, `skills/researchers-verifier/SKILL.md:47-61`).
- The system also enforces sequential production stages (research -> verification -> writing -> generation -> final) through routing rules and status transitions (`CLAUDE.md:134-205`, `handlers/core.py:927-977`).

Example control-flow excerpts:

```241:250:skills/researcher/SKILL.md
## Coordinating Specialist Researchers

For deep research, coordinate with specialized researchers:

| Specialist | Domain |
|------------|--------|
| `researchers-legal` | Court documents, indictments, sentencing |
| `researchers-gov` | DOJ/FBI/SEC press releases |
```

```945:960:servers/bitwize-music-server/handlers/core.py
# Pre-generation gate enforcement: block transition to "Generated" if gates fail
if field_key == "status" and not force:
    canonical_new = _CANONICAL_TRACK_STATUS.get(value.lower().strip(), value)
    if canonical_new == TRACK_GENERATED:
        ...
        if gate_blocking > 0:
            return _safe_json({
                "error": f"Cannot transition to 'Generated' — {gate_blocking} pre-generation gate(s) failed",
```

## 4. Tools & External Integrations

- **MCP (Model Context Protocol) server** for structured tool calls from skills (`.mcp.json:1-9`, `servers/bitwize-music-server/server.py:66-107`).
- **Filesystem/state cache + markdown parsing** for albums/tracks/session context (`tools/state/indexer.py`, `servers/bitwize-music-server/handlers/core.py:105-355`).
- **Web search/fetch via skill-allowed tools** (used in research roles; not Python API wrappers in repo) (`skills/researcher/SKILL.md:8-16`, `skills/researchers-verifier/SKILL.md:8-16`).
- **Audio/video processing dependencies** like `ffmpeg`, `numpy/scipy/soundfile/pyloudnorm`, `matchering`, AnthemScore via processing handlers/tools (`handlers/processing/_helpers.py:53-193`, `handlers/processing/video.py:50-83`).
- **Cloud object storage** upload to **Cloudflare R2 / AWS S3** through boto3 (`tools/cloud/upload_to_cloud.py:86-131`, `:252-325`).
- **PostgreSQL** integration for tweet/promo content via `psycopg2` and MCP DB handlers (`tools/database/connection.py:14-81`, `server.py:323-353`).
- **Optional browser automation dependency** (`playwright`) documented for document retrieval workflows (`servers/bitwize-music-server/README.md:31-33`).

## 5. Notable Code Walkthrough

- `servers/bitwize-music-server/server.py:106-353` — Initializes `FastMCP`, wires shared cache state, and registers all tool modules; this is the runtime backend every skill depends on for structured operations.
- `servers/bitwize-music-server/handlers/core.py:854-1057` — Implements `update_track_field` with transition validation and hard workflow gates (source links required, pre-generation checks, Suno link checks), turning instructions into enforceable state logic.
- `skills/researcher/SKILL.md:241-331` — Defines lead-researcher behavior, specialist delegation map, and required output artifacts (`RESEARCH.md`, `SOURCES.md`), showing explicit multi-role coordination design.
- `skills/researchers-verifier/SKILL.md:47-137` — Represents a dedicated QA agent role in the pipeline, separate from gatherers, with formal verification report structure before human approval.
- `CLAUDE.md:48-113` and `:132-171` — Global orchestration spec: MCP-first access pattern, workflow stage order, and routing rules among major skills.

## 6. Use-Case Mapping

The assigned primary use case (`Browser / Terminal Use`) is **partially true but not the best fit**. The core of this repo is a **workflow-automation framework** for AI-assisted music production in Claude Code: it orchestrates roles, enforces status gates, and automates local processing/cloud upload steps (`CLAUDE.md:134-170`, `handlers/core.py:945-1007`). Browser use appears mainly as a support capability inside research/document-hunting (WebFetch/WebSearch, optional Playwright), not the central architecture (`skills/researcher/SKILL.md:8-16`, `servers/bitwize-music-server/README.md:31-33`).  
**Better category: Workflow Automation.**

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear role decomposition (lead researcher + specialist subagents + verifier) with explicit handoffs.
  - Strong procedural guardrails: source verification and generation/finalization gates are codified, not just suggested.
  - Practical MCP backend with rich state/query/update tooling for reliable agent actions.
  - Real-world integration breadth (audio tooling, cloud uploads, DB), showing agent workflows beyond toy chat tasks.

- **Limitations:**
  - Multi-agent orchestration is mostly prompt/instruction-driven; there is limited explicit runtime planner/graph code in Python.
  - Heavy dependence on Claude Code skill-routing semantics makes portability to other runtimes/frameworks harder.
  - Some claims in docs (tool counts/scale) are hard to verify directly without executing full environment.
  - Determinism/reproducibility of agent delegation behavior may vary because control logic is partly natural-language policy.

- **Research relevance:**
  - Useful evidence of **instruction-governed multi-agent workflows** (hierarchical specialization) in production-like creative pipelines.
  - Demonstrates coupling of LLM role orchestration with strict deterministic gates via external tool APIs.
  - Illustrates a hybrid architecture where “agent cognition” is declarative (skill prompts) and execution is procedural (MCP tools/state engine).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
