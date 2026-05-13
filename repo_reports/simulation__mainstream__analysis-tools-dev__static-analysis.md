---
repo_name: analysis-tools-dev/static-analysis
url: "https://github.com/analysis-tools-dev/static-analysis"
stars: 14508
forks: 1459
contributors_count: 346
last_commit_date: "2026-04-13T22:18:31+00:00"
primary_use_case: Simulation
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-05-05T07:51:31.120843+00:00"
model: auto
duration_s: 101.0
clone_size_kb: 1790
mas_related: no
uses_mas: no
final_use_case: None
---
## 1. Overview

This repository is a curated data-and-pipeline project for static analysis tools, not an AI runtime system. Contributors add or modify YAML records in `data/tools/`, then CI and local commands (`make render`) use Rust binaries to validate, transform, and render outputs like `README.md` and JSON API files. The project also runs PR checks that enforce contribution quality criteria (stars, contributor count, project age) by querying GitHub metadata. In practice, users run make/CI workflows and receive generated catalog artifacts plus automated PR feedback.

## 2. Agent Framework & Architecture

No LLM agent framework is implemented here. I found no runtime imports/usages of LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, OpenAI/Anthropic SDKs, or prompt/planner/router abstractions in the actual code under `ci/`. The core is a Rust workspace with two command-line tools: `render` and `pr-check` (`ci/Cargo.toml:1-17`).

Architecture is pipeline-oriented automation:
- `render` ingests YAML tags/tools, validates/parses them, optionally checks deprecation from GitHub commit activity, then renders markdown/JSON artifacts (`ci/render/src/bin/main.rs:74-157`, `ci/render/src/lib.rs:67-174`).
- `pr-check` reads changed tool YAML files, queries GitHub REST endpoints, evaluates criteria, renders a markdown report, and posts/updates a PR comment (`ci/pr-check/src/main.rs:319-505`).
- GitHub Actions orchestrate when each binary runs (`.github/workflows/ci.yml:46-85`, `.github/workflows/pr-check.yml:71-109`).

So the “intelligence” is deterministic rules and validation logic in Rust, not model-based reasoning.

## 3. Orchestration Pattern

Closest match: **sequential workflow automation** (single-process/task pipeline), not multi-agent orchestration.

Control flow in `render` is linear (parse args → read YAML → transform → write outputs):
```74:103:ci/render/src/bin/main.rs
fn main() -> Result<()> {
    let mut args = Arguments::from_env();
    let args = Args { /* ... */ };

    let tags = read_tags(args.tags)?;
    let parsed_tools = read_tools(args.tools)?;
    let tools: Result<Vec<Entry>> = parsed_tools
        .into_iter()
        .map(|t| Entry::from_parsed(t, &tags))
        .collect();
    let mut tools = tools?;
    tools.sort();
    // ...
}
```

Control flow in `pr-check` is also linear batch processing per file (read → check → aggregate → comment):
```471:501:ci/pr-check/src/main.rs
let mut reports = Vec::new();
for path in &tool_paths {
    let tool = read_tool(path).with_context(|| format!("Failed to read {}", path.display()))?;
    let report = check_tool(&client, &tool).await?;
    reports.push(report);
}
let comment_body = render_comment(&reports)?;
/* write or post comment */
let any_failures = reports.iter().any(|r| r.any_fail());
if any_failures { std::process::exit(1); }
```

## 4. Tools & External Integrations

- **GitHub REST API (repo metadata, contributors, PR comments):** wired in `GithubClient` methods (`ci/pr-check/src/main.rs:131-280`), used for criteria checks and comment upsert (`ci/pr-check/src/main.rs:319-433`).
- **GitHub API via `hubcaps` crate (commit recency for deprecation):** used in `check_deprecated` (`ci/render/src/lib.rs:22-65`).
- **GitHub Actions workflows:** orchestration and automation triggers (`.github/workflows/ci.yml`, `pr-check.yml`, `pr-comment.yml`, `render.yml`).
- **Filesystem/YAML/JSON templating pipeline:** reads `data/tools/*.yml`, writes `README.md` and `data/api/*.json` (`ci/render/src/bin/main.rs:31-51`, `118-142`).
- **No MCP servers, vector DBs, browser automation, shell-agent tool use, or LLM APIs** in repository runtime code.

## 5. Notable Code Walkthrough

- `ci/render/src/bin/main.rs:74-157` - Main renderer entrypoint: parses CLI args, loads tags/tools YAML, applies optional deprecation checks, builds catalog/API, and writes markdown/JSON outputs.
- `ci/render/src/lib.rs:23-65` - Deprecation checker: calls GitHub commits API and marks tools as deprecated if inactivity exceeds 365 days.
- `ci/render/src/types.rs:134-179` - Core schema conversion from YAML (`ParsedEntry`) to validated internal model (`Entry`), including strict tag/type validation and error reporting.
- `ci/pr-check/src/main.rs:319-400` - Per-tool contribution criteria evaluator (stars, age, contributors), including graceful skips for non-GitHub sources.
- `.github/workflows/pr-check.yml:75-109` - CI wiring that builds/runs `pr-check`, persists results as artifacts, and fails workflow on unmet hard criteria.

## 6. Use-Case Mapping

The assigned primary use case (`Simulation`) does **not** fit the implemented code. This repo is best categorized as **Workflow Automation**: deterministic CI/CD automation around structured data curation, validation, rendering, and PR governance. There is no simulation engine, agent environment, or iterative agent interaction loop in runtime code.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, enforceable contribution policy encoded as executable checks (`ci/pr-check/src/main.rs`).
  - Reproducible artifact generation from structured YAML source of truth (`Makefile`, `render` binary).
  - Good CI separation for fork-safe commenting (`pr-check` + `pr-comment` workflow split).
  - Strong typed data model and validation in Rust reduces schema drift/runtime ambiguity.

- **Limitations:**
  - No LLM/agent implementation despite some tool descriptions mentioning AI; this repo is not an agentic system itself.
  - Mostly GitHub-centric validation logic (non-GitHub sources are skipped/manual).
  - Sequential processing; limited concurrency/performance optimization for larger-scale checks.
  - Minimal abstraction for extensible policy rules beyond current hardcoded criteria.

- **Research relevance:**
  - Useful as evidence of **policy-as-code workflow automation** in open-source curation pipelines.
  - Useful example of **CI-mediated governance** with automated PR feedback loops.
  - Not suitable as evidence of multi-agent coordination, LLM planning, or agent communication protocols.

## 8. Machine-readable classification

MAS_RELATED: no
USES_MAS: no
FINAL_USE_CASE: None
