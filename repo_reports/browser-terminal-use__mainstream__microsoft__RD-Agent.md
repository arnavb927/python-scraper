---
repo_name: microsoft/RD-Agent
url: "https://github.com/microsoft/RD-Agent"
stars: 12627
forks: 1512
contributors_count: 37
last_commit_date: "2026-04-13T11:56:47+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T11:02:53.504291+00:00"
model: auto
duration_s: 86.4
clone_size_kb: 19328
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`microsoft/RD-Agent` is an LLM-driven R&D automation system that repeatedly proposes, implements, runs, and evaluates experiments for domains like Kaggle/data science, quant, RL, and fine-tuning. In practice, users run scenario loops (for example Kaggle or data-science loops) that instantiate an `RDLoop`-style workflow and keep iterating experiments until limits/timeouts are reached (`rdagent/components/workflow/rd_loop.py`, `rdagent/scenarios/data_science/loop.py`, `rdagent/app/kaggle/loop.py`). Each iteration generates a new hypothesis/task, writes or edits code in workspaces, executes it, then summarizes feedback into a trace DAG used for future decisions. The output is not just chat text: it is runnable experiment code, execution results, and a persistent experiment history/knowledge state.

## 2. Agent Framework & Architecture

The repo is **primarily custom agent infrastructure**, not LangGraph/CrewAI/AutoGen/LangChain-based orchestration. Core control flow is implemented in custom abstractions (`LoopBase`, `RDLoop`, `EvoAgent`, `RAGEvoAgent`) with explicit step scheduling and trace management (`rdagent/utils/workflow/loop.py`, `rdagent/components/workflow/rd_loop.py`, `rdagent/core/evolving_agent.py`).  

For LLM access, it uses a custom backend abstraction (`APIBackend`) over LiteLLM/OpenAI-compatible providers (`rdagent/oai/backend/base.py`, `rdagent/oai/llm_utils.py`). It also includes a **Pydantic-AI integration layer** for MCP tool-enabled agents (`rdagent/components/agent/base.py`, `rdagent/oai/backend/pydantic_ai.py`). LangChain appears only in document-loading utilities (PDF parsing), not as the agent orchestrator (`rdagent/components/document_reader/document_reader.py`).

Architecturally, intelligence is split into role-like modules: hypothesis generation, hypothesis→experiment conversion, coder/developer, runner, and summarizer/feedback. `RDLoop` wires these roles dynamically via config (`import_class(...)`) and executes them as a repeating pipeline (`direct_exp_gen -> coding -> running -> feedback -> record`) while maintaining a DAG trace of experiment lineage (`rdagent/components/workflow/rd_loop.py`, `rdagent/core/proposal.py`). Scenario-specific loops (Data Science, RL, Finetune, Kaggle) override or specialize these roles, making this a multi-role, manager-worker style system with optional RAG and knowledge graph augmentation.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) with asynchronous pipelined loops**.

- The manager is the loop engine (`LoopBase`) that schedules step execution, handles retries/skip/withdraw semantics, and runs multiple loops concurrently with semaphores/queues (`rdagent/utils/workflow/loop.py:194-352`).
- Workers are role components (proposal generator, coders, runners, summarizers) invoked in ordered stages by `RDLoop` and scenario subclasses (`rdagent/components/workflow/rd_loop.py:199-242`, `rdagent/scenarios/data_science/loop.py:154-210`).

Excerpt showing step-driven manager flow:

```102:124:rdagent/components/workflow/rd_loop.py
async def direct_exp_gen(self, prev_out: dict[str, Any]):
    ...
def coding(self, prev_out: dict[str, Any]):
    exp = self.coder.develop(prev_out["direct_exp_gen"]["exp_gen"])
def running(self, prev_out: dict[str, Any]):
    exp = self.runner.develop(prev_out["coding"])
def feedback(self, prev_out: dict[str, Any]):
    feedback = self.summarizer.generate_feedback(prev_out["running"], self.trace)
```

Excerpt showing async orchestration and parallel workers:

```336:390:rdagent/utils/workflow/loop.py
async def execute_loop(self) -> None:
    li = await self.queue.get()
    while self.step_idx[li] < len(self.steps):
        await self._run_step(li, force_subproc=RD_AGENT_SETTINGS.is_force_subproc())

async def run(...):
    tasks = [
        asyncio.create_task(self.kickoff_loop()),
        *[asyncio.create_task(self.execute_loop()) for _ in range(RD_AGENT_SETTINGS.get_max_parallel())],
    ]
```

## 4. Tools & External Integrations

