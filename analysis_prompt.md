You are analyzing a multi-agent / agentic-AI GitHub repository that has been
cloned into your current workspace. The repository is the working directory
(cwd) for this session, so you can read files, list directories, and search
the code freely.

# Repository under analysis

- repo_name: {repo_name}
- url: {url}
- stars: {stars}
- forks: {forks}
- contributors_count: {contributors_count}
- last_commit_date: {last_commit_date}
- assigned primary_use_case (from upstream classifier): {primary_use_case}
- popularity tier: {user_tier}
- upstream architecture_labels (heuristic, may be wrong): {architecture_labels}
- upstream use_case_labels (heuristic): {use_case_labels}
- upstream description: {description}

# Your task

Read enough of the actual source code (not just the README) to understand
exactly how this project uses LLM agents. Then produce a single Markdown
report with the EXACT section structure below. Do not add extra top-level
sections. Do not wrap the whole response in a code fence. Output Markdown
directly so it can be saved straight to a `.md` file.

If a section genuinely does not apply (e.g. no external tools), say so
explicitly in 1-2 lines rather than skipping the section.

When you cite code, reference the file path and approximate line numbers
(e.g. `src/agents/planner.py:42-78`). Quote at most ~10 lines of code per
example. Keep total report length under ~1500 words.

---

## 1. Overview

One paragraph (3-5 sentences) describing what this repo is and what problem
it solves. Be concrete: what does a user actually run, and what do they get?

## 2. Agent Framework & Architecture

State which framework(s) are actually used (LangGraph, LangChain, AutoGen,
CrewAI, LlamaIndex, custom, etc.) - confirm by inspecting imports and code,
not by trusting the upstream labels. Describe the high-level architecture
in 1-3 paragraphs: how many agents, how they're defined, where the
"intelligence" lives (prompts, graphs, planners, routers, etc.).

## 3. Orchestration Pattern

Pick the closest match and justify it with file references:
sequential / hierarchical (manager-worker) / graph (LangGraph-style state
machine) / swarm (peer-to-peer) / event-driven / blackboard / other.
Show how control flows between agents (1-2 short code excerpts).

## 4. Tools & External Integrations

List the external tools, APIs, and services the agents can call - e.g. MCP
servers, web search, browser automation (Playwright, Browserbase),
shell/terminal use, vector stores (Chroma, Pinecone, pgvector), databases,
file system, custom HTTP APIs, RAG pipelines. For each, note the file
where it's wired up.

## 5. Notable Code Walkthrough

Pick 3-5 of the most representative files and explain in 1-3 sentences each
what they do and why they matter. Use bullet points with `path:line-range`
references.

## 6. Use-Case Mapping

Explain concretely how this repo realizes the assigned primary use case
(`{primary_use_case}`). If the assignment looks wrong after reading the code,
say so and suggest the better category from: Workflow Automation,
Code Generation, RAG + Agents, Browser / Terminal Use, Simulation.

## 7. Strengths, Limitations & Research Relevance

Three short bullet lists:
- **Strengths:** what this repo does unusually well (3-5 bullets)
- **Limitations:** real gaps you observed in the code (3-5 bullets)
- **Research relevance:** what an academic study of multi-agent systems
  could reasonably cite this repo as evidence of (2-4 bullets)

## 8. Machine-readable classification

End the report with this exact two-line block, plain text, no code fence,
no extra characters before or after. Downstream tooling parses these
verbatim, so the keys and casing must be preserved.

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation

Rules:
- `USES_MAS` must be exactly `yes` or `no`. Use `yes` only if the repo
  actually implements multiple coordinated LLM agents (planner+worker,
  manager+team, swarm, multi-role debate, graph of agents, etc.) at
  runtime. A single-agent assistant, a chatbot, an awesome-list, a UI
  library, or pure infrastructure code is `no` even if it mentions agents.
- `FINAL_USE_CASE` must be EXACTLY one of:
  `Workflow Automation`, `Code Generation`, `RAG + Agents`,
  `Browser / Terminal Use`, `Simulation`, `None`.
  Use `None` only when the repo doesn't fit any of those (e.g. an
  awesome-list or a non-agent library) - in that case `USES_MAS` is
  almost always `no`.

End of report. Do not append any extra commentary after Section 8.
