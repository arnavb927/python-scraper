---
repo_name: alirezarezvani/claude-skills
url: "https://github.com/alirezarezvani/claude-skills"
stars: 12374
forks: 1630
contributors_count: 21
last_commit_date: "2026-04-13T08:45:04+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T07:01:08.001613+00:00"
model: auto
duration_s: 95.5
clone_size_kb: 27410
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a large **skill/plugin library** for agentic coding assistants (Claude Code, Codex, Cursor, Gemini CLI, etc.), not a single runnable app. Users install a skill folder (for example `engineering/agenthub` or `engineering/llm-wiki`) and then run slash commands that define workflows for agents and subagents. The repository provides: (a) prompt/role specs for agents, (b) command playbooks, and (c) Python utility scripts that support those workflows with deterministic file/git operations. In practice, a user gets reusable “agent operating systems” (e.g., multi-agent tournaments, wiki-maintenance assistants) that can be dropped into their own assistant runtime.

## 2. Agent Framework & Architecture

No LangGraph/LangChain/CrewAI/AutoGen runtime is implemented in Python here; imports for those frameworks are absent in `.py` code (`rg` over `*.py` found no matches). The orchestration is mostly **custom prompt-driven architecture** designed for host environments (Claude Code/Codex/Cursor) that provide an `Agent`/subagent tool.

The clearest MAS implementation is `engineering/agenthub`, where one coordinator agent controls N worker agents. The coordinator lifecycle and protocol are encoded in skill docs and agent specs (`engineering/agenthub/skills/agenthub/SKILL.md:55-97`, `engineering/agenthub/agents/hub-coordinator.md:11-71`), while Python scripts manage session state, message board files, branch/worktree metadata, and evaluation (`engineering/agenthub/skills/agenthub/scripts/*.py`).

A second architecture appears in `engineering/llm-wiki`: specialized subagents (`wiki-ingestor`, `wiki-librarian`, `wiki-linter`) are dispatched per command (`engineering/llm-wiki/skills/llm-wiki/SKILL.md:90-97`, `engineering/llm-wiki/commands/wiki-ingest.md:33-36`). “Intelligence” primarily lives in markdown prompts/workflows; scripts are support tooling and explicitly avoid LLM calls (`engineering/llm-wiki/skills/llm-wiki/scripts/ingest_source.py:5-8`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker), with parallel fan-out/fan-in**.

Coordinator assigns work, waits, evaluates, merges winner; workers do isolated execution. This is explicit in `hub-coordinator` and `spawn` command specs:

```19:26:engineering/agenthub/agents/hub-coordinator.md
Agent(
  prompt: "You are agent-{i} in hub session {session-id}. Your task: {task}.
           Read your assignment at .agenthub/board/dispatch/{seq}-agent-{i}.md.
           Work in your worktree, commit all changes, then write your result
           summary to .agenthub/board/results/agent-{i}-result.md and exit.",
  isolation: "worktree"
)
```

```35:40:engineering/agenthub/skills/spawn/SKILL.md
1. Load session config from `.agenthub/sessions/{session-id}/config.yaml`
2. For each agent 1..N:
   - Write task assignment to `.agenthub/board/dispatch/`
   - Build agent prompt with task, constraints, and board write instructions
3. Launch ALL agents in a **single message** with multiple Agent tool calls:
```

State transitions are a simple linear machine (`init -> running -> evaluating -> merged/archived`) enforced in code (`engineering/agenthub/skills/agenthub/scripts/session_manager.py:25-33`, `157-180`).

## 4. Tools & External Integrations

