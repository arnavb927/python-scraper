---
repo_name: wshobson/agents
url: "https://github.com/wshobson/agents"
stars: 34124
forks: 3701
contributors_count: 55
last_commit_date: "2026-04-18T18:30:34+00:00"
primary_use_case: Simulation
user_tier: Mainstream
total_score: 9
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Simulation]
generated_at: "2026-04-27T09:05:12.450560+00:00"
model: auto
duration_s: 99.2
clone_size_kb: 8288
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`wshobson/agents` is primarily a **Claude Code plugin marketplace repository**: a large collection of plugin manifests, agent prompts, command playbooks, and skills that users install into Claude Code rather than a standalone Python/JS app they run directly (`README.md:42-83`, `.claude-plugin/marketplace.json:12-1045`). In practice, a user runs slash commands like `/full-stack-feature` or `/team-review`, and Claude executes multi-step workflows defined in these Markdown command files (`plugins/full-stack-orchestration/commands/full-stack-feature.md:1-594`, `plugins/agent-teams/commands/team-review.md:1-79`). The one substantial executable codebase in-repo is `plugin-eval`, a Python CLI that scores plugin/skill quality using static checks plus optional LLM-based judging and Monte Carlo simulation (`plugins/plugin-eval/src/plugin_eval/cli.py:14-166`, `plugins/plugin-eval/src/plugin_eval/engine.py:71-129`). So the repo solves “intelligent automation” mostly by packaging reusable orchestration instructions for Claude Code.

## 2. Agent Framework & Architecture

This repo does **not** implement a LangGraph/CrewAI/AutoGen runtime in source code. The real framework is a **custom prompt/config architecture for Claude Code plugins**: agents and workflows are defined as Markdown + frontmatter and executed by Claude Code’s host runtime (`docs/architecture.md:137-150`, `plugins/agent-teams/agents/team-lead.md:1-7`).  

There are many references to LangGraph/LangChain in skills, but these are instructional examples for users, not this repo’s orchestration engine (e.g., “Quick Start with LangGraph” inside a skill doc: `plugins/llm-application-dev/skills/rag-implementation/SKILL.md:70-90`).

