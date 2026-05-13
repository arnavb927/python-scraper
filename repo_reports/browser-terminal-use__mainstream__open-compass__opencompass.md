---
repo_name: open-compass/opencompass
url: "https://github.com/open-compass/opencompass"
stars: 6921
forks: 769
contributors_count: 165
last_commit_date: "2026-04-20T12:05:41+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T08:04:39.493202+00:00"
model: auto
duration_s: 92.5
clone_size_kb: 15284
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`opencompass/opencompass` is primarily an LLM evaluation platform that runs configurable benchmark pipelines across many models and datasets, then computes metrics and summaries. Users typically run an evaluation config (via `run.py` / CLI), which builds tasks, executes inference over dataset splits, and writes prediction/evaluation artifacts to `work_dir` outputs (`run.py:1-4`, `opencompass/tasks/openicl_infer.py:20-159`). Beyond plain generation/perplexity evaluation, it also supports agent-style inference modes where a model can use tools (notably Python/IPython interpreters) and logs step traces (`opencompass/openicl/icl_inferencer/icl_agent_inferencer.py:76-147`). So the core product is benchmark orchestration, with agent execution as one evaluation modality rather than the whole architecture.

## 2. Agent Framework & Architecture

Framework usage in code is **custom OpenCompass orchestration + Lagent-based agents**, with an optional LangChain wrapper:
- Lagent-backed agent wrappers (`opencompass/models/lagent.py:9-35`, `opencompass/lagent/agents/react.py:75-131`).
- Optional LangChain adapter exists (`opencompass/models/langchain.py:8-23`), but no LangGraph/AutoGen/CrewAI imports were found in runtime code paths.
- Task orchestration itself is OpenCompass/MMEngine registries and task runners (`opencompass/tasks/openicl_infer.py:20-159`).

The high-level architecture is: config-driven task runner builds model + dataset + retriever + inferencer, then executes inference batch-wise (`opencompass/tasks/openicl_infer.py:119-158`). If `AgentInferencer` is selected, it delegates each user turn to a single Lagent agent and records intermediate tool-use steps (`opencompass/openicl/icl_inferencer/icl_agent_inferencer.py:85-119`). Intelligence lives in prompt/protocol templates and ReAct loop logic: protocol formatting/parsing, tool selection, and iterative action execution are implemented in `ReActProtocol`/`ReAct` (`opencompass/lagent/agents/react.py:19-73`, `95-131`).

Important nuance: this repo supports **agentic execution**, but usually as a **single tool-using agent per sample**, embedded inside a larger evaluation workflow.

## 3. Orchestration Pattern

Closest match: **hierarchical workflow automation (manager-worker), with single-agent inner loops**.

- At workflow level, `OpenICLInferTask` is a manager that iterates models/datasets, builds components, and dispatches inferencer execution (`opencompass/tasks/openicl_infer.py:67-104`, `123-158`).
- Inside `AgentInferencer`, each prompt is handled by one ReAct-style worker agent that iterates thought/action/observation until finish (`opencompass/openicl/icl_inferencer/icl_agent_inferencer.py:90-100`; `opencompass/lagent/agents/react.py:103-124`).

Example control flow:
```95:124:opencompass/lagent/agents/react.py
for turn in range(self.max_turn):
    prompt = self._protocol.format(...)
    response = self._llm.generate_from_template(prompt, 512)
    thought, action, action_input = self._protocol.parse(response, self._action_executor)
    action_return: ActionReturn = self._action_executor(action, action_input)
    ...
    if action_return.type == self._action_executor.finish_action.name:
        agent_return.response = action_return.result['text']
        break
```

```123:149:opencompass/tasks/openicl_infer.py
retriever = ICL_RETRIEVERS.build(retriever_cfg)
inferencer_cfg = self.infer_cfg['inferencer']
inferencer_cfg['model'] = self.model
inferencer = ICL_INFERENCERS.build(inferencer_cfg)
...
inferencer.inference(retriever, prompt_template=prompt_template, ...)
```

## 4. Tools & External Integrations

