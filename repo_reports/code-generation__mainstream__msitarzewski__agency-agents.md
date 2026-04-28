---
repo_name: msitarzewski/agency-agents
url: "https://github.com/msitarzewski/agency-agents"
stars: 85485
forks: 13695
contributors_count: 72
last_commit_date: "2026-04-12T04:25:59+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T10:05:40.856707+00:00"
model: auto
duration_s: 79.1
clone_size_kb: 3997
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`msitarzewski/agency-agents` is a large, tool-agnostic library of agent personas encoded as Markdown prompt files, plus shell scripts to convert/install those prompts into multiple agentic coding environments. A user typically runs `scripts/convert.sh` and `scripts/install.sh`, then invokes specific agents (e.g., “Frontend Developer,” “Evidence Collector,” “Agents Orchestrator”) inside Claude Code, Cursor, Gemini CLI, etc. The practical output is not a standalone app, but a reusable multi-role operating model: structured prompts, handoff templates, and QA gates that drive coordinated AI-assisted delivery. In short, this repo packages a “virtual agency” workflow rather than executing LLM calls directly in repository code.

## 2. Agent Framework & Architecture

This repo does **not** use CrewAI/LangGraph/LangChain/AutoGen as executable dependencies. There are no framework imports or runtime Python/TypeScript orchestration modules; the only executable code is Bash for format conversion and installation (`scripts/convert.sh:1-639`, `scripts/install.sh:1-665`). The “framework” is effectively **custom prompt architecture** implemented as frontmatter-rich Markdown agent specs (e.g., `specialized/agents-orchestrator.md:1-367`, `testing/testing-evidence-collector.md:1-210`).

Architecturally, intelligence lives in prompt content: agent identity, role constraints, workflow phases, decision logic, retry rules, and handoff templates. The repo defines many specialist agents plus one meta-controller (“Agents Orchestrator”) that describes how to activate others in sequence and loops. The NEXUS strategy document formalizes a multi-phase operating model, gatekeepers, and inter-agent dependencies (`strategy/nexus-strategy.md:73-117`, `strategy/nexus-strategy.md:287-375`, `strategy/nexus-strategy.md:597-667`).

Operationally, this is a **prompt-native MAS design** that depends on host environments capable of spawning/subagent delegation. The repo supplies the behavior spec; external tools supply the runtime.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker workflow with staged pipeline + retry loops** (a hybrid of sequential and controlled parallel tracks).

Control flow is explicit in the orchestrator prompt: PM → architecture → per-task Dev↔QA loop → final reality check (`specialized/agents-orchestrator.md:21-32`, `specialized/agents-orchestrator.md:79-107`). NEXUS expands this into seven macro phases with gate checks and optional parallel workstreams (`strategy/nexus-strategy.md:75-93`, `strategy/nexus-strategy.md:145-163`, `strategy/nexus-strategy.md:295-314`).

Example excerpt 1 (`specialized/agents-orchestrator.md`):
```text
- Manage full workflow: PM → ArchitectUX → [Dev ↔ QA Loop] → Integration
- Task-by-task validation ... Failed tasks loop back to dev with specific feedback
- Maximum 3 attempts per task before escalation
```

Example excerpt 2 (`strategy/nexus-strategy.md`):
```text
Developer Agent -> Evidence Collector -> Decision Logic
PASS -> Next Task
FAIL -> Retry (<=3)
BLOCKED -> Escalate
```

## 4. Tools & External Integrations

