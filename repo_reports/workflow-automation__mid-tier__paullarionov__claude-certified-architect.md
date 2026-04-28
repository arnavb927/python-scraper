---
repo_name: paullarionov/claude-certified-architect
url: "https://github.com/paullarionov/claude-certified-architect"
stars: 1396
forks: 300
contributors_count: 8
last_commit_date: "2026-04-14T19:07:26+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T16:01:15.619525+00:00"
model: auto
duration_s: 65.5
clone_size_kb: 28526
uses_mas: no
final_use_case: None
---
## 1. Overview

This repository is primarily a certification study package, not an executable agent system. A user mainly reads `guide_*.md` files and can open prebuilt `practical_test_*.html` mock exams; maintainers can also run a helper script to regenerate those HTML tests from question data (`utils/build_practical_test_html.py:18-25`, `:422-475`). The only automation code in-repo is content/build tooling (HTML generation and PDF publishing via GitHub Actions), not an LLM application runtime (`.github/workflows/markdown-to-pdf.yml:13-66`). In practice, users get multilingual exam-prep documentation and interactive quiz pages.

## 2. Agent Framework & Architecture

No actual agent framework runtime is implemented in this repository. There are **no real imports** for CrewAI/LangGraph/LangChain/AutoGen/Agent SDK in executable code; the only Python file imports standard library modules (`json`, `subprocess`, `os`, `sys`) for static content generation (`utils/build_practical_test_html.py:5`).

The repo does discuss multi-agent architecture conceptually in the study guide (e.g., `AgentDefinition`, coordinator/subagent, `Task` tool), but those are instructional snippets inside Markdown, not wired runtime code (`guide_en.MD:332-409`). So the architecture here is: documentation + generated quiz artifacts, with no live planner/router/agent graph execution path.

## 3. Orchestration Pattern

Closest match: **other (documentation/build pipeline), not agent orchestration**.

Control flow in executable code is a simple sequential build loop, not multi-agent coordination:
- Load question data by spawning another script, then build HTML per language (`utils/build_practical_test_html.py:18-25`, `:473-475`).
- CI job sequentially converts guides to PDFs and commits artifacts (`.github/workflows/markdown-to-pdf.yml:35-66`).

Example excerpts:

```18:25:utils/build_practical_test_html.py
def get_questions(lang):
    result = subprocess.run(
        ["python3", "extract_question.py", lang, "all"],
        capture_output=True, text=True, cwd=ROOT_DIR
    )
    return json.loads(result.stdout)
```

```473:475:utils/build_practical_test_html.py
for lang in BUILD_LANGS:
    build(lang)
```

## 4. Tools & External Integrations

No runtime LLM-agent tools are wired in code. What is actually integrated:

- **Local subprocess execution** for content generation via `subprocess.run` (`utils/build_practical_test_html.py:19-22`).
- **GitHub Actions CI** for Markdown-to-PDF conversion (`.github/workflows/markdown-to-pdf.yml:13-53`).
- **Node/npm CLI tool** `md-to-pdf` used in CI (`.github/workflows/markdown-to-pdf.yml:32-45`).
- **Git push from CI** to commit generated PDFs (`.github/workflows/markdown-to-pdf.yml:54-64`).

The guide references MCP, Claude API, and subagents, but these are educational examples only (`guide_en.MD:460-503`, `:332-409`), not active integrations in repository code.

## 5. Notable Code Walkthrough

- `utils/build_practical_test_html.py:18-25,422-475` — Core script that assembles multilingual interactive test HTML by fetching question JSON and embedding CSS/JS templates; this is the main executable artifact builder.
- `utils/build_practical_test_html.py:234-420` — Embedded frontend quiz logic (state, navigation, answer checking, summary rendering), showing this repo’s “app” behavior is static exam UI, not LLM orchestration.
- `.github/workflows/markdown-to-pdf.yml:13-66` — Build pipeline that converts `guide_*.md` to PDFs and optionally commits them back, representing the repository’s primary automation workflow.
- `guide_en.MD:332-409` — Multi-agent patterns (coordinator/subagents/`Task`) presented as curriculum content; important for understanding intent but not implemented runtime behavior.
- `guide_en.MD:469-487` — Example `.mcp.json` snippet for GitHub/Jira MCP servers; again instructional reference, not present as executable config in this repo.

## 6. Use-Case Mapping

The assigned category (**Workflow Automation**) is only partially accurate. The repository does automate documentation packaging (HTML test generation and PDF CI), so there is lightweight workflow automation in the tooling layer (`utils/build_practical_test_html.py:473-475`, `.github/workflows/markdown-to-pdf.yml:35-66`).  

However, for **agentic-AI classification**, this repo is better categorized as **None**: it is a study-material corpus about agents, not a running multi-agent system or LLM workflow implementation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong, structured educational coverage of Claude API/Agent SDK/MCP concepts with scenario-based framing (`guide_en.MD:55-68`, `:306-409`).
  - Practical, multilingual delivery format (Markdown + generated HTML quiz + PDF automation).
  - Reproducible content pipeline via CI for keeping docs synchronized (`.github/workflows/markdown-to-pdf.yml:35-66`).
  - Includes concrete pseudo-code/config examples useful for onboarding (`guide_en.MD:336-345`, `:469-487`).

- **Limitations:**
  - No executable LLM agent runtime, no real agent classes, and no orchestration engine in source code.
  - No dependency manifest or runnable app entrypoint for agent behavior.
  - `build_practical_test_html.py` depends on `extract_question.py`, which is not present in this clone (`utils/build_practical_test_html.py:20`), reducing reproducibility.
  - “Agent” content is descriptive only; cannot empirically evaluate performance, reliability, or coordination mechanisms from this repo alone.

- **Research relevance:**
  - Useful as evidence of how practitioners are taught multi-agent patterns (coordinator/subagent, tool loops, MCP).
  - Useful for curriculum analysis of agent engineering best practices and anti-patterns.
  - Not suitable as evidence of implemented MAS runtime behavior, benchmarking, or systems-level orchestration outcomes.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
