---
repo_name: gtmagents/gtm-agents
url: "https://github.com/gtmagents/gtm-agents"
stars: 168
forks: 29
contributors_count: 3
last_commit_date: "2026-04-03T17:37:23+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T17:51:53.529825+00:00"
model: auto
duration_s: 85.6
clone_size_kb: 2859
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`gtmagents/gtm-agents` is a large Claude Code plugin marketplace repository that packages GTM automation assets (agents, commands, and skills) as Markdown definitions rather than an executable Python/JS agent runtime. A user installs this marketplace in Claude Code (`/plugin marketplace add gtmagents/gtm-agents`), installs selected plugins, and invokes slash commands like `/campaign-orchestration:launch-campaign ...` to get generated plans, briefs, sequences, and analytics artifacts. The repo’s core value is breadth of domain-specific workflow templates across sales, marketing, and RevOps, with standardized frontmatter and validation scripts to keep plugin assets consistent. In practice, this is a prompt-and-configuration catalog for agentic workflow execution inside Claude Code, not a standalone orchestrator service.

## 2. Agent Framework & Architecture

No LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex runtime is implemented in this repository. I found no framework imports or runtime orchestration code; the only Python code is maintenance tooling (validation/scaffolding), e.g., `scripts/validate_marketplace.py` and `scripts/smoke_test_plugins.py`.

Architecture is **manifest + markdown assets**:
- `.claude-plugin/marketplace.json` enumerates plugins and points to agent/command/skill files.
- `plugins/*/agents/*.md` defines role prompts and model hints (`haiku`/`sonnet`).
- `plugins/*/commands/*.md` defines command usage and workflow steps.
- `plugins/*/skills/*/SKILL.md` defines reusable “Agent Skills” instructions.
- `scripts/*.py` validates structure/frontmatter and scaffolds templates.

Representative evidence:

```2:10:.claude-plugin/marketplace.json
  "name": "gtm-agents",
  "description": "Comprehensive AI agents for sales, marketing, and growth teams",
  "version": "1.0.0",
  "owner": {
    "name": "GTM Agents",
    "email": "opensource@intentgpt.ai",
    "url": "https://github.com/gtmagents/gtm-agents"
  },
  "plugins": [
```

```164:188:scripts/validate_marketplace.py
def validate_agent_frontmatter():
    agent_dir = ROOT / "plugins"
    for agent_path in agent_dir.rglob("agents/*.md"):
        ...
        for key in ("name", "description", "model"):
            if key not in data:
                fail(f"{rel}: missing '{key}' in frontmatter")
        ...
        model = str(data["model"]).lower()
        if model not in ALLOWED_AGENT_MODELS:
```

## 3. Orchestration Pattern

Closest match: **other (declarative, document-driven workflow templates)** with **pipeline/hierarchical intent** described in Markdown, but not enforced by executable graph code in this repo.

Control flow is specified textually inside command docs (e.g., orchestrator → phase agents), and command files reference agent/skill invocations as guidance:

```16:22:plugins/abm-orchestration/commands/target-accounts.md
## Workflow
1. **Data Merge** – combine CRM, enrichment, intent, product usage, partner data.
2. **Scoring & Tiering** – apply ideal customer fit, engagement, pipeline stage to produce T1/T2/T3 split.
3. **Buying Committee Mapping** – surface key personas, roles, known contacts.
4. **Signal Highlights** – list recent intent spikes, product usage, news, hiring signals.
5. **Activation Suggestions** – propose first-touch plays per tier.
```

```28:32:plugins/abm-orchestration/commands/target-accounts.md
## Agent/Skill Invocations
- `abm-strategist` – ensures scoring logic aligns with program goals.
- `account-tiering` skill – enforces tier definitions.
- `signal-intel` skill – aggregates intent/product signals.
```

## 4. Tools & External Integrations

This repo does **not** wire live API clients, SDK calls, MCP servers, or vector DB clients in executable code. Integrations appear as declarative references/examples in docs and configuration content.

- **Claude Code plugin runtime integration** via marketplace manifest (`.claude-plugin/marketplace.json`), which maps command/agent/skill assets.
- **Slash-command interface** (`/plugin install`, `/sales-prospecting:...`) documented in `docs/usage-guide.md`.
- **Potential external systems listed as workflow targets** (CRM, marketing, analytics, PM tools) in command/docs, not implemented adapters in code (`plugins/campaign-orchestration/commands/launch-campaign.md`, `docs/usage-guide.md`).
- **Provider catalog (declarative only)** listing many enrichment/data vendors in `plugins/data-enrichment-master/config/providers.yaml`; this is a registry-like document wrapped in markdown, not executable integration code.

## 5. Notable Code Walkthrough

- `./.claude-plugin/marketplace.json:10-40`  
  Central manifest that defines plugin composition (`commands`, `agents`, `skills`) and effectively acts as the repository’s runtime contract for Claude Code plugin loading.

- `plugins/campaign-orchestration/commands/launch-campaign.md:16-60`  
  Most explicit orchestration spec: describes a “master coordinator,” phase sequencing, and planning guardrails (plan JSON, retries/escalation). Shows how multi-agent behavior is intended to be prompted.

- `plugins/sales-prospecting/agents/lead-researcher.md:1-27`  
  Representative agent prompt file with model tag, activation criteria, and capability framing; this is where role-level “intelligence” instructions live.

- `scripts/validate_marketplace.py:71-125`  
  Enforces structural quality of the catalog (required keys, semantic versioning, file existence), then validates agent/command/skill frontmatter consistency.

- `scripts/smoke_test_plugins.py:66-86`  
  CI-friendly integrity check that iterates all referenced assets and fails on missing/empty/frontmatter-less markdown; demonstrates repo focus on content QA, not runtime execution.

## 6. Use-Case Mapping

The upstream label **RAG + Agents** looks inaccurate for this codebase. I found no retrieval pipeline implementation (no indexing/chunking/embedding/vector store/query stack), and no executable multi-agent runtime graph. What this repo concretely provides is a **workflow-automation prompt catalog** for Claude Code plugins: users run domain commands to produce operational deliverables (campaign plans, lead lists, analytics briefs, handoff docs). Best category is therefore **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Very large, systematically organized prompt asset library across GTM domains (`plugins/*` + marketplace manifest).
  - Strong schema/quality governance via validation and smoke-test scripts (`scripts/validate_marketplace.py`, `scripts/smoke_test_plugins.py`).
  - Clear role/task decomposition into agents, commands, and skills with reusable frontmatter conventions.
  - Practical operator-facing command UX (`/plugin ...`, `/plugin-name:command`) documented with many examples.
  - Good interoperability posture around Agent Skills packaging and indexing (`skills-index.json`, `available_skills.xml`).

- **Limitations:**
  - No executable orchestration engine in-repo (no manager-worker runtime, no state machine implementation).
  - No concrete RAG stack implementation despite frequent “insights”/“signals” language.
  - External integrations are mostly aspirational/documented, not wired with API code or tested connectors.
  - Behavioral correctness depends heavily on LLM prompt adherence in external host runtime (Claude Code), making reproducibility weaker.
  - Some docs claim advanced integrations/pipelines that are not backed by corresponding implementation code here.

- **Research relevance:**
  - Evidence for **declarative multi-agent prompt architecture** as an alternative to code-centric MAS frameworks.
  - Useful case study in **prompt asset governance** (schema validation, frontmatter constraints, CI checks).
  - Demonstrates how domain workflows can be encoded as reusable command+skill templates for operational automation.
  - Relevant to studies on **human-readable orchestration specifications** versus executable agent graphs.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
