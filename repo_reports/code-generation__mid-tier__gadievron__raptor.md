---
repo_name: gadievron/raptor
url: "https://github.com/gadievron/raptor"
stars: 2330
forks: 359
contributors_count: 19
last_commit_date: "2026-04-22T23:07:23+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T14:10:31.297185+00:00"
model: auto
duration_s: 89.2
clone_size_kb: 15943
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`gadievron/raptor` is a Python-first security automation framework that runs a multi-phase pipeline over a target repo or binary, not a generic chat agent. Users typically run `python3 raptor.py agentic --repo <target>` (or slash-command wrappers), and RAPTOR executes scanner stages (Semgrep/CodeQL), exploitability validation, LLM-based triage, optional exploit/patch generation, and report generation. The core output is structured JSON/Markdown artifacts (for example `orchestrated_report.json`, `agentic-report.md`) plus optional generated exploit/patch files. The project is designed to make offensive/defensive workflows repeatable and budget-aware, with fallback between external APIs and Claude Code subprocess agents. In practice it automates end-to-end vulnerability analysis workflow more than it automates application code authoring.

## 2. Agent Framework & Architecture

Framework usage is **custom orchestration**, not LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex. I found no imports for those frameworks across the codebase; orchestration is hand-built with Python modules and thread pools (`packages/llm_analysis/orchestrator.py`, `packages/llm_analysis/dispatch.py`).

Architecture is split into phases orchestrated by `raptor_agentic.py`: scan, validate, prep, then agentic analysis orchestration. “Intelligence” lives in prompt builders/task classes and provider routing, not in a graph DSL. Phase 3 (`packages/llm_analysis/agent.py`) prepares enriched per-finding contexts; Phase 4 (`packages/llm_analysis/orchestrator.py`) dispatches specialized tasks (analysis, retry, consensus, exploit, patch, group-analysis) with model-role routing (`packages/llm_analysis/tasks.py`, `packages/llm_analysis/llm/config.py`).

There are effectively multiple runtime agents: either (a) external LLM calls via provider adapters, or (b) Claude Code sub-agents invoked as sandboxed `claude -p` subprocesses with constrained tool permissions (`packages/llm_analysis/cc_dispatch.py`). This is true multi-agent coordination: multiple finding-level workers plus consensus workers and group-analysis workers under a central orchestrator.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker pipeline with parallel worker pools** (plus staged workflow automation). A top-level manager (`raptor_agentic.py`) executes sequential phases; within Phase 4, `orchestrate()` is a manager that fans out parallel task workers over findings via a generic dispatcher.

```715:726:raptor_agentic.py
from packages.llm_analysis.orchestrator import orchestrate
orchestration_result = orchestrate(
    prep_report_path=analysis_report,
    repo_path=original_repo_path,
    out_dir=out_dir,
    max_parallel=args.max_parallel,
    max_findings=args.max_findings,
    no_exploits=args.no_exploits,
    no_patches=args.no_patches,
)
```

```285:353:packages/llm_analysis/orchestrator.py
analysis_results = dispatch_task(AnalysisTask(), findings, dispatch_fn, role_resolution, results_by_id, cost_tracker, max_parallel)
dispatch_task(RetryTask(results_by_id=results_by_id), findings, dispatch_fn, role_resolution, results_by_id, cost_tracker, max_parallel)
if consensus_models:
    dispatch_task(ConsensusTask(), findings, dispatch_fn, role_resolution, results_by_id, cost_tracker, max_parallel)
if not no_exploits:
    dispatch_task(ExploitTask(), findings, dispatch_fn, role_resolution, results_by_id, cost_tracker, max_parallel)
if not no_patches:
    dispatch_task(PatchTask(), findings, dispatch_fn, role_resolution, results_by_id, cost_tracker, max_parallel)
```

This is not peer-to-peer swarming and not event-driven pub/sub; control is centralized and phase/task ordered.

## 4. Tools & External Integrations

