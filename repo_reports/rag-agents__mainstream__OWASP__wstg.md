---
repo_name: OWASP/wstg
url: "https://github.com/OWASP/wstg"
stars: 9134
forks: 1586
contributors_count: 167
last_commit_date: "2026-04-22T16:07:46+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 7
architecture_labels: [Custom/Other]
use_case_labels: [RAG + Agents]
generated_at: "2026-04-27T11:14:19.318290+00:00"
model: auto
duration_s: 67.5
clone_size_kb: 32989
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`OWASP/wstg` is primarily a content repository for the OWASP Web Security Testing Guide: a large, structured Markdown corpus of security testing methodology, plus CI/CD scripts that publish derived artifacts (web pages, JSON checklist, XLSX, PDF/EPUB). A user typically consumes the guide by reading the Markdown in `document/`, or by using generated outputs like `checklists/checklist.json` and `checklists/checklist.xlsx`. Maintainers run GitHub Actions workflows that regenerate these artifacts when guide content changes, then open pull requests automatically. The core problem it solves is standardizing and distributing web-app security testing knowledge, not running an interactive AI agent system.

## 2. Agent Framework & Architecture

No LLM agent framework is implemented in this repository. I found no runtime usage of LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex-style imports, no model client orchestration, and no planner/router/worker codepaths. The codebase is documentation plus automation scripts.

The architecture is a documentation + build/publish pipeline: markdown source in `document/`, transformed by workflow jobs into deployment-ready content and checklist artifacts. For example, `build-checklists.yml` runs Python scripts to generate checklist JSON and XLSX and optionally publishes to Google Drive (`.github/workflows/build-checklists.yml:26-42`, `.github/xlsx/scripts/upload-to-google-drive.py:27-50`). Likewise, web and ebook publication is handled by shell/CI workflows (`.github/workflows/www_latest_update.yml:15-95`, `.github/pdf/scripts/make-pdf.sh:360-409`).

## 3. Orchestration Pattern

Closest match: **other (CI workflow automation pipeline)**, not multi-agent orchestration. Control flow is sequential, job-step based GitHub Actions automation, where workflow steps invoke scripts and external CLIs.

Example control flow excerpt from workflow (trigger -> generate -> branch/PR):

```23:37:.github/workflows/build-checklists.yml
    - name: Setup Python
      uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6
      with:
        python-version: "3.10"
    - name: Install Dependencies
      run: |
        pip install openpyxl pydrive
    - name: Generate JSON Checklist
      run: |
        python3 ./.github/json/scripts/generate_checklist_json.py
```

Example script-level orchestration (build -> enrich -> report -> write output):

```781:790:.github/json/scripts/generate_checklist_json.py
def main() -> None:
    data = build_checklist()
    data, existing_cre_ids, unique_ids, opencre_failures = enrich_with_opencre(data)
    _write_cre_opencre_summary_report(
        data, existing_cre_ids, unique_ids, opencre_failures
    )
    _write_empty_objectives_report(_empty_objective_entries(data))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    OUTPUT_PATH.write_text(text, encoding="utf-8")
```

## 4. Tools & External Integrations

- **GitHub Actions + GitHub CLI (`gh`)** for automation and PR creation, wired in `.github/workflows/www_latest_update.yml:83-95` and `.github/workflows/build-checklists.yml:63-76`.
- **OpenCRE HTTP API** (`https://www.opencre.org/rest/v1/standard/...`) used to enrich checklist entries with CRE mappings, wired in `.github/json/scripts/generate_checklist_json.py:27-31` and network calls at `:95-145`, `:210-233`.
- **Google Drive API (PyDrive)** for publishing checklist XLSX, wired in `.github/xlsx/scripts/upload-to-google-drive.py:1-2` and `:27-50`.
- **Local file-system transforms** over Markdown corpus (`document/**`) to produce JSON/XLSX/PDF/web-ready content, wired across `.github/json/scripts/generate_checklist_json.py`, `.github/xlsx/scripts/build-checklist.py`, and `.github/pdf/scripts/make-pdf.sh`.
- **PDF toolchain/CLI utilities** (`md-to-pdf`, `pdftk`, `sed`, `find`) for ebook generation, wired in `.github/pdf/scripts/make-pdf.sh:50-53`, `:375-381`, `:398-409`.
- **No MCP servers, browser automation frameworks, vector DBs, or LLM APIs** found in repository runtime code.

## 5. Notable Code Walkthrough

- `.github/json/scripts/generate_checklist_json.py:738-794` - Core generator that parses WSTG markdown into structured JSON, enriches test IDs with OpenCRE mappings, emits quality/status markdown reports, and writes `checklists/checklist.json`.
- `.github/workflows/build-checklists.yml:1-95` - CI workflow that reacts to `document/**` changes, runs checklist generation scripts, conditionally creates a branch/PR, and publishes XLSX to Google Drive.
- `.github/xlsx/scripts/build-checklist.py:94-148` - Converts checklist JSON into formatted Excel using an existing template (`openpyxl`) and updates checksum in `checklists/README.md`.
- `.github/workflows/www_latest_update.yml:43-95` - Deploy workflow that clones target website repo, copies latest docs, rewrites navigation/front matter, pushes branch, and opens PR automatically.
- `.github/pdf/scripts/make-pdf.sh:360-409` - End-to-end PDF build script combining markdown preprocessing, chapter PDF generation, bookmark injection, and final consolidated output.

## 6. Use-Case Mapping

The assigned label **“RAG + Agents” appears incorrect** for this repository. There is no retrieval pipeline feeding an LLM, no prompt orchestration, and no runtime multi-agent collaboration. The repo’s executable logic is best categorized as **Workflow Automation**: deterministic CI/CD pipelines and content transformation scripts triggered by repository changes (`.github/workflows/*.yml`, `.github/*/scripts/*`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strongly structured documentation corpus with stable taxonomy (`document/README.md`) suitable for downstream tooling.
  - Reproducible automation for multiple output formats (JSON/XLSX/PDF/web) from one markdown source.
  - Practical external integrations (OpenCRE, Google Drive, GitHub PR automation) implemented in plain scripts.
  - Good CI operationalization: change detection, conditional execution, and artifact publishing.

- **Limitations:**
  - Not an LLM/agent system; no inference-time autonomy, planning, or role-based agent coordination.
  - Workflow scripts are mostly imperative shell/Python with limited abstraction; maintainability may be script-dependent.
  - No dedicated architecture for conversational interfaces, tool-calling agents, or memory/state beyond CI job context.
  - External dependency failures (OpenCRE/API/network/auth) can impact pipeline reliability.

- **Research relevance:**
  - Useful as evidence of **documentation-to-artifact automation pipelines**, not MAS behavior.
  - Useful for studying governance and reproducibility in security knowledge engineering.
  - Useful as a high-quality corpus source for *future* RAG systems, but not itself a RAG+agent implementation.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
