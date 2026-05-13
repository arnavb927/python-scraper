---
repo_name: KeygraphHQ/shannon
url: "https://github.com/KeygraphHQ/shannon"
stars: 39810
forks: 4390
contributors_count: 7
last_commit_date: "2026-04-21T07:45:50+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T06:43:20.473619+00:00"
model: auto
duration_s: 101.6
clone_size_kb: 51191
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`KeygraphHQ/shannon` is an autonomous, multi-agent penetration-testing pipeline that users run via `./shannon start ...` (local) or `npx @keygraph/shannon start ...` (npx mode), which launches a Dockerized Temporal worker stack and executes a full scan workflow (`apps/cli/src/commands/start.ts:29-115`). The system analyzes a target web app plus its source repo, runs specialist LLM agents for recon, vulnerability analysis, and exploitation, and writes structured deliverables into `.shannon/deliverables` and workspace logs (`apps/worker/src/temporal/workflows.ts:431-553`). The core value is automated end-to-end security workflow execution with retry, checkpointing, and resume support rather than interactive chat. Users get per-phase markdown findings and a final consolidated security assessment report.

## 2. Agent Framework & Architecture

This repo does **not** use LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex (no such imports found). It uses a **custom multi-agent architecture** built on:
- Anthropic Claude Agent SDK (`@anthropic-ai/claude-agent-sdk`) for agent execution (`apps/worker/src/ai/claude-executor.ts:9-10`, `apps/worker/package.json:21-33`)
- Temporal for orchestration/state/retries (`apps/worker/src/temporal/workflows.ts:26-33`)

Agents are explicitly declared in a static registry (`AGENTS`) with names, prerequisites, prompt templates, deliverable filenames, and model tier (`apps/worker/src/session-manager.ts:14-107`). “Intelligence” primarily lives in prompt templates (`apps/worker/prompts/*.txt`) plus runtime prompt interpolation and routing logic (`apps/worker/src/services/prompt-manager.ts:355-405`). Execution lifecycle (prompt load, SDK run, output validation, git checkpoint/rollback, auditing) is centralized in `AgentExecutionService` (`apps/worker/src/services/agent-execution.ts:92-231`).

The architecture is pipeline-specialist based: pre-recon and recon agents run first, then five vulnerability specialists, then matching exploit specialists, then a final report agent. Prompt-level specialization is explicit (e.g., `vuln-xss`, `exploit-authz`) and each specialist can run with isolated Playwright sessions mapped by agent (`apps/worker/src/session-manager.ts:151-176`, `apps/worker/src/services/prompt-manager.ts:378-388`).

## 3. Orchestration Pattern

Closest match: **other (hybrid staged pipeline + parallel pipelined branches)**.

It is not a peer swarm or manager chatbot. Temporal workflow code implements sequential early phases, then concurrent vuln→exploit pipelines (up to configurable concurrency), then sequential reporting (`apps/worker/src/temporal/workflows.ts:431-537`).

```450:479:apps/worker/src/temporal/workflows.ts
async function runVulnExploitPipeline(...) {
  const vulnAgentName = `${vulnType}-vuln`;
  const exploitAgentName = `${vulnType}-exploit`;
  ...
  vulnMetrics = await runVulnAgent();
  ...
  const decision = await a.checkExploitationQueue(activityInput, vulnType);
  ...
  } else if (decision.shouldExploit && exploit) {
    exploitMetrics = await runExploitAgent();
```

```500:520:apps/worker/src/temporal/workflows.ts
const maxConcurrent = input.pipelineConfig?.max_concurrent_pipelines ?? 5;
...
const pipelineResults = await runWithConcurrencyLimit(pipelineThunks, maxConcurrent);
aggregatePipelineResults(pipelineResults);
```

Control flow is workflow-driven (Temporal) rather than LLM-planned at runtime; agents do specialized tasks inside orchestrator-defined stages.

## 4. Tools & External Integrations

