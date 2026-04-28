---
repo_name: VoltAgent/awesome-openclaw-skills
url: "https://github.com/VoltAgent/awesome-openclaw-skills"
stars: 46983
forks: 4613
contributors_count: 89
last_commit_date: "2026-04-20T06:41:09+00:00"
primary_use_case: Simulation
user_tier: Mainstream
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T11:43:09.751597+00:00"
model: auto
duration_s: 57.1
clone_size_kb: 1258
uses_mas: no
final_use_case: None
---
## 1. Overview

`VoltAgent/awesome-openclaw-skills` is a curated index of OpenClaw skills, not an executable agent system. A user “runs” it by browsing `README.md` and category pages to find skill links, then installing selected skills via `clawhub install <skill-slug>` or manual copy instructions (`README.md:52-74`). The repository’s core output is organized discovery metadata (thousands of categorized links), plus contribution governance for adding/removing entries (`CONTRIBUTING.md:7-49`). It solves discovery/curation at ecosystem scale, not runtime orchestration of LLM agents.

## 2. Agent Framework & Architecture

No agent framework is implemented in this repo (no LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex runtime code found in source files). The codebase is almost entirely Markdown plus one GitHub Action workflow; there are no Python/TypeScript application modules defining agents, prompts, tools, planners, or routing logic.

Architecture is documentation-centric: a large root index (`README.md`) with category drill-down files under `categories/`, and contribution policy that constrains entries to links from the upstream OpenClaw skills registry (`CONTRIBUTING.md:3-31`). “Agent” language in files refers to **third-party listed skills**, not agents executed by this repository itself.

## 3. Orchestration Pattern

Closest match: **other (static curation + CI validation), not multi-agent orchestration**.  
There is no runtime control flow between agents. The only automation is a pull-request description checker in GitHub Actions.

Example (contribution model is link curation, not execution):
```11:15:CONTRIBUTING.md
Add your skill to the end of the relevant category in `README.md`:

```markdown
- [skill-name](https://github.com/openclaw/skills/tree/main/skills/author/skill-name/SKILL.md) - Short description of what it does.
```
```

Example (CI gate checks PR body regexes):
```15:22:.github/workflows/pr-check.yml
const body = context.payload.pull_request.body || '';

const hasClawhubLink = /https:\/\/clawhub\.ai\/[\w-]+\/[\w-]+/.test(body);
const hasGithubLink = /https:\/\/github\.com\/openclaw\/skills\/tree\/main\/skills\/[\w-]+\/[\w-]+/.test(body);

const errors = [];
if (!hasClawhubLink) {
```

## 4. Tools & External Integrations

This repository does not wire tools into an agent runtime. It references external services as links/documentation only.

- **GitHub Actions**: PR metadata validation via `actions/github-script` (`.github/workflows/pr-check.yml:1-40`).
- **OpenClaw / ClawHub references**: install and registry URLs documented for users (`README.md:52-59`, `README.md:93-95`).
- **OpenClaw skills ecosystem links**: category files list third-party skills/APIs, but those integrations are not implemented here (`categories/ai-and-llms.md:7-120`, etc.).
- **No MCP server/client wiring in repo code**: MCP appears only inside listed skill descriptions, not as executable integration in this repository.

## 5. Notable Code Walkthrough

- `README.md:46-190` — Main catalog index: explains purpose, install instructions, filtering rationale, and category table; this is the primary user-facing artifact.
- `README.md:192-353` — Inline category blocks with curated skill entries and links to full category pages; shows repository’s data model (Markdown link lists).
- `categories/ai-and-llms.md:1-120` — Representative category file format: heading, count, and many normalized skill bullets; demonstrates scalable, static taxonomy.
- `CONTRIBUTING.md:3-63` — Governance and acceptance criteria (must already exist in `openclaw/skills`, concise descriptions, anti-spam policy), crucial for quality control.
- `.github/workflows/pr-check.yml:1-40` — Only executable automation in repo; enforces required PR links and comments/fails on missing metadata.

## 6. Use-Case Mapping

The assigned primary use case (`Simulation`) appears incorrect for this repository. After inspecting source files, this repo is best classified as **Workflow Automation** only in the limited sense of curation workflow management (submission rules + CI validation), and operationally it is closer to a static awesome-list dataset than an agent runtime. It does not simulate environments, agents, or interactions; it organizes links to external skills that may themselves support many use cases.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Large-scale, structured skill discovery with clear category taxonomy (`README.md`, `categories/*`).
  - Strong contribution constraints reduce low-quality or off-registry entries (`CONTRIBUTING.md:30-35`).
  - Lightweight CI enforcement keeps PR metadata consistent (`.github/workflows/pr-check.yml:17-39`).
  - Transparent filtering rationale and security cautioning for users (`README.md:79-89`, `README.md:158-172`).

- **Limitations:**
  - No executable agent framework/code, so no direct MAS behavior to evaluate.
  - No machine-readable schema (JSON/YAML index) for downstream programmatic analysis; mostly Markdown.
  - Link quality/security are partly trust-based despite warnings; no automated link-health/security scanning in-repo.
  - “Agentic” claims in entries are unverified here; repository curates references rather than validating implementations.

- **Research relevance:**
  - Useful as an ecosystem corpus for studying taxonomy and diffusion of agent-skill patterns at scale.
  - Evidence for community governance mechanisms in open agent-skill registries (policy + CI gatekeeping).
  - Not suitable as direct evidence of multi-agent runtime orchestration algorithms or coordination protocols.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
