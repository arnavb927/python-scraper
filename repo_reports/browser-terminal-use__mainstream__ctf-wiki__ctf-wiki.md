---
repo_name: ctf-wiki/ctf-wiki
url: "https://github.com/ctf-wiki/ctf-wiki"
stars: 9296
forks: 1433
contributors_count: 200
last_commit_date: "2026-04-22T07:50:07+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [Custom/Other]
use_case_labels: [Browser / Terminal Use]
generated_at: "2026-04-27T11:13:11.146044+00:00"
model: auto
duration_s: 74.8
clone_size_kb: 212799
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`ctf-wiki/ctf-wiki` is a large MkDocs-based documentation repository for CTF/security learning content, not an executable agent system. Users primarily run documentation build commands such as `python3 scripts/docs.py build-all` and `python3 scripts/docs.py serve` to generate and preview a static site locally (`README.md:52-67`, `scripts/docs.py:267-359`). The output is a multilingual static knowledge website (Chinese/English/Traditional Chinese) organized through large MkDocs navigation configs (`docs/zh/mkdocs.yml:1-618`). It also includes GitHub Actions for CI, preview deployment, and Docker image publishing (`.github/workflows/*.yml`).

## 2. Agent Framework & Architecture

No LLM-agent framework is implemented in this repository runtime. There are no operational imports/usages of LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, or OpenAI SDKs in project code that users run for site generation; the Python code is focused on MkDocs orchestration and GitHub automation (`scripts/docs.py:1-458`, `requirements.txt:1-6`).

What *does* exist is educational prose about agent concepts (e.g., “Agent Loop”) inside markdown docs, including illustrative code snippets embedded in articles rather than imported modules or runnable package components (`docs/zh/docs/ai/ai-for-security/agent/introduction.md:31-123`, `docs/zh/docs/ai/ai-for-security/agent/agent-loop.md:131-271`). That means intelligence/planning/tool-use logic is discussed as learning material, but not instantiated as repository architecture.

The real architecture is: MkDocs content tree + a Python CLI (`typer`) that builds multilingual docs + CI/CD workflows that deploy static artifacts (`scripts/docs.py:87-359`, `.github/workflows/preview-site-wrapper.yml:24-40`).

## 3. Orchestration Pattern

Closest match: **other (documentation build pipeline orchestration), not agent orchestration**.

Control flow is deterministic and procedural:
- `build_all()` updates language configs, builds default docs, then parallel-builds other language sites via multiprocessing (`scripts/docs.py:267-287`).
- CI workflows chain build -> artifact -> deploy -> PR comment steps (`.github/workflows/preview-site-wrapper.yml:28-40`, `.github/workflows/preview-site.yml:21-48`).

Example snippets:

```267:287:scripts/docs.py
@app.command()
def build_all():
    site_path = Path("site").absolute()
    update_languages(lang=None)
    ...
    subprocess.run(["mkdocs", "build", "--site-dir", site_path], check=True)
    ...
    with Pool(cpu_count * 2) as p:
        p.map(build_lang, langs)
```

```21:48:.github/workflows/preview-site.yml
- name: Download Artifact Docs
  uses: dawidd6/action-download-artifact@v6
...
- name: Deploy to Netlify
  uses: nwtgck/actions-netlify@v1.1
...
- name: Comment Deploy
  uses: ./.github/actions/comment-docs-preview-in-pr
```

## 4. Tools & External Integrations

No agent tool-calling stack is wired for runtime (no MCP, browser automation framework, vector DB, or LLM API client as part of app behavior). External integrations present are CI/deployment/documentation tooling:

- **MkDocs + Material + minify plugin** for site generation (`requirements.txt:1-6`, `docs/zh/mkdocs.yml:28-31`).
- **Typer CLI** for docs build/serve commands (`scripts/docs.py:15`, `scripts/docs.py:87-359`).
- **GitHub Actions ecosystem** for CI and deployments (`.github/workflows/ci.yml:19-52`, `.github/workflows/preview-site*.yml`).
- **Netlify deployment** action (`.github/workflows/ci.yml:34-44`, `.github/workflows/preview-site.yml:33-43`).
- **GitHub API + PyGithub + httpx** in a custom action that comments preview URLs on PRs (`.github/actions/comment-docs-preview-in-pr/app/main.py:6-69`).
- **DockerHub push** pipeline (`.github/workflows/dockerhub.yml:15-25`).

## 5. Notable Code Walkthrough

- `scripts/docs.py:87-359` - Core operational CLI. Defines commands (`build_all`, `build_lang`, `serve`, `live`) and manages multilingual site assembly, placeholder insertion for missing translations, and MkDocs invocation.
- `scripts/docs.py:361-453` - Config/nav transformation utilities (`update_config`, `get_file_to_nav_map`, `get_sections`) that keep language navigation and alternates consistent.
- `.github/actions/comment-docs-preview-in-pr/app/main.py:14-70` - Custom GitHub Action app: parses workflow event, finds matching PR by commit SHA, posts preview URL comment via GitHub API.
- `.github/workflows/preview-site-wrapper.yml:24-40` - PR-triggered preview build workflow: install deps, build docs, zip and upload site artifact.
- `docs/zh/docs/ai/ai-for-security/agent/agent-loop.md:131-271` - Representative “agentic AI” content in docs; provides explanatory sample code for a looped LLM+executor design, but it is article text, not integrated runtime module.

## 6. Use-Case Mapping

The upstream assigned use case (`Browser / Terminal Use`) appears incorrect for this repository as implemented. This repo does not provide an agent that operates a browser or terminal at runtime; instead it automates documentation build/deploy workflows (MkDocs build, CI artifact/deploy, PR comments) and contains educational text about agent systems. A better fit is **Workflow Automation** because the executable logic coordinates build, packaging, deployment, and CI messaging rather than autonomous browser/terminal task execution.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong, explicit multilingual docs build pipeline with reusable CLI commands (`scripts/docs.py`).
  - Practical CI/CD chain for preview deployments and feedback in PRs (`preview-site-wrapper` + `preview-site` workflows).
  - Mature documentation structure with extensive taxonomy in MkDocs navigation (`docs/zh/mkdocs.yml`).
  - Includes current AI-agent educational material relevant to security learners (`docs/zh/docs/ai/...`).

- **Limitations:**
  - No runnable LLM agent implementation despite agent-themed content; code snippets are instructional markdown only.
  - No packaged Python module/app for agent execution, benchmarking, or reproducible experiments.
  - Minimal test/validation infrastructure for the Python build script beyond CI execution.
  - AI/agent examples in docs are not version-pinned runnable artifacts within this repo.

- **Research relevance:**
  - Useful as evidence of **community documentation practices** around agentic security concepts, not as an implemented MAS benchmark.
  - Illustrates how security education projects integrate AI-agent theory into curricula/content.
  - Good case for studying documentation-driven dissemination of agent workflows versus production agent systems.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
