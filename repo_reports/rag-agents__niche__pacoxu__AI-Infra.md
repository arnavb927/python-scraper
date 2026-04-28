---
repo_name: pacoxu/AI-Infra
url: "https://github.com/pacoxu/AI-Infra"
stars: 188
forks: 18
contributors_count: 4
last_commit_date: "2026-04-22T09:58:38+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 2
architecture_labels: [LangChain, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T17:48:50.490509+00:00"
model: auto
duration_s: 70.5
clone_size_kb: 12245
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`pacoxu/AI-Infra` is primarily a curated documentation and benchmarking repository for AI infrastructure learning, not an executable agent application. A user mainly reads Markdown guides (`README.md`, `docs/*`, `agent-infra/README.md`) and can optionally run shell scripts that benchmark Kubernetes sandbox runtimes for agent execution environments rather than running agents themselves (`agent-infra/scripts/agent-sandbox-benchmark/*.sh`). The practical output is a knowledge base (landscape maps, learning paths, case studies) plus benchmark artifacts such as JSONL latency logs and generated Markdown reports. In short, it helps engineers study and evaluate AI-infra components around agents/inference, but does not implement an in-repo LLM agent workflow.

## 2. Agent Framework & Architecture

No runtime LLM agent framework is implemented in this repo. I found no imports/usages of LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, OpenAI SDKs, or equivalent orchestration code in executable source; the code files are Node.js SVG generators and Bash benchmark automation (`scripts/generate-landscape-svg.js:1-331`, `archive/mcm-radar/scripts/generate-mcm-radar-svg.js:1-475`, `agent-infra/scripts/agent-sandbox-benchmark/*.sh`).

The “agent” material is documentation about external ecosystems and patterns, especially Kubernetes-native sandboxing and platform comparisons (`agent-infra/README.md:9-900`). The repo architecture is content-centric: domain docs under `docs/`, agent ecosystem notes under `agent-infra/`, and scripts for diagram generation and benchmark reproducibility (`STRUCTURE.md:24-49`, `STRUCTURE.md:109-121`).

Where “intelligence” exists, it is human-authored curation and taxonomy (landscape JSON + Markdown), not prompt-defined planning or agent routing.

## 3. Orchestration Pattern

Closest match: **other (scripted automation + documentation pipeline)**, not an agentic orchestration pattern.

Control flow is shell-sequential benchmark automation over runtimes/tasks, with Kubernetes CRD lifecycle calls:

```101:109:agent-infra/scripts/agent-sandbox-benchmark/run-benchmark.sh
apiVersion: agents.x-k8s.io/v1alpha1
kind: Sandbox
metadata:
  name: ${name}
spec:
  podTemplate:
    spec:
      runtimeClassName: ${runtime_class}
```

```218:233:agent-infra/scripts/agent-sandbox-benchmark/run-benchmark.sh
for round in $(seq 1 "${ROUNDS}"); do
  for runtime in "${RUNTIME_LIST[@]}"; do
    measure_cold_start "${runtime}" "${round_dir}/cold-start.jsonl"
    for task in ${TASKS}; do
      measure_task_latency "${runtime}" "${task}" "${round_dir}/tasks.jsonl"
    done
  done
done
```

This is benchmark job orchestration, not multi-agent reasoning/control transfer.

## 4. Tools & External Integrations

- **Kubernetes API via `kubectl`**: create namespaces, apply Sandbox manifests, wait for readiness, exec commands, delete resources (`agent-infra/scripts/agent-sandbox-benchmark/deploy.sh:21-63`, `run-benchmark.sh:148-163`, `run-benchmark.sh:189-212`).
- **Kubernetes Agent Sandbox CRDs**: uses `agents.x-k8s.io/v1alpha1` `Sandbox` and warm-pool manifests (`run-benchmark.sh:101-127`, `agent-infra/scripts/agent-sandbox-benchmark/k8s/warmpool-*.yaml`).
- **RuntimeClass integration (gVisor/Kata/VM)**: benchmark targets configured via RuntimeClass resources (`runtimeclasses.yaml:10-67`, `run-benchmark.sh:80-89`).
- **Helm/Go/oha tooling setup**: dependency bootstrap for benchmark environment (`setup.sh:18-43`).
- **Node.js + filesystem for diagram generation**: local JSON-to-SVG rendering; no LLM/API calls (`scripts/generate-landscape-svg.js:3-11`, `archive/mcm-radar/scripts/generate-mcm-radar-svg.js:11-18`).
- **No external LLM API/tool-calling runtime** in repo code; references to MCP/LangChain/CrewAI are explanatory docs only (`agent-infra/README.md:328-438`, `README.md:284-335`).

## 5. Notable Code Walkthrough

- `agent-infra/scripts/agent-sandbox-benchmark/run-benchmark.sh:1-245` - Core executable workflow: defines task suites, maps runtimes to RuntimeClasses, provisions per-task sandboxes, runs commands inside them, and records latency/cold-start JSONL. This is the most “operational” logic in the repo.
- `agent-infra/scripts/agent-sandbox-benchmark/report.sh:1-115` - Post-processing pipeline: parses benchmark JSONL with Python stdlib and emits percentile/error tables in Markdown, turning raw runs into comparable metrics.
- `agent-infra/scripts/agent-sandbox-benchmark/deploy.sh:1-67` - Environment deployment automation for warm pools and namespace setup, wiring benchmark assumptions to a Kubernetes cluster.
- `scripts/generate-landscape-svg.js:1-331` - Data-driven visualization generator for AI-infra landscape; demonstrates repository’s curation-first workflow (JSON source -> maintained SVG artifact).
- `STRUCTURE.md:24-121` - Canonical architecture of the repository itself (docs domains, agent-infra track, scripts), confirming this is a knowledge/benchmark repo rather than an agent runtime codebase.

## 6. Use-Case Mapping

The assigned label **RAG + Agents** does **not** match the implemented code. The repository discusses RAG, agent frameworks, and protocols extensively in docs, but does not implement a retrieval pipeline, vector store integration, LLM prompting loop, or coordinated agents at runtime. What it concretely realizes is **workflow automation for infra benchmarking and documentation generation** (shell + Kubernetes + report generation), plus curated learning content. A better category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong, well-structured AI-infra knowledge curation with explicit taxonomy and maintenance rules (`STRUCTURE.md:13-23`, `README.md:147-335`).
  - Reproducible sandbox-runtime benchmark scripts with clear runtime comparators (`run-benchmark.sh:26-33`, `run-benchmark.sh:80-89`).
  - Practical Kubernetes integration details (RuntimeClass, warm pools, namespace setup) useful for ops experimentation (`deploy.sh:21-55`, `runtimeclasses.yaml:10-67`).
  - Data-driven diagram generation avoids manual drift for landscape visuals (`scripts/generate-landscape-svg.js:6-11`, `scripts/generate-landscape-svg.js:330-331`).

- **Limitations:**
  - No in-repo LLM agent implementation (single-agent or multi-agent) despite agent-focused docs.
  - No runnable RAG pipeline (no ingestion/retrieval/indexing code, no vector DB wiring).
  - No tests/CI for script correctness or benchmark reproducibility robustness.
  - Benchmark scripts run one sandbox per sample/task, which may not reflect realistic pooled long-session agent workloads (`run-benchmark.sh:183-212`).

- **Research relevance:**
  - Useful as evidence of **ecosystem framing and operational concerns** around agent infrastructure (sandboxing, runtime isolation, standards like MCP) rather than agent algorithms.
  - Useful for studying **Kubernetes-oriented benchmarking methodology** for sandbox runtimes supporting agent execution.
  - Useful as an example of **documentation-as-infrastructure** in rapidly evolving AI infra domains.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
