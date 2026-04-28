---
repo_name: protontypes/open-sustainable-technology
url: "https://github.com/protontypes/open-sustainable-technology"
stars: 2486
forks: 311
contributors_count: 104
last_commit_date: "2026-04-19T20:46:20+00:00"
primary_use_case: Simulation
user_tier: Mid-Tier
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T15:04:49.649376+00:00"
model: auto
duration_s: 61.5
clone_size_kb: 46761
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

This repository is primarily a curated “awesome-list” plus automation around maintaining and publishing sustainability project metadata, not an LLM application. A contributor typically edits `README.md` to add projects, while GitHub Actions scripts validate links, enrich project metadata from ecosyste.ms, and publish CSV releases for downstream consumption. The core runnable pieces are workflow-triggered Python scripts in `.github/workflows` (for PR review comments, dataset export, and link maintenance). The output users get is a maintained directory (`README.md`), generated CSV datasets (`projects.csv`, `organizations.csv`), and automated PR comments/maintenance pull requests.

## 2. Agent Framework & Architecture

No LLM agent framework is actually used. I found no imports or runtime references to LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, OpenAI SDKs, or prompt/orchestrator code (repo-wide search over Python and config files returned no matches).

Architecture is conventional automation: GitHub Actions orchestrate standalone scripts. For example, `pr_review.yml` executes `.github/workflows/pr_review.py`, which extracts a URL from PR text and calls ecosyste.ms APIs to generate a markdown comment artifact (`.github/workflows/pr_review.py:29-36`, `:330-356`). A second workflow (`pr_review_comment.yml`) consumes that artifact and posts it using GitHub CLI (`.github/workflows/pr_review_comment.yml:22-32`).

A separate pipeline (`release_dataset_action.yml` + `release_dataset.py`) fetches ecosyste.ms data, transforms it with pandas, and pushes records to Grist via REST (`.github/workflows/release_dataset.py:84-95`, `:443-507`, `:516-654`). This is workflow automation/data engineering, not agentic reasoning.

## 3. Orchestration Pattern

Closest match: **event-driven sequential workflow automation** (GitHub Actions), not multi-agent orchestration.

Control flow is triggered by repository events, then runs linear steps:

```23:32:.github/workflows/pr_review_comment.yml
      - name: Post comment
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          if [ ! -f comment.md ] || [ ! -s comment.md ]; then
            echo "No comment to post"
            exit 0
          fi
          PR_NUMBER=$(cat pr_number.txt)
          COMMENT=$(cat comment.md)
          gh pr comment "$PR_NUMBER" --repo "${{ github.repository }}" --body "$COMMENT"
```

And data-fetch -> transform -> emit comment happens in one script path:

```336:356:.github/workflows/pr_review.py
    project_url = extract_project_url(pr_body)
    if not project_url:
        print("Could not extract a project URL from the PR body.")
        sys.exit(0)

    repos = fetch_repos_data(project_url)
    packages = fetch_packages_data(project_url)
    commits = fetch_commits_data(project_url)
    issues = fetch_issues_data(project_url)

    trigger_ost_sync(project_url)

    if not repos and not packages and not commits and not issues:
        comment = f"Could not fetch project data ..."
    else:
        comment = build_comment(project_url, repos, packages, commits, issues)
```

## 4. Tools & External Integrations

- **ecosyste.ms APIs** for repository/package/commit/issue/project metadata lookups, wired in `.github/workflows/pr_review.py:49-73` and `.github/workflows/release_dataset.py:84-114`.
- **Grist API** for writing `Projects`, `Organizations`, and `Funding` tables, wired in `.github/workflows/release_dataset.py:56-74`, `:443-507`, `:516-654`.
- **GitHub Actions runtime** as orchestrator, wired in `.github/workflows/pr_review.yml`, `.github/workflows/pr_review_comment.yml`, `.github/workflows/release_dataset_action.yml`, `.github/workflows/maintain_listing.yaml`.
- **GitHub CLI (`gh`)** to post PR comments, wired in `.github/workflows/pr_review_comment.yml:30-32`.
- **PyGithub** to open maintenance PRs programmatically, wired in `.github/workflows/maintenance/maintenance_script.py:31`, `:92-135`, `:343-392`.
- **HTTP link checking with cache** (`requests`, `diskcache`, retries) for README link maintenance, wired in `.github/workflows/maintenance/maintenance_script.py:64-83`, `:196-213`, `:237-270`.
- **No MCP servers, browser automation, vector DBs, or LLM inference APIs** are present.

## 5. Notable Code Walkthrough

- `.github/workflows/pr_review.py:29-36,330-360`  
  Extracts the first non-ignored URL from PR body, calls multiple ecosyste.ms endpoints, computes heuristic checks (activity, documentation, license, usage), and writes a markdown PR comment artifact.

- `.github/workflows/release_dataset.py:84-95,159-214,443-507`  
  Pulls bulk project metadata, performs heavy pandas-based normalization/enrichment, then batches and uploads records to Grist tables through authenticated REST requests.

- `.github/workflows/maintenance/maintenance_script.py:160-174,237-270,343-392`  
  Parses README links, checks for dead/redirected URLs with cached HTTP probes, then auto-creates GitHub pull requests to replace redirected links or remove dead ones.

- `.github/workflows/pr_review.yml:3-35`  
  Defines event trigger (`pull_request` on `README.md` changes), runs `pr_review.py`, and uploads artifacts for downstream comment-posting workflow.

- `.github/workflows/maintain_listing.yaml:59-86`  
  Operational wrapper for maintenance script: dispatch input for max updates, runs script with GitHub token, runs lint, and opens PR via `peter-evans/create-pull-request`.

## 6. Use-Case Mapping

The assigned primary use case (`Simulation`) looks incorrect for this repository itself. While the curated list contains many simulation projects in sustainability domains, this codebase does not run simulation models; it maintains a catalog and metadata pipeline. Based on the implemented code, the best category is **Workflow Automation**: event-triggered scripts ingest API data, validate links, enrich records, and automate PR/release operations. There is no runtime multi-agent or LLM-agent behavior.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Robust automation around community curation (PR review comments, link maintenance, monthly releases).
  - Practical external-data integration (ecosyste.ms + Grist + GitHub) with clear operational scripts.
  - Strong maintenance ergonomics (retry logic, caching, batch uploads, artifact handoff between workflows).
  - Useful reproducible data pipeline for sustainability ecosystem tracking.

- **Limitations:**
  - No LLM or multi-agent implementation despite “agentic” framing; unsuitable as evidence of MAS runtime behavior.
  - Most logic is in monolithic scripts, limiting modularity and testability.
  - Limited explicit test coverage in-repo for core data transforms and API edge cases.
  - Some workflow scripts perform broad side effects (deleting/reloading Grist records), which can be operationally risky.

- **Research relevance:**
  - Good case study for **open-source ecosystem workflow automation** in a domain repository.
  - Useful evidence for **event-driven CI/CD orchestration** of curation pipelines.
  - Not suitable evidence for **LLM coordination, planning, tool-using agents, or MAS control policies**.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
