---
repo_name: yzhao062/pyod
url: "https://github.com/yzhao062/pyod"
stars: 9816
forks: 1468
contributors_count: 66
last_commit_date: "2026-04-16T20:28:21+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 8
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-05-05T07:04:51.187101+00:00"
model: auto
duration_s: 93.4
clone_size_kb: 23684
mas_related: yes
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`pyod` is primarily an anomaly detection library, but this version adds an agent-facing orchestration layer (`ADEngine`) that can profile data, choose detectors from a knowledge base, run multiple detectors, fuse their outputs, and iterate from feedback. A user can run it directly in Python (`engine.investigate(X)`), through CLI commands (`pyod info`, `pyod mcp serve`), or via MCP tools exposed to external LLM assistants. The output is a structured investigation state with plans, per-detector results, consensus labels/scores, quality metrics, and report text/JSON. In practice, this solves the “which detector should I use, and how do I trust the result?” workflow across tabular, time series, graph, text, and image inputs.

## 2. Agent Framework & Architecture

The repository does **not** use LangGraph, LangChain, AutoGen, CrewAI, or LlamaIndex in its runtime code. The implemented framework is a **custom orchestration engine** (`ADEngine`) plus an **MCP tool server** via `mcp.server.fastmcp` (`pyod/mcp_server.py:26-47`, `pyod/mcp_server.py:274-279`).

Architecture is layered:  
- `ADEngine` is the orchestrator/state machine for investigation (`pyod/utils/ad_engine.py:833-1571`).  
- `KnowledgeBase` loads structured JSON artifacts (`algorithms.json`, `routing_rules.json`, `benchmarks.json`, `papers.json`) used for planning decisions (`pyod/utils/knowledge/__init__.py:27-63`).  
- MCP exposes ADEngine functions as callable tools to external LLM agents (`pyod/mcp_server.py:247-279`).

The “intelligence” mostly lives in deterministic routing rules and benchmark-backed metadata, not in a central planner LLM. There is a deprecated LLM component (`AutoModelSelector`) that calls OpenAI chat completions (`pyod/utils/auto_model_selector.py:134-162`), but current comments direct users to ADEngine instead (`pyod/utils/auto_model_selector.py:8-13`).

## 3. Orchestration Pattern

Closest match: **sequential workflow automation with iterative loop** (custom state machine), not a multi-LLM-agent graph.

Control flow is explicit phase progression (`start -> plan -> run -> analyze`, then optional `iterate`), enforced by `state.phase` checks (`pyod/utils/ad_engine.py:921-930`, `pyod/utils/ad_engine.py:1567-1571`).

Example 1, sequential one-shot pipeline:
```1543:1571:pyod/utils/ad_engine.py
def investigate(self, X, data_type=None, priority='balanced'):
    """One-shot investigation: start → plan → run → analyze."""
    state = self.start(X, data_type=data_type)
    state = self.plan(state, priority=priority)
    state = self.run(state)
    state = self.analyze(state)
    return state
```

Example 2, multi-detector run plus consensus:
```951:1009:pyod/utils/ad_engine.py
for plan in state.plans:
    try:
        raw = self.run_detection(state.data, plan)
        entry = dict(raw)
        entry['detector_name'] = plan['detector_name']
        entry['status'] = 'success'
        results.append(entry)
...
rank_scores = np.array([
    rankdata(r['scores_train']) / n_samples
    for r in successful
])
consensus_scores = np.mean(rank_scores, axis=0)
consensus_labels = (vote_count > len(successful) / 2).astype(int)
```

## 4. Tools & External Integrations

- **MCP server / tool calling**: exposes `profile_data`, `plan_detection`, `build_detector`, `list_detectors`, `explain_detector`, `compare_detectors`, `get_benchmarks` for external agents (`pyod/mcp_server.py:66-213`, `pyod/mcp_server.py:247-279`).
- **OpenAI API**:
  - Embeddings integration via `OpenAIEncoder` (`openai` package, `OpenAI().embeddings.create`) (`pyod/utils/encoders/openai_encoder.py:10-13`, `pyod/utils/encoders/openai_encoder.py:73-91`).
  - Deprecated GPT-based model selection via chat completions (`pyod/utils/auto_model_selector.py:149-162`).