- **LLM providers via LiteLLM/OpenAI-compatible APIs**: central generation/embedding backend with retries, caching, JSON/code parsing (`rdagent/oai/backend/base.py`, `rdagent/oai/llm_utils.py`, `rdagent/oai/backend/pydantic_ai.py`).
- **MCP tool servers (via Pydantic-AI)**: `PAIAgent` supports MCP toolsets; specialized agents for Context7 and RAG wire MCP HTTP servers (`rdagent/components/agent/base.py`, `rdagent/components/agent/context7/__init__.py`, `rdagent/components/agent/rag/__init__.py`).
- **Knowledge/RAG stores**: custom vector store (`PDVectorBase`) and graph-based knowledge base (`UndirectedGraph`, CoSTEER KB) using embeddings for retrieval (`rdagent/components/knowledge_management/vector_base.py`, `rdagent/components/knowledge_management/graph.py`, `rdagent/components/coder/CoSTEER/knowledge_management.py`).
- **Terminal/shell execution**: extensive `subprocess` usage for coding/eval workflows, archiving, Kaggle CLI submission/download (`rdagent/scenarios/data_science/loop.py`, `rdagent/app/kaggle/loop.py`, `rdagent/app/CI/run.py`).
- **Browser automation**: Selenium + ChromeDriverManager to crawl Kaggle competition pages (`rdagent/scenarios/kaggle/kaggle_crawler.py:14-107`).
- **Kaggle API**: leaderboard/notebook retrieval and competition integration (`rdagent/scenarios/kaggle/kaggle_crawler.py:208-273`).
- **Containerized execution**: MLEBench Docker environment integration for dataset prep and commands (`rdagent/scenarios/kaggle/kaggle_crawler.py:118-166`).

## 5. Notable Code Walkthrough

- `rdagent/components/workflow/rd_loop.py:31-242`  
  Defines the canonical multi-role agent loop (`hypothesis_gen`, `hypothesis2experiment`, `coder`, `runner`, `summarizer`) and the core step methods used across scenarios.

- `rdagent/utils/workflow/loop.py:85-405`  
  Implements the orchestration runtime: automatic step discovery via metaclass, async queue/semaphore scheduling, subprocess execution mode, checkpoint dump/load, and termination controls.

- `rdagent/scenarios/data_science/proposal/exp_gen/proposal.py:492-1500`  
  A representative “intelligence-heavy” module: problem identification, hypothesis generation/critique/rewrite, optional RAG retrieval, hypothesis selection, and task generation with structured outputs.

- `rdagent/components/coder/data_science/model/__init__.py:30-131`  
  Shows coder-agent behavior: builds prompts from workspace/context + retrieved knowledge, calls `APIBackend`, validates/edit constraints, and emits concrete code file edits.

- `rdagent/components/coder/CoSTEER/knowledge_management.py:354-455`  
  Shows RAG strategy over evolving traces: generating/updating knowledge from outcomes and querying former failures/similar successes to guide later coding iterations.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially accurate. The project does include browser automation (Selenium Kaggle crawl) and heavy terminal/CLI execution (`subprocess`, Kaggle CLI, CI commands), but those are support mechanisms inside a broader autonomous experiment pipeline.  

After reading core runtime/orchestration code, the dominant use case is **Workflow Automation**: orchestrating multi-step LLM-driven R&D workflows (propose → code → run → evaluate → iterate) across domains. So the better final category is `Workflow Automation`.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear modular role decomposition (proposal/coder/runner/summarizer) with reusable loop runtime.
  - Robust orchestration features: async parallel loops, semaphores, resumable sessions, skip/withdraw error policies.
  - Strong traceability: DAG-based experiment lineage with feedback-linked records.
  - Practical integration breadth (LLMs, MCP, Kaggle, Selenium, Docker, vector/graph knowledge).
  - Scenario-specialized loops built on a common core, enabling comparative experimentation.

- **Limitations:**
  - Framework heterogeneity can be confusing (custom core + Pydantic-AI + LiteLLM + optional LangChain utilities).
  - “Agent” boundaries are mostly role classes; not all roles are independently autonomous conversational agents.
  - Large, complex modules (especially DS proposal logic) may be hard to reason about/verify formally.
  - Heavy reliance on prompt engineering and runtime heuristics may reduce reproducibility across model/backends.
  - Limited explicit formal guarantees for convergence/optimality of multi-agent coordination.

- **Research relevance:**
  - Evidence for **hierarchical multi-agent workflow orchestration** in real-world ML/R&D automation.
  - Useful case study of combining **iterative coding agents with retrieval/knowledge feedback loops**.
  - Demonstrates practical engineering patterns for **long-horizon autonomous experimentation** (checkpointing, trace DAGs, failure handling).
  - Illustrates integration of external tools (browser/CLI/APIs) into agentic pipelines beyond pure chat.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