- **Claude Agent SDK / LLM runtime**: core message streaming and agent turns via `query(...)` (`apps/worker/src/ai/claude-executor.ts:9`, `332-401`).
- **Temporal orchestration**: workflow/activity runtime, retries, queryable progress (`apps/worker/src/temporal/workflows.ts:92-103`, `196-203`; `apps/worker/src/temporal/worker.ts:420-445`).
- **Docker + Docker Compose**: infra boot and per-scan ephemeral worker containers (`apps/cli/src/docker.ts:75-94`, `169-243`).
- **Browser automation (Playwright CLI/MCP style)**: prompts instruct use of `playwright-cli` with per-agent session IDs (`apps/worker/prompts/recon.txt:75-76`, `126-127`), and env wiring includes Playwright output path (`apps/worker/src/ai/claude-executor.ts:158-160`).
- **Shell/CLI tools used by agents**: prompts direct `save-deliverable` and Bash tooling (`apps/worker/prompts/recon.txt:76-82`); implemented in scripts (`apps/worker/src/scripts/save-deliverable.ts:10-16`, `71-136`).
- **TOTP helper tool**: `generate-totp` CLI for MFA flows (`apps/worker/src/scripts/generate-totp.ts:10-18`; referenced in login prompt `apps/worker/prompts/shared/login-instructions.txt:19-20`).
- **Git integration for checkpoints/recovery**: checkpoint/commit/rollback around agent runs (`apps/worker/src/services/agent-execution.ts:125-139`, `216-240`).
- **Configurable provider backends**: SDK env supports Anthropic API, Bedrock, Vertex, LiteLLM router (`apps/worker/src/ai/claude-executor.ts:167-190`).
- **Injectable external findings/output hooks**: `FindingsProvider`, `CheckpointProvider`, `ReportOutputProvider` extension points (default no-op) (`apps/worker/src/services/container.ts:76-79`, `apps/worker/src/interfaces/findings-provider.ts:13-25`, `apps/worker/src/temporal/activities.ts:835-896`).

## 5. Notable Code Walkthrough

- `apps/worker/src/session-manager.ts:14-107` — Canonical agent registry defining all specialist roles, prerequisites, prompts, and deliverables; this is the static MAS topology.
- `apps/worker/src/temporal/workflows.ts:290-567` — Main orchestrator implementing phase transitions, branch concurrency, exploit gating, resume/skip logic, and final report assembly.
- `apps/worker/src/services/agent-execution.ts:92-231` — Agent lifecycle engine; loads prompts, invokes Claude SDK, validates outputs, and applies git-based transactional behavior.
- `apps/worker/src/ai/claude-executor.ts:127-313` — Low-level LLM execution wrapper with SDK options (`maxTurns`, `permissionMode`), provider/env wiring, streaming loop, and error handling.
- `apps/cli/src/commands/start.ts:50-115` — User entrypoint that ensures Docker image/infra, provisions workspace mounts, and starts isolated worker containers for scans.

## 6. Use-Case Mapping

The assigned primary use case (`Code Generation`) appears **incorrect** for this repository. The system’s core behavior is orchestrating a multi-phase autonomous pentest workflow (preflight, recon, vuln analysis, exploitation, reporting) with retries, checkpoints, and resumability (`apps/worker/src/temporal/workflows.ts:415-553`). While it generates markdown/text artifacts, that generation is a byproduct of workflow automation, not developer code synthesis. A better category is **Workflow Automation** (with secondary overlap in Browser/Terminal Use due to Playwright + shell tool execution in prompts).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear explicit multi-agent decomposition with role-specialized prompts and deliverables (`apps/worker/src/session-manager.ts:14-107`).
  - Production-grade orchestration: retries, heartbeat, resume, checkpointing, and progress queries (`apps/worker/src/temporal/workflows.ts:65-135`, `196-203`, `240-284`).
  - Hybrid sequential+parallel pipeline design enabling efficient concurrent specialization (`apps/worker/src/temporal/workflows.ts:437-520`).
  - Strong operational packaging (Dockerized infra, ephemeral worker-per-scan, workspace isolation) (`apps/cli/src/docker.ts:169-243`).
  - Extensibility hooks for external findings/checkpoint/report output providers (`apps/worker/src/services/container.ts:40-46`, `76-80`).

- **Limitations:**
  - Heavy dependence on prompt instructions for tool behavior correctness (e.g., Task-only source analysis), which may be brittle across model behavior drift (`apps/worker/prompts/recon.txt:74-84`).
  - Tight coupling to Claude Agent SDK; limited abstraction for swapping to non-Claude agent runtimes (`apps/worker/src/ai/claude-executor.ts:9`, `349`).
  - Security scope and operational assumptions are encoded in prompts rather than strongly enforced programmatically for all actions (`apps/worker/prompts/recon.txt:44-66`).
  - Private deliverables git uses hard reset/clean in resume restore path, which is safe for isolated deliverables but operationally sharp-edged (`apps/worker/src/temporal/activities.ts:707-713`).
  - No evidence of learned policy/planner optimization; orchestration is static and hand-authored.

- **Research relevance:**
  - Good real-world example of **LLM multi-agent specialization under deterministic workflow orchestration**.
  - Demonstrates **hybrid orchestration pattern**: deterministic control plane + generative specialist workers.
  - Useful case for studying **reliability engineering in MAS** (retry taxonomies, checkpointing, resumability).
  - Shows practical interplay between **agent prompts, tool ecosystems, and infrastructure-level isolation**.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