- **Graph stack (PyTorch Geometric)**: graph data typing and graph detectors rely on PyG when available (`pyod/utils/ad_engine.py:96-101`).
- **Local file/data loading** in MCP path: CSV/NPY/NPZ/JSON/MAT ingestion for tool calls (`pyod/mcp_server.py:216-245`).
- **Packaged knowledge/RAG-like retrieval**: JSON knowledge artifacts are loaded and queried by rule engine (`pyod/utils/knowledge/__init__.py:36-57`); no vector DB or external retriever is wired.
- **No browser automation, shell-execution tools, web search API, or external DB/vector-store integration** in the agent runtime code.

## 5. Notable Code Walkthrough

- `pyod/utils/ad_engine.py:125-231, 833-1571`  
  Core orchestrator: profiles modality, matches routing rules, executes top detectors, computes consensus, scores quality, and handles iterative feedback actions.

- `pyod/utils/knowledge/__init__.py:14-85`  
  Knowledge access layer: lazy-loads algorithms/benchmarks/rules/papers JSON and serves planner/query methods used by ADEngine.

- `pyod/utils/knowledge/routing_rules.json:1-178`  
  Encodes planning policy as declarative conditions and ranked recommendations by modality and constraints (e.g., tabular, time-series, graph, text/image presets).

- `pyod/mcp_server.py:66-107, 247-279`  
  Converts ADEngine operations into MCP tools, making PyOD usable by external LLM agents without embedding framework-specific code.

- `pyod/utils/auto_model_selector.py:97-162, 248-359`  
  Legacy LLM-driven selector (OpenAI chat calls + JSON parsing/retries); marked deprecated in favor of deterministic ADEngine.

## 6. Use-Case Mapping

The assigned label `RAG + Agents` is **partially accurate but overstated**. The repo does have agent-facing orchestration and a retrieval-like knowledge layer (structured JSON lookup/rules), plus MCP exposure for LLM assistants. However, it does **not** implement a classical RAG stack (no retrieval index/vector store/chunking pipeline) and does not run multiple coordinated LLM personas.

A better primary category is **Workflow Automation**: the central value is automated anomaly-detection workflow orchestration with planning, execution, consensus, and iteration (`pyod/utils/ad_engine.py:833-1571`), optionally controlled by an external agent through MCP.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong typed workflow state with explicit phases and next-action guidance (`pyod/utils/investigation.py:21-65`).
  - Deterministic, inspectable planning from benchmark-backed routing rules (`pyod/utils/knowledge/routing_rules.json:4-176`).
  - Built-in multi-detector consensus and quality assessment, beyond single-model inference (`pyod/utils/ad_engine.py:970-1176`).
  - Clean MCP interface that makes the engine reusable by many LLM clients (`pyod/mcp_server.py:247-279`).
  - Broad modality support behind one API path (tabular/time-series/graph/text/image).

- **Limitations:**
  - No true multi-agent LLM coordination at runtime; orchestration is algorithmic, not MAS in the strict LLM-agent sense.
  - Planning logic is static-rule based; little adaptive learning from outcomes beyond heuristic iteration.
  - Knowledge layer is local JSON, not scalable retrieval infrastructure (no vector store, ranking model, or provenance tracing).
  - Deprecated LLM selector exists alongside new engine, which can blur architecture expectations.
  - External tool surface is mostly PyOD-internal; limited integrations with broader enterprise data systems.

- **Research relevance:**
  - Good evidence for **agent-oriented workflow design** in scientific ML tooling without heavy framework dependency.
  - Useful case for comparing **rule-based planners vs LLM planners** in anomaly detection operations.
  - Demonstrates MCP as a practical bridge from domain engines to general-purpose LLM agents.
  - Supports study of consensus/quality metrics as guardrails in semi-autonomous analytical pipelines.

## 8. Machine-readable classification

MAS_RELATED: yes  
USES_MAS: no  
FINAL_USE_CASE: Workflow Automation