- **Python code execution tool**: sandboxed multiprocessing Python executor for agent actions (`opencompass/lagent/actions/python_interpreter.py:51-157`).
- **Jupyter/IPython execution tool**: kernel-backed interpreter with image capture/output parsing (`opencompass/lagent/actions/ipython_interpreter.py:39-253`).
- **OpenAI-compatible API calls**: evaluator uses raw HTTP `requests.post` against OpenAI-style chat/function-calling endpoint (`opencompass/openicl/icl_evaluator/icl_agent_evaluator.py:255-332`).
- **Lagent framework integration**: action executor + ReAct protocol/agent wiring (`opencompass/models/lagent.py:21-35`, `opencompass/lagent/agents/react.py:4-8`).
- **Optional LangChain integration**: `initialize_agent`/`load_tools` wrapper (`opencompass/models/langchain.py:15-23`).
- **VLMEvalKit (optional)**: visual scoring backend for CIBench evaluator (`opencompass/datasets/cibench.py:240-248`, `367-377`).
- **Notebook/CLI tooling via subprocess**: `jupytext` + `jupyter nbconvert` in evaluator artifact generation (`opencompass/datasets/cibench.py:440-445`).

No MCP server integration or browser automation stack (e.g., Playwright) is wired in the inspected agent runtime paths.

## 5. Notable Code Walkthrough

- `opencompass/tasks/openicl_infer.py:20-159` - Core orchestration task: builds model/retriever/inferencer from config and runs inference over model-dataset matrix; this is the primary runtime backbone.
- `opencompass/openicl/icl_inferencer/icl_agent_inferencer.py:76-147` - Agent-mode inferencer that bridges chat-format benchmark samples into agent `.chat()` calls and persists prediction + step traces.
- `opencompass/models/lagent.py:9-101` - Adapter that instantiates Lagent agents/tools from registry configs and normalizes action traces into OpenCompass output schema.
- `opencompass/lagent/agents/react.py:95-131` - ReAct loop implementation: prompt formatting, LLM generation, parsed tool call, execution, and termination condition.
- `opencompass/lagent/actions/ipython_interpreter.py:125-253` - High-impact tool implementation enabling persistent kernel execution, timeout handling, and multimodal (text/image) outputs for code-interpreter benchmarks.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** looks mostly inaccurate for this repo’s primary behavior. The dominant pattern is **evaluation workflow automation**: config-defined benchmarking pipelines, parallel runners, infer/eval/summarize stages (`opencompass/tasks/openicl_infer.py:67-159`).  
Agentic parts mainly call Python/IPython tools for reasoning/code-execution tasks, not browser navigation or terminal operation automation (`opencompass/lagent/actions/python_interpreter.py:96-157`, `opencompass/lagent/actions/ipython_interpreter.py:232-253`).  
Better category: **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong modular registry architecture for swapping models, retrievers, inferencers, evaluators.
  - Practical agent-eval support with step-level traces, not just final answers.
  - Integrates code-interpreter style tools (Python and Jupyter kernel) for realistic tool-use benchmarking.
  - Supports many evaluation modes (ICL, ToT, subjective judge pipelines) under one orchestration framework.
  - Clear config-driven reproducibility for benchmark runs.

- **Limitations:**
  - Multi-agent coordination is limited; most “agent” execution is single-agent ReAct loops.
  - Optional framework wrappers (e.g., LangChain) are thin and not central to orchestration logic.
  - Tool safety/isolation is basic (exec-based interpreters), with limited security hardening visible in these modules.
  - Some evaluators depend on external APIs and heuristic parsing, which can add nondeterminism.
  - Browser/terminal autonomous interaction is not a first-class runtime capability.

- **Research relevance:**
  - Useful evidence for **agentic evaluation infrastructure** rather than novel MAS coordination algorithms.
  - Demonstrates how to operationalize tool-augmented LLM benchmarking at scale with reproducible configs.
  - Provides concrete ReAct + interpreter integration patterns for benchmark tasks.
  - Relevant to studies comparing single-agent tool use vs non-agent baselines across datasets.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
