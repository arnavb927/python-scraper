---
repo_name: shanraisshan/claude-code-best-practice
url: "https://github.com/shanraisshan/claude-code-best-practice"
stars: 47445
forks: 4666
contributors_count: 4
last_commit_date: "2026-04-22T17:17:05+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T10:20:31.111349+00:00"
model: auto
duration_s: 73.3
clone_size_kb: 118629
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a **configuration-and-workflow template** for Claude Code, not a traditional Python/JS app. A user runs slash commands (for example `/weather-orchestrator` or workflow-maintenance commands) inside Claude Code, and those commands dispatch subagents and skills to complete structured tasks like fetching weather, generating SVG output files, or auditing documentation drift. The main deliverable is reproducible agentic workflows defined in Markdown/YAML (`.claude/commands`, `.claude/agents`, `.claude/skills`) plus hook automation in Python (`.claude/hooks/scripts/hooks.py`). In practice, users get orchestrated multi-step outcomes (reports, updated markdown/docs, generated assets) from one command invocation.

## 2. Agent Framework & Architecture

This repo uses a **custom Claude Code native agent framework** (commands + subagents + skills + hooks), not LangGraph/LangChain/CrewAI runtime code. Evidence: orchestration is declared in command files with explicit `Agent` and `Skill` tool usage (`.claude/commands/weather-orchestrator.md:1-59`, `.claude/commands/workflows/development-workflows.md:55-210`), while agents are defined via frontmatter (`.claude/agents/weather-agent.md:1-35`, `.claude/agents/workflows/best-practice/workflow-claude-subagents-agent.md:1-18`).

Architecture is hierarchical and role-based: a top-level command acts as coordinator, dispatches one or more specialized subagents, and then invokes skills for deterministic subtasks. For instance, `/weather-orchestrator` forces a three-step flow: ask user unit → call `weather-agent` → call `weather-svg-creator` (`.claude/commands/weather-orchestrator.md:24-50`). The `weather-agent` itself is constrained to invoke `weather-fetcher` through `Skill` and explicitly forbids direct API calls (`.claude/agents/weather-agent.md:41-70`).

A second layer of system behavior comes from lifecycle hooks configured globally in `.claude/settings.json` and executed by Python (`.claude/settings.json:86-443`, `.claude/hooks/scripts/hooks.py:423-481`). So “intelligence” is split across: (1) prompt contracts in command/agent markdown, (2) skill instructions, and (3) deterministic hook middleware.

## 3. Orchestration Pattern

Closest pattern: **hierarchical (manager-worker) orchestration** with some sequential pipeline behavior.

Control flow is explicit: command (manager) delegates to agent (worker), then invokes a finishing skill.

```24:50:.claude/commands/weather-orchestrator.md
### Step 2: Fetch Weather Data via Agent
Use the Agent tool to invoke the weather agent:
- subagent_type: weather-agent
...
### Step 3: Create SVG Weather Card
Use the Skill tool to invoke the weather-svg-creator skill:
- skill: weather-svg-creator
```

The worker agent is itself constrained to a single specialized skill call and return contract:

```53:70:.claude/agents/weather-agent.md
1. **Invoke**: Call the Skill tool with `skill: weather-fetcher`
...
### Step 1: Invoke weather-fetcher skill
Skill(skill: "weather-fetcher")
...
If the Skill tool invocation does not return a numeric temperature and unit, DO NOT attempt to fetch the data yourself.
```

For larger workflows, the same manager-worker pattern scales to **parallel fan-out** (e.g., launch 2 research agents concurrently, then merge) in `.claude/commands/workflows/development-workflows.md:55-153`.

## 4. Tools & External Integrations

