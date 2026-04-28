---
repo_name: VoltAgent/awesome-claude-code-subagents
url: "https://github.com/VoltAgent/awesome-claude-code-subagents"
stars: 18023
forks: 2056
contributors_count: 30
last_commit_date: "2026-04-20T07:13:01+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T11:45:44.867537+00:00"
model: auto
duration_s: 76.2
clone_size_kb: 1638
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

This repository is primarily a **catalog of Claude Code subagent definitions**, not an executable agent runtime. A user typically either copies individual `.md` agent files into `~/.claude/agents` (or `.claude/agents`) or runs the interactive installer script to select categories and install/uninstall agent files. The output is a set of role-specific prompt files (with frontmatter like `name`, `tools`, `model`) that Claude Code can invoke later in another environment. It solves discovery/packaging/governance of many specialized agent personas, rather than implementing live multi-agent execution logic itself.

## 2. Agent Framework & Architecture

No LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex runtime was found in source code; there are no Python/TS orchestration modules with framework imports. The repository is a **custom, declarative prompt-packaging format** built around Markdown agent specs plus plugin manifests.

Agent definitions are Markdown files with YAML frontmatter specifying identity and capabilities (`name`, `description`, `tools`, `model`), followed by long behavioral instructions and pseudo-protocols (often JSON snippets showing hypothetical inter-agent messages). Example structure is visible in `categories/01-core-development/fullstack-developer.md` and `categories/09-meta-orchestration/multi-agent-coordinator.md`. Packaging is done through `.claude-plugin` manifests that enumerate agent files per category, and a top-level marketplace manifest aggregates category plugins.

The “intelligence” therefore lives in prompt text and metadata constraints, not in code-based planners/routers/graphs. The only real executable logic in-repo is operational tooling (installer and catalog cache/fetch scripts), not agent reasoning runtime.

## 3. Orchestration Pattern

Closest match: **Other (declarative prompt library / static role catalog)**, not an implemented runtime orchestration pattern.

The repo describes hierarchical/sequential/swarm-like patterns in prose, but control flow is not executed by repository code. For example, the `codebase-orchestrator` file encodes an approval-gated lifecycle in instructions:

```13:18:categories/09-meta-orchestration/codebase-orchestrator.md
When invoked:
1. Map repository structure
2. Identify architectural risks
3. Propose safe actions
4. Execute approved diffs
```

Likewise, “communication protocol” snippets are templates, not running message buses:

```116:123:categories/09-meta-orchestration/codebase-orchestrator.md
{
  "requesting_agent": "codebase-orchestrator",
  "request_type": "get_structure_context",
  "payload": {
    "query": "Define absolute repository boundaries, required scaffolding schemas, and exact context limitations before I trigger the assessment phase."
  }
}
```

So the repository provides **orchestration playbooks**, but no executable agent-to-agent dispatcher/state machine.

## 4. Tools & External Integrations

- **Claude Code tool permissions (declared, not wired in code)**: agent frontmatter exposes capabilities like `Read`, `Write`, `Edit`, `Bash`, `Glob`, `Grep`, `WebFetch`, `WebSearch` (e.g., `categories/01-core-development/fullstack-developer.md`, `categories/10-research-analysis/trend-analyst.md`).
- **Custom/MCP-like tool names (declarative references)**: some agents list tools such as `airis-mcp-gateway`, `context-manager`, `error-coordinator`, `subagent-catalog:search` (e.g., `categories/09-meta-orchestration/codebase-orchestrator.md`), but these are not implemented here as callable services.
- **GitHub HTTP integration (actual code)**: installer and catalog scripts use `curl` against GitHub API/raw endpoints to fetch category/agent files (`install-agents.sh`, `tools/subagent-catalog/config.sh`).
- **Local filesystem integration (actual code)**: installer copies/removes `.md` agent files to/from `~/.claude/agents` or project `.claude/agents` (`install-agents.sh`).
- **CI/GitHub Actions (actual code)**: workflow checks plugin-version bump consistency and marketplace sync (`.github/workflows/enforce-plugin-version-bump.yml`).

No vector store, DB connector, browser automation runtime, or in-repo RAG pipeline implementation was found.

## 5. Notable Code Walkthrough

- `install-agents.sh:17-27,162-195,528-555` - Interactive installer core: chooses global/local mode, optionally fetches from GitHub, and installs/uninstalls agent `.md` files. This is the main executable entry point users run.
- `.claude-plugin/marketplace.json:1-93` - Top-level plugin registry mapping category plugins, versions, and metadata; central for distribution/versioning of the catalog.
- `categories/09-meta-orchestration/codebase-orchestrator.md:1-10,109-124,164-187` - Representative high-complexity agent definition showing frontmatter tool model, strict approval-loop behavior, and pseudo-JSON protocol.
- `categories/01-core-development/fullstack-developer.md:1-6,96-111,141-166` - Representative “builder” agent spec demonstrating standard schema: role, checklist, protocol query, and phased workflow template.
- `tools/subagent-catalog/config.sh:8-12,38-47,49-70` - Support script implementing catalog cache TTL, atomic fetch, and stale-cache fallback for slash-command-based discovery.

## 6. Use-Case Mapping

The assigned label **Code Generation** is only partially accurate. The repository helps code generation indirectly by providing specialized coding agent prompts (e.g., backend/frontend/fullstack roles), but the repo itself does not generate code at runtime; it distributes reusable agent definitions and orchestration playbooks.

A better primary category is **Workflow Automation**: most executable logic concerns installing, packaging, versioning, and discovering agent definitions, while many prompt assets focus on orchestration/process coordination. This is a meta-layer automation artifact rather than a concrete codegen engine.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Large, systematically organized role library across 10 categories with consistent frontmatter schema.
  - Clear packaging/distribution mechanics via per-category plugins plus marketplace manifest.
  - Practical install UX (`install-agents.sh`) supporting local vs remote source and global vs project scope.
  - Strong prompt engineering depth in role checklists, phased workflows, and communication templates.
  - Governance signals (CI rule for plugin version bumps) improve catalog maintenance discipline.

- **Limitations:**
  - No executable multi-agent runtime; orchestration is descriptive text, not enforceable control logic.
  - Tool names in frontmatter are not validated in-repo; compatibility depends on external Claude setup.
  - Heavy reliance on long static prompts may cause drift/inconsistency without automated tests for behavior.
  - Installer and catalog scripts are shell-centric and primarily Unix-oriented.
  - No benchmark harness showing real task outcomes, latency, or quality across agents.

- **Research relevance:**
  - Evidence of **prompt-level role decomposition** and reusable agent persona design patterns.
  - Useful corpus for studying **instruction-template standardization** across many specialist agents.
  - Example of ecosystem tooling for **agent catalog lifecycle management** (install/version/discovery).
  - Illustrates gap between “multi-agent described in prompts” vs “multi-agent implemented in code.”

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
