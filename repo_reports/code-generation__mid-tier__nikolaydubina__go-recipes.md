---
repo_name: nikolaydubina/go-recipes
url: "https://github.com/nikolaydubina/go-recipes"
stars: 4482
forks: 166
contributors_count: 15
last_commit_date: "2026-04-03T11:43:48+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T13:27:12.415097+00:00"
model: auto
duration_s: 53.5
clone_size_kb: 39100
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`go-recipes` is not an agent runtime; it is a curated catalog of Go tooling recipes, maintained as structured data and rendered into documentation. A contributor edits `page.yaml` entries (tool name, description, install command, usage command), then runs `go generate` to rebuild `README.md` via the `mdpage` generator (`main.go:3-5`). End users primarily consume the generated README as a searchable cookbook of commands across testing, dependencies, visualization, code generation, refactoring, and build workflows (`README.md:14-120`). In practice, what users “run” is individual CLI snippets from the recipes, not this repository as an autonomous application.

## 2. Agent Framework & Architecture

No LLM or agent framework is used in this repository. There are no imports/usages of LangGraph, LangChain, AutoGen, CrewAI, LlamaIndex, OpenAI/Anthropic SDKs, or prompt/planner/router abstractions in the codebase; executable code is a minimal stub with a `go:generate` directive (`main.go:3-5`).

Architecture is static-content generation:  
- Source of truth: `page.yaml` (large structured recipe dataset, grouped by topic) (`page.yaml:14-35`).  
- Build step: `go generate` invokes `github.com/nikolaydubina/mdpage` to transform YAML into Markdown (`main.go:3`).  
- Output artifact: `README.md` with generated TOC and sections (`README.md:14-103`).  

So the “intelligence” is editorial curation in YAML, not runtime decision-making by agents.

## 3. Orchestration Pattern

Closest match: **other (static document generation pipeline)**, not a multi-agent orchestration pattern.

Control flow is one-step generation:

```3:5:main.go
//go:generate go run github.com/nikolaydubina/mdpage -page page.yaml -o README.md

func main() { /* 👋🏻 */ }
```

And the PR template enforces that workflow (edit YAML -> regenerate README):

```1:4:.github/pull_request_template.md
- [ ] do not edit `README.md` directly
- [ ] `page.yaml` updated
- [ ] `go generate` run
```

There is no planner-worker, graph state machine, or event bus for agents at runtime.

## 4. Tools & External Integrations

No agent-callable tool layer exists. Relevant integrations are documentation/build-time only:

- **`mdpage` generator**: used to compile `page.yaml` into `README.md` (`main.go:3`).  
- **GitHub (repo metadata/assets links)**: many recipe URLs and images point to external GitHub projects (`page.yaml:39-43`, `page.yaml:129-133`).  
- **Codecov mention**: appears as a recipe target, not integrated runtime API in this repo (`page.yaml:25-29`).  
- **Many external Go CLIs listed**: e.g., `gotestsum`, `go-cover-treemap`, `goc`, etc., but only as text recipes/commands in YAML (`page.yaml:31-45`, `page.yaml:99-110`).  

No MCP servers, browser automation, vector DB, embedded RAG pipeline, or internal API clients are wired up here.

## 5. Notable Code Walkthrough

- `main.go:3-5` - Defines the repository’s only executable behavior: a `go:generate` command invoking `mdpage` to build docs from YAML. This is the core automation mechanism.
- `page.yaml:14-120` - Primary data model for the project (groups, entries, descriptions, requirements, commands). This file is effectively the product.
- `README.md:14-103` - Generated output showing the structured table of contents and rendered recipes; demonstrates that repository value is documentation delivery.
- `.github/pull_request_template.md:1-4` - Encodes contribution workflow constraints ensuring generated docs remain in sync with YAML source.

## 6. Use-Case Mapping

The assigned label **Code Generation** is partially understandable (the repo includes many *examples* of code-generation tools), but this repository itself does **not** implement code generation logic for user source code via agents or a dedicated generator service. Its own operation is better classified as **Workflow Automation**: maintain a structured recipe database and auto-generate documentation (`main.go:3`, `.github/pull_request_template.md:1-3`).  

It is also **not** a multi-agent system; there are zero coordinated LLM agents in runtime code.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear single-source-of-truth architecture (`page.yaml`) with deterministic generation into `README.md`.
  - Scales to a very large catalog while preserving consistent schema (title, description, commands, requirements).
  - Contributor process is explicit and enforceable (`do not edit README directly`, run `go generate`).
  - High practical utility as a discovery index for Go tooling across many workflow domains.

- **Limitations:**
  - No executable application logic beyond docs generation; minimal code surface.
  - No LLM, no agent coordination, no runtime autonomy.
  - No validation/testing pipeline visible for schema correctness or dead links in recipes.
  - Heavy dependence on external tool links can drift over time without automated checks.

- **Research relevance:**
  - Useful as an example of **human-curated workflow knowledge base**, not MAS behavior.
  - Could support studies on tooling taxonomy/knowledge organization in developer ecosystems.
  - Not suitable evidence for agent orchestration, planning, tool-use policies, or cooperative multi-agent dynamics.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