- **Static analysis engines (Semgrep, CodeQL)** wired in `raptor_agentic.py:450-495` and launched as subprocesses (`packages/static-analysis/scanner.py`, `packages/codeql/agent.py`).
- **Claude Code sub-agent runtime** via `claude -p` subprocess invocation in `packages/llm_analysis/cc_dispatch.py:31-38`, including JSON schema output and budget caps.
- **External LLM APIs** (Anthropic, OpenAI-compatible endpoints, Gemini, Mistral, Ollama) through provider abstraction in `packages/llm_analysis/llm/providers.py:426-998` and model-role config in `packages/llm_analysis/llm/config.py:455-515`.
- **Sandbox/egress controls** for untrusted subprocesses and Claude sub-agents through `core.sandbox.run(...)` in `packages/llm_analysis/cc_dispatch.py:60-65`, implemented in `core/sandbox/*`.
- **Filesystem + repo code reading tools for Claude sub-agents** explicitly restricted to `Read,Grep,Glob` in `packages/llm_analysis/cc_dispatch.py:35`.
- **MCP-related trust gate (not active tool execution in this pipeline)**: `.mcp.json` and risky server config are inspected to block unsafe dispatch in `core/security/cc_trust.py:25-35` and `:236-257`.
- **Optional binary exploit feasibility tooling** via `packages.exploit_feasibility` called in `raptor_agentic.py:367-375`.

No vector database/RAG store pipeline is central here; this repo is primarily orchestration around scanners + LLM calls + subprocess agents.

## 5. Notable Code Walkthrough

- `raptor_agentic.py:405-726` - Main end-to-end workflow controller: runs scanner processes, validation pass, prep pass, and then hands findings to orchestration; this is the primary runtime entry for multi-agent behavior.
- `packages/llm_analysis/orchestrator.py:137-442` - Phase 4 manager: picks dispatch backend (external LLM vs Claude Code), runs parallel task stages, applies retries/consensus, aggregates costs, and writes `orchestrated_report.json`.
- `packages/llm_analysis/dispatch.py:123-270` - Generic concurrent dispatch engine using `ThreadPoolExecutor`; this is the core worker execution loop used by all task types.
- `packages/llm_analysis/tasks.py:21-318` - Defines agent roles/tasks (`AnalysisTask`, `ConsensusTask`, `ExploitTask`, `PatchTask`, `RetryTask`, `GroupAnalysisTask`) and their selection/finalization logic.
- `packages/llm_analysis/cc_dispatch.py:25-87` - Claude Code sub-agent adapter: builds constrained CLI invocation, applies sandboxing, parses structured envelopes, and returns normalized dispatch results.

## 6. Use-Case Mapping

The assigned primary use case (**Code Generation**) is **not the best fit** after reading the code. RAPTOR does generate exploit/patch text in some branches, but that is a sub-step inside a larger security workflow pipeline. The dominant behavior is orchestrating multi-stage analysis/validation/execution flows across tools and models (`raptor_agentic.py`, `orchestrator.py`), with reporting and lifecycle management as first-class outputs.

A better label is **Workflow Automation**: the repo automates a complex security research workflow end-to-end, coordinating scanners, validators, LLM agents, budgets, retries, and consensus.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear staged pipeline with explicit phase boundaries and artifacts (`raptor_agentic.py`).
  - Real multi-agent coordination (analysis + consensus + retry + exploit + patch + group-level reasoning).
  - Strong operational safeguards around untrusted execution and Claude sub-agent dispatch (`core/sandbox`, `cc_trust.py`).
  - Provider-agnostic LLM routing with role-based model assignment and fallback logic (`llm/config.py`, `llm/providers.py`).
  - Practical cost/budget tracking integrated into orchestration decisions (`orchestrator.py:30-134`).

- **Limitations:**
  - Much orchestration depends on subprocess conventions and file artifacts; less formally typed inter-agent state than graph frameworks.
  - Prompt-heavy logic is embedded in Python strings, which can become hard to audit/version at scale (`agent.py`, `cc_dispatch.py`).
  - Parallel dispatch is thread-pool based and in-process; no durable distributed queue/executor for very large workloads.
  - Some behavior is environment-sensitive (tool installs, keys, local `claude` availability), so reproducibility varies.
  - Despite “agentic” framing, many stages are still deterministic pipeline glue rather than autonomous planning loops.

- **Research relevance:**
  - Evidence of **manager-worker MAS design** in production-like security automation.
  - Example of **hybrid agent substrate**: API LLM agents plus CLI sub-agents with constrained tools.
  - Useful case for studying **safety controls in agent orchestration** (sandboxing, trust-gating, budget cutoffs).
  - Demonstrates **consensus/retry mechanisms** for reducing unstable single-pass LLM judgments.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