- **Agent-host IDE/CLI integrations**: Conversion and install pipelines target Claude Code, Copilot, Antigravity, Gemini CLI, OpenCode, Cursor, Aider, Windsurf, OpenClaw, Qwen, and Kimi (`README.md:541-557`, `scripts/convert.sh:12-22`, `scripts/install.sh:12-23`).
- **Filesystem + local shell automation**: Install scripts detect local environments and copy/generated agent artifacts into tool-specific directories (`scripts/install.sh:141-185`, `scripts/install.sh:305-535`).
- **OpenClaw registration hook**: optional CLI-based workspace registration via `openclaw agents add` (`scripts/install.sh:411-426`).
- **MCP memory integration (optional pattern)**: documented integration with any MCP memory server exposing `remember/recall/rollback/search`; setup is advisory, not bundled server code (`integrations/mcp-memory/README.md:13-29`, `integrations/mcp-memory/setup.sh:14-33`).
- **QA/browser tooling references inside prompts**: agent instructions mention Playwright screenshots and CLI checks, but these are behavioral instructions for host agents, not repo-managed runtime services (`testing/testing-evidence-collector.md:41-55`).

## 5. Notable Code Walkthrough

- `scripts/convert.sh:83-133,202-249,481-639` - Core transformation engine: parses frontmatter/body from source agent `.md` files and emits tool-specific agent formats (`.mdc`, `SKILL.md`, YAML bundles, etc.), enabling portability across ecosystems.
- `scripts/install.sh:131-169,305-535,540-665` - Environment-aware installer: detects which tools exist, supports interactive/non-interactive and parallel install modes, and deploys converted artifacts to each tool’s expected path.
- `specialized/agents-orchestrator.md:21-32,79-147,362-367` - Central orchestration spec defining manager logic, quality gates, retry limits, and the “single command pipeline” activation prompt.
- `strategy/nexus-strategy.md:73-117,287-375,703-725` - Full multi-agent doctrine: seven-phase lifecycle, command structure, Dev↔QA loops, handoff protocol, and explicit gate-fail handling.
- `testing/testing-evidence-collector.md:39-69,100-118,119-174` - Representative worker/QA agent showing strict evidence-based validation behavior and standardized PASS/FAIL reporting contracts for loop feedback.

## 6. Use-Case Mapping

The assigned label **Code Generation** is only partially accurate. While many agents support engineering tasks, the repository’s core artifact is a **cross-functional orchestration system** for planning, implementation, QA, launch, and operations, spanning marketing/support/product/legal as first-class roles (`README.md:205-245`, `strategy/nexus-strategy.md:507-550`). Its strongest realized capability is coordinated process execution with gates, handoffs, and retries rather than code synthesis alone.

So the better classification is **Workflow Automation**: the repo encodes reusable multi-agent workflows (especially NEXUS and Agents Orchestrator) that automate role delegation, sequencing, and validation across an end-to-end delivery lifecycle.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Very rich role-specialized prompt corpus with consistent frontmatter and reusable structure across many domains (`README.md:533-537`).
- Clear orchestration doctrine (NEXUS) with explicit gates, retries, escalation, and handoff schemas (`strategy/nexus-strategy.md:703-725`).
- Strong portability layer: one source corpus converted to many agentic tool formats (`scripts/convert.sh:12-24`, `scripts/convert.sh:557-629`).
- Practical operator UX in scripts (interactive selector, auto-detection, parallelization) for real-world adoption (`scripts/install.sh:190-299`, `scripts/install.sh:625-641`).

- **Limitations:**
- No native runtime orchestration engine in repo (no direct LLM API execution, no task state backend); execution depends entirely on external host capabilities.
- Little formal validation of prompt correctness/efficacy beyond format conversion/linting; behavioral guarantees are mostly normative.
- Prompt instructions occasionally assume specific local files/tools that may not exist in user environments (e.g., QA script paths in agent prompts).
- Heavy markdown-first design can drift over time without machine-enforced inter-agent contract checks.

- **Research relevance:**
- Strong example of **prompt-native MAS governance** (role decomposition, gatekeeping, retry policies) without bespoke agent framework code.
- Useful evidence for studying **human-readable orchestration protocols** and institutionalized handoff templates in LLM teamwork.
- Demonstrates ecosystem-level pattern: separating agent knowledge/orchestration specs from runtime execution platform via conversion adapters.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