Architecturally, “intelligence” is split between:
- **Agent role prompts** (e.g., `team-lead`) describing behavior and constraints (`plugins/agent-teams/agents/team-lead.md:9-92`).
- **Command playbooks** that encode multi-step control flow, checkpoints, and delegation (`plugins/full-stack-orchestration/commands/full-stack-feature.md:12-18`, `133-154`, `345-432`).
- **`plugin-eval` Python modules** that call Claude models via `claude_agent_sdk` for automated scoring (`plugins/plugin-eval/src/plugin_eval/layers/judge.py:55-83`, `plugins/plugin-eval/src/plugin_eval/layers/monte_carlo.py:53-80`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with sequential phase gating**.

The command definitions act as manager/orchestrator, delegating work to specialized subagents and enforcing order/checkpoints. Example from full-stack flow:

```133:154:plugins/full-stack-orchestration/commands/full-stack-feature.md
Use the Task tool to launch a database architecture agent:

Task:
  subagent_type: "general-purpose"
  description: "Design database schema and data models for $FEATURE"
  prompt: |
    You are a database architect. Design the database schema and data models for this feature.
```

The same workflow later fans out into parallel specialist reviews (test/security/performance), then reconverges (`plugins/full-stack-orchestration/commands/full-stack-feature.md:345-456`).

Agent-teams commands show explicit team orchestration lifecycle (spawn, assign, monitor, cleanup):

```27:33:plugins/agent-teams/commands/team-review.md
1. Use `TeamCreate` tool to create the team with `team_name: "review-{timestamp}"` and `description`
2. For each requested dimension, use `Agent` tool to spawn a teammate:
   - `name`: `{dimension}-reviewer`
   - `subagent_type`: "agent-teams:team-reviewer"
```

## 4. Tools & External Integrations

- **Claude Code team/task orchestration APIs** (`TeamCreate`, `Agent`, `TaskCreate`, `TaskUpdate`, `TaskList`, `TeamDelete`) wired in agent-teams command playbooks (`plugins/agent-teams/commands/team-feature.md:65-79`, `plugins/agent-teams/commands/team-review.md:27-40`, `77-79`).
- **Subagent/task delegation** via `Task` tool in full-stack orchestrator (`plugins/full-stack-orchestration/commands/full-stack-feature.md:133-154`, `233-257`, `345-432`).
- **Shell/Git/GitHub CLI usage** (e.g., `git diff`, `gh pr diff`, build/test steps) in orchestration commands (`plugins/agent-teams/commands/team-review.md:22-24`, `plugins/agent-teams/commands/team-feature.md:61-64`, `94-96`).
- **Web tools** (`WebSearch`, `WebFetch`) explicitly allowed in business-analysis commands (`plugins/startup-business-analyst/commands/market-opportunity.md:3-4`, `70-73`).
- **MCP integrations** (Obsidian, Atlassian/Jira) described as required dependencies in standup workflow (`plugins/team-collaboration/commands/standup-notes.md:16-20`, `38-45`).
- **Claude model API via SDK** in `plugin-eval` (LLM judge/simulation layers) through `claude_agent_sdk.query` (`plugins/plugin-eval/src/plugin_eval/layers/judge.py:61-83`, `plugins/plugin-eval/src/plugin_eval/layers/monte_carlo.py:56-80`).

## 5. Notable Code Walkthrough

- `plugins/full-stack-orchestration/commands/full-stack-feature.md:12-594`  
  Encodes a full end-to-end delivery workflow with strict sequencing, persistent state files, phase checkpoints, and multiple delegated agent tasks; this is the clearest “workflow-as-prompt” orchestration artifact.
- `plugins/agent-teams/commands/team-feature.md:59-115`  
  Defines parallel development orchestration: decompose into streams, enforce file ownership boundaries, manage dependencies, verify integration, then teardown team resources.
- `plugins/agent-teams/agents/team-lead.md:1-92`  
  Core manager-agent contract: decomposition rules, dependency graph handling, ownership conflict prevention, and team lifecycle protocol.
- `plugins/plugin-eval/src/plugin_eval/engine.py:71-129`  
  Python control plane for evaluation: always run static layer, optionally run judge and Monte Carlo, then compute blended composite quality scores.
- `plugins/plugin-eval/src/plugin_eval/layers/judge.py:55-99` and `plugins/plugin-eval/src/plugin_eval/layers/monte_carlo.py:53-110`  
  Concrete runtime LLM usage via `claude_agent_sdk`; judge handles rubric-based semantic scoring, while Monte Carlo runs repeated stochastic simulations and aggregates statistical reliability metrics.

## 6. Use-Case Mapping

The upstream primary label **Simulation** is partially true only for the `plugin-eval` Monte Carlo component (`plugins/plugin-eval/src/plugin_eval/layers/monte_carlo.py:1-18`, `129-183`). But that is a subsystem for quality scoring, not the repository’s central value.

The dominant behavior is better categorized as **Workflow Automation**: this repo mainly provides reusable operational playbooks that orchestrate agents, tools, and phases for software delivery, reviews, debugging, and team coordination (`README.md:30-40`, `165-181`; `plugins/full-stack-orchestration/commands/full-stack-feature.md`; `plugins/agent-teams/commands/team-review.md`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Large, systematically organized prompt/agent marketplace with consistent plugin structure and discoverability (`.claude-plugin/marketplace.json`, `docs/architecture.md:79-150`).
  - Explicit orchestration logic (checkpoints, failure halts, dependency handling) in command playbooks, not just vague prompts (`plugins/full-stack-orchestration/commands/full-stack-feature.md:12-18`, `207-224`).
  - Strong practical integration surface (git/gh, web tools, MCP, team/task APIs) across workflows.
  - Includes a real evaluation framework (`plugin-eval`) with weighted dimensions and statistical scoring, uncommon in prompt repos.

- **Limitations:**
  - Most “agent logic” is declarative Markdown instructions; no in-repo runtime scheduler/executor independent of Claude Code platform.
  - Framework claims (LangGraph/CrewAI, etc.) are often instructional content inside skills, not implemented imports/execution paths in this repo (`plugins/llm-application-dev/skills/rag-implementation/SKILL.md:70-90`).
  - Quality/behavior of orchestrations depends heavily on external host behavior and model compliance with long natural-language instructions.
  - Tool contracts in command docs are not compile-time validated here; many integrations are expectation-based.

- **Research relevance:**
  - Good evidence of **prompt-programmed multi-agent coordination patterns** (manager-worker, phase gates, parallel reviewers) in production workflows.
  - Useful corpus for studying **governance by prompt constraints** (e.g., halt-on-failure, checkpoint approvals, ownership boundaries).
  - `plugin-eval` offers a concrete hybrid methodology combining static heuristics + LLM judging + Monte Carlo reliability, relevant for agent-system evaluation research.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
