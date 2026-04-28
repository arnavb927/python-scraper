---
repo_name: natlas/natlas
url: "https://github.com/natlas/natlas"
stars: 658
forks: 91
contributors_count: 17
last_commit_date: "2026-03-03T17:32:57+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T16:07:59.586468+00:00"
model: auto
duration_s: 78.0
clone_size_kb: 2357
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`natlas/natlas` is an attack-surface scanning platform, not an LLM-agent project. Users run a `natlas-server` plus one or more `natlas-agent` workers; the server assigns scan targets and policies, and agents execute network scans (primarily `nmap`) and return structured results for indexing/search (`README.md:15-45`, `natlas-server/app/api/routes.py:22-82`). The core outcome is continuous, orchestrated host/port/service visibility across scoped IP ranges, with optional screenshots and rescans (`natlas-agent/natlas/threadscan.py:49-123`). In practice, this automates recurring security scan workflows and centralizes results in Elasticsearch-backed views.

## 2. Agent Framework & Architecture

This repository does **not** use LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, or any LLM SDK. Dependency manifests only include infra/security stack libraries (Flask, Elasticsearch, requests, pydantic, libnmap, etc.) and no LLM tooling (`natlas-server/pyproject.toml:8-39`, `natlas-agent/pyproject.toml:1-20`).

Architecture is custom and service-oriented: a central Flask server exposes work APIs, and distributed scan “agents” are daemon workers that poll for tasks, execute scans, and submit results (`natlas-server/app/api/routes.py:22-82`, `natlas-agent/natlas/net.py:21-25`, `natlas-agent/natlas-agent.py:109-136`). Intelligence here is operational logic (scope filtering, PRNG-based target scheduling, rescan queue handling), not prompt-driven reasoning (`natlas-server/app/scope/scan_manager.py:33-83`, `natlas-server/app/scope/scope_manager.py:76-114`).

So the term “agent” in this codebase means autonomous scan worker processes, not LLM role-agents.

## 3. Orchestration Pattern

Closest pattern: **hierarchical manager-worker (server dispatcher + many worker agents)** with queue-based, polling orchestration.

Server-side dispatch path:
```22:31:natlas-server/app/api/routes.py
@bp.route("/getwork", methods=["GET"])
@is_agent_authenticated
def getwork() -> Response:
    manual = request.args.get("target", "")
    if "natlas-agent" in request.headers["user-agent"]:
        verstr = request.headers["user-agent"].split("/")[1]
        if verstr != current_app.config["NATLAS_VERSION"]:
            errmsg = f"The server detected you were running version {verstr} but the server is running {current_app.config['NATLAS_VERSION']}"
```

Worker execution loop:
```159:167:natlas-agent/natlas/threadscan.py
def run(self) -> None:
    while True:
        with push_scope() as scope:
            add_breadcrumb(
                category="scan_workflow", message="Fetching work", level="info"
            )
            work_item = self.get_work()
```

Control flow is: server selects next target (`scope_manager` / `scan_manager`), agent polls `/api/getwork`, runs `nmap` + optional screenshot tools, then POSTs to `/api/submit` (`natlas-server/app/api/routes.py:84-207`, `natlas-agent/natlas/threadscan.py:140-207`). This is not a graph/swarm LLM orchestration model.

## 4. Tools & External Integrations

- **Nmap subprocess execution** for primary scan workload (`natlas-agent/natlas/threadscan.py:21-47`, `:62-70`).
- **Aquatone** for web screenshots via subprocess (`natlas-agent/natlas/screenshots.py:83-114`).
- **vncsnapshot/xvfb-run** for VNC screenshots (`natlas-agent/natlas/screenshots.py:117-149`).
- **HTTP API between agents and server** using `requests` (`natlas-agent/natlas/net.py:33-115`, endpoints at `:21-25`).
- **Elasticsearch** for scan result storage/search (`natlas-server/pyproject.toml:10-12`, runtime wiring in `docker-compose.yml:6-31`, result writes in `natlas-server/app/api/routes.py:124`, `:197`).
- **PostgreSQL + SQLAlchemy** for app metadata/config/state (`docker-compose.yml:53-70`, `:128`, and DB model usage in `natlas-server/app/api/prepare_work.py:61-69`).
- **MinIO (S3-compatible)** for screenshot/object storage in deployment wiring (`docker-compose.yml:33-52`, `:129-133`).
- **OpenTelemetry + Zipkin** optional observability services (`docker-compose.yml:83-98`).
- **No MCP, browser automation frameworks, terminal-agent tools, or vector DB/RAG pipeline** beyond the security scanning stack.

## 5. Notable Code Walkthrough

- `natlas-server/app/api/routes.py:22-207` - Main control-plane API: assigns work (`/getwork`), validates/submits scan payloads (`/submit`), enforces scope/version/auth checks, and persists accepted results.
- `natlas-agent/natlas-agent.py:45-136` - Agent entrypoint: bootstraps environment/capability checks, starts a thread pool of scan workers, supports manual target mode and continuous auto-poll mode.
- `natlas-agent/natlas/threadscan.py:49-207` - Worker execution core: builds scan commands, runs scans with timeout handling, optional screenshot collection, submission, and cleanup.
- `natlas-server/app/scope/scan_manager.py:33-83` - Target scheduling engine: computes effective scope and uses a cyclic PRNG to iterate addresses across scan cycles.
- `natlas-server/app/api/prepare_work.py:60-79` - Work-item assembly: combines scan reason, target tags, global agent config, services hash, and unique scan ID into the payload sent to agents.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is correct for this repository, but it is **not AI-agentic** in the LLM sense. Natlas automates a full scanning workflow: scope/rule management on server, distributed task dispatch to agents, asynchronous scan execution, result normalization, and storage/search (`natlas-server/app/api/routes.py:53-81`, `natlas-agent/natlas/threadscan.py:159-207`). The automation target is continuous attack-surface monitoring operations, not code generation, RAG, or agentic reasoning.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear manager-worker separation between server orchestration and distributed workers.
  - Robust operational controls (auth headers, retry/backoff, timeout handling, scope validation).
  - Practical scan-cycle scheduling using cyclic PRNG over effective scope.
  - Extensible data collection pipeline (nmap + screenshots + tags + rescans).
  - Production-minded observability/error hooks (Sentry/OpenTelemetry).

- **Limitations:**
  - No LLM components despite “agent” terminology; unusable as evidence for LLM multi-agent design.
  - Polling-based control plane (no push/event bus), which may add latency/overhead at scale.
  - Some technical debt explicitly noted in scope manager cache/session handling (`scope_manager.py:23-26`).
  - Toolchain tightly coupled to external binaries (`nmap`, `aquatone`, `vncsnapshot`) and host capabilities.
  - Minimal abstraction for richer autonomous strategy beyond predefined scan logic.

- **Research relevance:**
  - Good example of **non-LLM autonomous worker orchestration** in security operations.
  - Useful for studying manager-worker reliability patterns (retry, backoff, validation, cleanup) in distributed automation.
  - Evidence for cyclical randomized scheduling of large IP scopes in continuous scanning systems.
  - Not suitable for claims about prompt engineering, agent planning, or LLM coordination.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