- **Claude Code built-in tools (Agent, Skill, AskUserQuestion, Read/Write/Edit/Bash/WebFetch/WebSearch)** wired in command/agent frontmatter and instructions (`.claude/commands/weather-orchestrator.md:4-7`, `.claude/agents/workflows/best-practice/workflow-claude-subagents-agent.md:6-17`).
- **Open-Meteo HTTP API** for live weather retrieval, called via `WebFetch` in skill instructions (`.claude/skills/weather-fetcher/SKILL.md:19-30`).
- **GitHub API + docs URLs** for drift-research agents (`.claude/commands/workflows/best-practice/workflow-claude-subagents.md:26-35`, `.claude/agents/development-workflows-research-agent.md:34-57`).
- **Shell/terminal execution** for timezone/time retrieval (`agent-teams/.claude/agents/time-agent.md:16-21`) and generally allowed in research agents (`.claude/agents/development-workflows-research-agent.md:6-17`).
- **MCP servers** configured at project level: Playwright MCP, Context7 MCP, DeepWiki MCP (`.mcp.json:2-24`), plus broad MCP permissions in settings (`.claude/settings.json:11-19`).
- **Hook runtime (Python)** triggered on many lifecycle events (PreToolUse, PostToolUse, SubagentStart, etc.), including logging and sound notifications (`.claude/settings.json:86-443`, `.claude/hooks/scripts/hooks.py:29-71`, `.claude/hooks/scripts/hooks.py:312-350`).

## 5. Notable Code Walkthrough

- `.claude/commands/weather-orchestrator.md:14-59`  
  Defines a strict end-to-end orchestration contract: user elicitation, delegated weather fetch via subagent, then SVG generation via skill, with fail-closed guards.

- `.claude/agents/weather-agent.md:1-84`  
  Core specialist worker definition; binds model/tool limits, preloads `weather-fetcher`, and enforces “must use Skill tool” behavior to prevent ad-hoc API access.

- `.claude/skills/weather-fetcher/SKILL.md:1-48`  
  Encapsulates external API retrieval logic (Open-Meteo URLs, required JSON fields, output schema), separating data-fetch procedure from orchestration policy.

- `.claude/commands/workflows/development-workflows.md:55-210`  
  Representative multi-agent “team” workflow: mandatory parallel agent launch, merge/report phases, changelog append, and badge update.

- `.claude/hooks/scripts/hooks.py:29-77` and `.claude/hooks/scripts/hooks.py:423-481`  
  Deterministic middleware that executes on hook events, maps events to actions (sounds/logging), and avoids blocking the main agent flow.

## 6. Use-Case Mapping

The assigned use case (`Code Generation`) is **partially true but not primary**. The repository’s implemented runtime focuses more on **workflow automation of AI operations**: orchestrating agent calls, fetching external data, producing structured reports/artifacts, and maintaining docs/changelogs via command pipelines (`.claude/commands/workflows/*`, `.claude/commands/weather-orchestrator.md`). There is no central code-synthesis engine or compiler/test loop architecture typical of dedicated code-generation systems. Better category: **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, enforceable agent contracts with explicit forbidden actions and fail-closed logic (`.claude/commands/weather-orchestrator.md:16-23`, `.claude/agents/weather-agent.md:43-50`).
  - Strong separation of concerns: orchestration (commands) vs specialist behavior (agents) vs reusable procedures (skills).
  - Demonstrates both sequential and parallel multi-agent control patterns (`.claude/commands/workflows/development-workflows.md:55-153`).
  - Extensive lifecycle hook integration for observability and deterministic side behavior (`.claude/settings.json:86-443`, `.claude/hooks/scripts/hooks.py:312-350`).

- **Limitations:**
  - Most “logic” is prompt-in-markdown; limited static guarantees or typed state transitions compared to code-first orchestrators.
  - Heavy dependence on Claude Code runtime semantics; portability to other MAS frameworks is low.
  - Some agent definitions rely on broad tool permissions (`Bash(*)`, `WebFetch(*)`) which can increase operational risk (`.claude/agents/development-workflows-research-agent.md:6-17`).
  - Sparse automated tests for workflows/hook behavior; reliability is mostly policy-based.

- **Research relevance:**
  - Good evidence of **declarative multi-agent orchestration** in production-like developer tooling.
  - Useful case for studying **guardrail prompts as control policy** (forbidden tools, mandatory delegation, fail-closed checks).
  - Demonstrates integration of **agentic workflows + deterministic event hooks** as a hybrid architecture.
  - Provides concrete artifacts for analyzing human-in-the-loop governance (approval gates before applying actions).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
