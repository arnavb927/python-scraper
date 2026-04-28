---
repo_name: katanaml/sparrow
url: "https://github.com/katanaml/sparrow"
stars: 5153
forks: 511
contributors_count: 4
last_commit_date: "2026-04-20T18:53:31+00:00"
primary_use_case: RAG + Agents
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T13:17:18.441364+00:00"
model: auto
duration_s: 85.0
clone_size_kb: 36279
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`katanaml/sparrow` is a document/data processing platform that combines vision-capable LLM inference pipelines with API-exposed “agents” for specific workflows. In practice, users run FastAPI services (`sparrow-ml/llm/api.py` and `sparrow-ml/agents/api.py`) and submit either files (PDF/images) or structured input to endpoints like `/api/v1/sparrow-llm/inference` or `/api/v1/sparrow-agents/execute/*`. The system then executes a fixed pipeline (query preparation, backend inference, optional validation/post-processing) or a domain flow (medical prescription parsing, trading decision generation). Outputs are structured JSON results, optionally via async Celery task polling. The repo is more of a production workflow stack with pluggable LLM backends than a conversational multi-agent planning framework.

## 2. Agent Framework & Architecture

The code does **not** use LangGraph, LangChain, CrewAI, AutoGen, or LlamaIndex (no imports found). The “agent” layer is a **custom framework** built around:
- Prefect tasks/flows (`@task`, `@flow`) for in-agent step orchestration (`sparrow-ml/agents/medical_prescriptions/agent.py:34-240`, `sparrow-ml/agents/trading/agent.py:8-153`)
- a simple in-memory `AgentManager` for registration/dispatch (`sparrow-ml/agents/base.py:20-37`)
- FastAPI + Celery for sync/async execution (`sparrow-ml/agents/api.py:108-383`, `sparrow-ml/agents/tasks.py:24-136`)

Architecturally, there are two domain agents (`medical_prescriptions`, `trading`) registered centrally, but they are invoked one-at-a-time by name. Most “intelligence” is in prompt/query construction and deterministic pipeline logic inside `sparrow-parse` (e.g., schema-grounded prompt generation and output validation in `sparrow-ml/llm/pipelines/sparrow_parse/sparrow_parse.py:223-239` and `:494-519`), plus model backend adapters in `sparrow-data/parse/sparrow_parse/vlmb/*`.

## 3. Orchestration Pattern

Closest match: **hierarchical dispatcher + sequential workflow**, not a cooperative multi-agent system.

Control flow is manager-dispatch to a selected agent, then that agent runs a linear Prefect flow:

```5:37:sparrow-ml/agents/base.py
class AgentManager:
    def __init__(self):
        self.agents = {}

    def register_agent(self, agent: Agent):
        self.agents[agent.name] = agent

    async def execute_agent(self, agent_name: str, input_data: Dict) -> Dict:
        if agent_name not in self.agents:
            raise ValueError(f"Agent '{agent_name}' not found")
        return await self.agents[agent_name].execute(input_data)
```

```228:240:sparrow-ml/agents/medical_prescriptions/agent.py
@flow(name="medical_prescriptions_flow")
async def execute(self, input_data: Dict) -> Dict:
    doc_structure = await detect_doc_structure(input_data, self.sparrow_client)
    pages = await split_document(input_data, doc_structure)
    results = await extract_data(input_data, pages, self.sparrow_client)
```

Celery only changes execution mode (async queue), not orchestration semantics (`sparrow-ml/agents/tasks.py:24-56`).

## 4. Tools & External Integrations

