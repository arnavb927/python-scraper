---
repo_name: edoardottt/awesome-hacker-search-engines
url: "https://github.com/edoardottt/awesome-hacker-search-engines"
stars: 10500
forks: 1007
contributors_count: 72
last_commit_date: "2026-04-23T07:07:27+00:00"
primary_use_case: Code Generation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T08:01:14.544187+00:00"
model: auto
duration_s: 212.4
clone_size_kb: 119
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`edoardottt/awesome-hacker-search-engines` is a curated security/OSINT resource list, not an executable agent system. The main artifact users consume is `README.md`, which organizes hundreds of links by reconnaissance category (servers, vulnerabilities, code search, DNS, leaks, etc.) for pentesting and threat-intel workflows. There is no runtime application to launch; instead, contributors submit PRs to update entries, and CI checks the list quality. The repository’s automation focuses on list maintenance (duplicate-link detection and markdown link validation), so users “get” a maintained reference catalog rather than software outputs.

## 2. Agent Framework & Architecture

No LLM agent framework is implemented in this repository. I did not find LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex imports or any agent runtime code; the only executable source is a shell maintenance script plus GitHub Actions workflow YAML.

The effective architecture is a **content repository + CI guardrails**: `README.md` stores the curated dataset, `scripts/check-dups.sh` validates intra-section duplicate links, and `.github/workflows/*.yml` runs validation on PRs/pushes and on a schedule (`scripts/check-dups.sh:1-37`, `.github/workflows/check-duplicates.yml:1-21`, `.github/workflows/link-check.yml:1-19`). “Intelligence” here is human curation, not model-based reasoning.

## 3. Orchestration Pattern

Closest match: **other (CI workflow automation), not multi-agent orchestration**.

Control flow is GitHub Actions job sequencing: trigger event -> checkout -> run script/action. There are no cooperating agents, planners, or routers.

Example control flow:
```1:13:.github/workflows/check-duplicates.yml
name: Check Duplicates
on:
 pull_request:
 branches:
 - main
jobs:
 check-duplicates:
 runs-on: ubuntu-latest
 steps:
 - name: Check Out Code
 uses: actions/checkout@v2
```

```14:21:.github/workflows/check-duplicates.yml
 - name: Run Check Duplicates Script
 run: |
 chmod +x scripts/check-dups.sh
 ./scripts/check-dups.sh
 working-directory: ${{ github.workspace }}
```

## 4. Tools & External Integrations

No LLM tools, model APIs, MCP servers, or agent toolchains are wired in this repo.

- GitHub Actions CI runner integration via workflow files (`.github/workflows/check-duplicates.yml:1-21`, `.github/workflows/link-check.yml:1-19`).
- Third-party GitHub Action `gaurav-nelson/github-action-markdown-link-check@v1` for link validation (`.github/workflows/link-check.yml:12-18`).
- Local shell utilities (`awk`, `grep`, `sort`, `uniq`, `sed`) used by duplicate checker script (`scripts/check-dups.sh:20-33`).
- Markdown link checker behavior configured in JSON (`.github/mlc_config.json:1-35`).

## 5. Notable Code Walkthrough

- `scripts/check-dups.sh:1-37` - Core maintenance script that parses `README.md` sections and fails CI when duplicate URLs exist within a section; this is the main executable logic in the repo.
- `.github/workflows/check-duplicates.yml:1-21` - PR/push automation that invokes the duplicate-check script, enforcing curation hygiene before changes merge.
- `.github/workflows/link-check.yml:1-19` - Scheduled weekly link-health check against `README.md`, ensuring external resource quality over time.
- `.github/mlc_config.json:1-35` - Link-check tuning (allowed status codes, headers, timeout, `.onion` ignore pattern), which defines operational policy for CI validation.
- `README.md:1-~1200` - Primary data asset: categorized OSINT/security search-engine index consumed directly by practitioners.

## 6. Use-Case Mapping

The assigned primary use case (`Code Generation`) does not match the implementation. This repository does not generate code and does not implement agents; it curates security search resources and automates checklist-style quality checks in CI. A better fit is **Workflow Automation** (for maintenance workflows around a curated knowledge artifact), with secondary classification as a non-agent “awesome list” repository.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Large, well-structured domain taxonomy in one place (`README.md` categories cover many reconnaissance surfaces).
  - Lightweight but practical CI checks catch duplicate links before merge (`scripts/check-dups.sh` + workflow).
  - Scheduled link auditing keeps long-lived curated data from decaying (`link-check.yml` cron).
  - Minimal operational complexity; contributors can understand and extend quickly.

- **Limitations:**
  - No LLMs, no agents, no runtime orchestration logic to study as MAS implementation.
  - Duplicate detection is shell/regex-based and section-scoped; may miss semantic duplicates or formatting edge cases.
  - Link checker config allows broad status codes (e.g., `400`, `403`, `429`), which can mask broken resources (`.github/mlc_config.json`).
  - Entire value depends on manual curation quality and contributor activity.

- **Research relevance:**
  - Useful as a **negative/control example** in MAS datasets: agent-labeled metadata can be wrong for “awesome list” repos.
  - Shows how community knowledge bases use simple CI automation without AI components.
  - Evidence for distinguishing **workflow automation** from **agentic autonomy** in repository classification studies.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