- **Host agent runtime (Claude Code/Codex/OpenClaw Agent tool):** orchestration assumes spawning subagents via `Agent(...)` calls (`engineering/agenthub/agents/hub-coordinator.md:17-26`, `engineering/agenthub/skills/spawn/SKILL.md:41-63`).
- **Git + git worktree isolation:** core execution substrate for parallel agents and cleanup (`engineering/agenthub/skills/agenthub/SKILL.md:72-76`, `92-95`; `engineering/agenthub/skills/agenthub/scripts/session_manager.py:191-207`; `result_ranker.py:63-78`).
- **Filesystem message board (.agenthub):** append-only coordination channels (`dispatch/progress/results`) implemented via file posts (`engineering/agenthub/skills/agenthub/SKILL.md:145-177`; `board_manager.py:122-162`).
- **Shell command evaluation:** per-agent metric evaluation executes arbitrary eval command in each worktree (`engineering/agenthub/skills/agenthub/scripts/result_ranker.py:81-89`, `244-252`).
- **Obsidian markdown vault integration (llm-wiki):** workflow assumes vault structure + index/log maintenance (`engineering/llm-wiki/skills/llm-wiki/SKILL.md:32-53`, `125-133`).
- **Local retrieval utilities (no external vector DB):** BM25 fallback search and graph/lint scripts (`engineering/llm-wiki/skills/llm-wiki/SKILL.md:108-111`; `commands/wiki-query.md:25-27`).
- **External APIs/services:** no mandatory paid API wiring in core scripts; Python tools are stdlib-only and generally local (`engineering/llm-wiki/skills/llm-wiki/SKILL.md:100-101`).

## 5. Notable Code Walkthrough

- `engineering/agenthub/skills/agenthub/scripts/hub_init.py:23-103,171-253`  
  Initializes collaboration sessions, creates `.agenthub` directory structure, writes `config.yaml` + `state.json`, and validates git-repo prerequisites.

- `engineering/agenthub/skills/agenthub/scripts/session_manager.py:25-33,157-210`  
  Implements the session state machine and lifecycle controls, including legal transition checks and worktree cleanup logic.

- `engineering/agenthub/skills/agenthub/scripts/result_ranker.py:81-116,230-312`  
  Executes eval commands in each agent worktree, extracts metrics via regex, combines with git diff stats, and ranks competing agent branches.

- `engineering/agenthub/agents/hub-coordinator.md:11-80`  
  Defines the orchestrator agent contract: dispatch, monitor, evaluate, merge, plus hard rules (immutability, wait-for-all, archive losers).

- `engineering/llm-wiki/agents/wiki-librarian.md:24-76`  
  Representative specialized subagent prompt: index-first retrieval, citation constraints, optional write-back to persistent wiki pages.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially accurate. This repo does involve terminal-centric execution (git, shell eval commands, CLI scripts), but its dominant behavior is reusable **agent workflow orchestration** across domains (engineering, product, marketing, compliance), not browser automation as a primary modality.

A better primary category is **Workflow Automation**: skills encode repeatable multi-step procedures, often with role-specialized agents/subagents and deterministic helper scripts (`engineering/agenthub/skills/agenthub/SKILL.md`, `engineering/llm-wiki/commands/*.md`). Browser use exists in some skills, but is not the core architectural center of the repository.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear manager-worker MAS pattern with explicit lifecycle and governance rules (`hub-coordinator`, `spawn`, `session_manager`).
  - Practical parallelization strategy using git worktrees for isolation and reproducibility.
  - Good separation of concerns: prompt orchestration in markdown, deterministic mechanics in Python scripts.
  - Portable design across multiple agent runtimes and tooling ecosystems.
  - Strong operational artifacts (state files, board posts, logs) useful for auditability.

- **Limitations:**
  - Multi-agent coordination is mostly specified in prompts/docs; limited executable enforcement of agent-behavior constraints.
  - No centralized runtime engine akin to LangGraph/CrewAI for robust scheduling/retries/observability.
  - Evaluation is mostly regex metric parsing or human/LLM judging; limited statistical rigor.
  - Heavy reliance on host tool semantics (`Agent` behavior differs across platforms).
  - Many components are templates/specs; fewer end-to-end integration tests for MAS workflows.

- **Research relevance:**
  - Evidence of **LLM-agent orchestration as protocol engineering** (prompt contracts + lightweight control scripts).
  - Useful case study for **filesystem-mediated coordination** (blackboard-like channels) in practical agent systems.
  - Demonstrates **parallel competitive agent strategy** (tournament-style selection with merge of winner).
  - Illustrates cross-platform “agent skill” packaging as a software distribution model for MAS behaviors.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