- **FastAPI service layer**: agent and LLM APIs wired in `sparrow-ml/agents/api.py:29-50` and `sparrow-ml/llm/api.py:51-56`.
- **Prefect orchestration**: task/flow decorators across agents and clients (`sparrow-ml/agents/trading/agent.py:2-125`, `sparrow-ml/agents/medical_prescriptions/sparrow_client.py:32-87`).
- **Celery + Redis queues**: async job execution and status polling (`sparrow-ml/agents/celery_config.py:8-37`, `sparrow-ml/agents/api.py:153-359`).
- **HTTP integration to Sparrow LLM API**: medical agent calls `/api/v1/sparrow-llm/inference` via `aiohttp` (`sparrow-ml/agents/medical_prescriptions/sparrow_client.py:53-75`, `:108-134`).
- **LLM/VLM backends**: backend factory supports Hugging Face Spaces, Ollama, MLX, vLLM (`sparrow-data/parse/sparrow_parse/vlmb/inference_factory.py:5-23`).
- **Model providers/libraries**: `ollama` chat (`.../ollama_inference.py:115-169`), `vllm` local runtime (`.../vllm_inference.py:61-67`, `:167-210`), Gradio HF Spaces client (`.../huggingface_inference.py:34-50`).
- **Database integration (optional)**: Oracle DB pool for key validation and usage logging (`sparrow-ml/llm/db_pool.py:45-79`, `:230-273`).
- **Finance data integration**: `yfinance` in the `stocks` instructor pipeline (`sparrow-ml/llm/pipelines/instructor/stocks.py:70-73`).
- **Document/image tooling**: `pypdf`, `pdf2image` for splitting/processing PDFs (`sparrow-ml/agents/medical_prescriptions/agent.py:6-8`, `:80-103`).

No MCP servers, browser automation, shell tools, or vector stores were found in core runtime code.

## 5. Notable Code Walkthrough

- `sparrow-ml/agents/base.py:5-37` — Defines the minimal agent abstraction and `AgentManager`; this is the central dispatch layer that makes the system “multi-agent” in naming, but only as a registry/invoker.
- `sparrow-ml/agents/medical_prescriptions/agent.py:34-246` — Most complete domain workflow: validates multi-page PDF, converts pages to images, routes page types, and calls extraction endpoints per page type.
- `sparrow-ml/agents/tasks.py:15-136` — Bridges API and workers; builds manager, executes selected agent inside Celery tasks, and handles async lifecycle/progress metadata.
- `sparrow-ml/llm/pipelines/sparrow_parse/sparrow_parse.py:77-130` — Core extraction pipeline entrypoint; constructs query strategy, executes backend inference, and post-processes/validates outputs.
- `sparrow-data/parse/sparrow_parse/vlmb/inference_factory.py:5-23` — Backend polymorphism point for swapping inference engines (HF/Ollama/MLX/vLLM), critical for deployment flexibility.

## 6. Use-Case Mapping

The assigned label `RAG + Agents` is only partially accurate. The code clearly implements **agents as workflow wrappers**, but there is no classical RAG stack (no retriever, vector DB, embedding index, document chunk retrieval loop). Instead, it performs structured extraction/instruction execution directly over uploaded documents/images and routes processing through predefined domain flows (`medical_prescriptions`, `trading`) and deterministic pipeline steps (`sparrow-parse`).  
A better category is **Workflow Automation**: the repository automates multi-step business pipelines around LLM/VLM inference rather than coordinating multiple reasoning agents or retrieval-grounded agent teams.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear production wiring: FastAPI + Celery + Prefect integration is practical and deployable (`sparrow-ml/agents/api.py`, `tasks.py`).
  - Strong backend modularity for model providers via factory pattern (`inference_factory.py:5-23`).
  - Structured output focus with schema prompts and validation hooks (`sparrow_parse.py:223-240`, `:494-519`).
  - Domain-specific workflow decomposition (document-type routing, per-page processing) is explicit and auditable (`medical_prescriptions/agent.py:188-215`).

- **Limitations:**
  - No runtime coordination among multiple agents; only one selected agent executes per request (`base.py:32-37`, `agents/api.py:138-141`).
  - “Trading” path is mostly placeholder/mock data for market/broker integration (`trading/market_client.py:19-40`).
  - Limited adaptive planning/decision-making; flows are hardcoded sequential procedures.
  - No retrieval/indexing layer despite “RAG” framing; extraction is direct prompt-over-input.
  - Error handling often broad and generic, reducing observability of root causes in some paths.

- **Research relevance:**
  - Useful example of **agent-as-workflow-service** architecture (registry + domain flows) rather than emergent multi-agent coordination.
  - Illustrates integration of orchestration frameworks (Prefect/Celery) with LLM inference backends in applied systems.
  - Demonstrates practical structured-extraction prompt engineering and post-hoc schema validation in document AI pipelines.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
