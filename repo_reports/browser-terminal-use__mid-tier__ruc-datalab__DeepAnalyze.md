---
repo_name: ruc-datalab/DeepAnalyze
url: "https://github.com/ruc-datalab/DeepAnalyze"
stars: 4038
forks: 660
contributors_count: 14
last_commit_date: "2026-03-28T07:27:53+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 6
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T12:24:53.629689+00:00"
model: auto
duration_s: 107.9
clone_size_kb: 60256
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`DeepAnalyze` is an autonomous data-analysis assistant that runs a local LLM (typically via a vLLM OpenAI-compatible endpoint), asks it to produce structured reasoning plus Python code, executes that code in a workspace, and iterates until a final `<Answer>` is produced. In practice, users either call `DeepAnalyzeVLLM.generate(...)` directly (`deepanalyze.py`, `run.py`) or use the FastAPI server (`API/main.py` + `API/chat_api.py`) for chat/file workflows. The system is designed to analyze uploaded tabular files, generate plots/artifacts, and output report-style answers. The repo also vendors training/infrastructure stacks (`deepanalyze/ms-swift`, `deepanalyze/SkyRL`), but the core product path is the code-execution analysis loop.

## 2. Agent Framework & Architecture

The production inference path is **custom agent orchestration**, not LangGraph/LangChain/CrewAI/AutoGen. Core imports are `openai`, `fastapi`, `requests`, `subprocess`, etc. (`API/chat_api.py`, `API/utils.py`, `deepanalyze.py`), and there are no framework-level graph/crew abstractions in the main runtime.

Architecture-wise, this is a **single LLM agent with tool-execution feedback**. The model is prompted to emit tagged segments (`<Analyze>`, `<Code>`, `<Execute>`, `<Answer>`), code is extracted and executed, execution output is appended back as a new message (`role: "execute"`), and generation continues until `<Answer>` appears (`deepanalyze.py:68-147`, `API/chat_api.py:287-344`). Intelligence largely lives in prompt/template conventions and this iterative controller loop, not in multiple collaborating model roles.

The repo does contain a separate bundled `SkyRL/skyagent` framework with reusable agent runners (`deepanalyze/SkyRL/skyagent/skyagent/agents/...`), but this is not the main DeepAnalyze API/inference path.

## 3. Orchestration Pattern

Closest match: **sequential loop (ReAct/code-interpreter style), single-agent iterative control**.

Control flow is: prompt -> model output -> detect/execute code -> append execution result -> next model call -> stop at `<Answer>`. Example:

```88:140:deepanalyze.py
for round_idx in range(self.max_rounds):
    payload = {"model": self.model_name, "messages": messages, ...}
    response = requests.post(self.api_url, headers={...}, json=payload)
    ans = response_data["choices"][0]["message"]["content"]
    if "<Answer>" in ans:
        break
    code_match = re.search(r"<Code>(.*?)</Code>", ans, re.DOTALL)
    ...
    exe_output = self.execute_code(code_str)
    messages.append({"role": "assistant", "content": ans})
    messages.append({"role": "execute", "content": exe_output})
```

The API server uses the same loop in async/streaming form:

```287:342:API/chat_api.py
while not finished:
    response = await vllm_client_async.chat.completions.create(..., stream=True, ...)
    cur_res = ""
    async for chunk in response:
        ...
        if "</Answer>" in cur_res:
            finished = True
            break
    ...
    if has_code_segment and has_closed_code and not finished:
        vllm_messages.append({"role": "assistant", "content": cur_res})
        code_str = extract_code_from_segment(cur_res)
        exe_output = await execute_code_safe_async(code_str, workspace_dir)
        ...
        vllm_messages.append({"role": "execute", "content": exe_output})
```

## 4. Tools & External Integrations

- **LLM serving via OpenAI-compatible API (vLLM endpoint)**: wired through `openai.OpenAI(base_url=API_BASE)` and async client (`API/chat_api.py:36-39`, `API/config.py:12`).
- **Python code execution tool**: extracted `<Code>` blocks run in subprocess with timeout and isolated workspace (`API/utils.py:130-219`); direct `exec` variant exists in library mode (`deepanalyze.py:26-67`).
- **Filesystem/workspace management**: per-thread workspaces, file copying, artifact tracking, generated outputs (`API/chat_api.py:72-115`, `API/utils.py:26-30`, `API/utils.py:350-409`).
- **File upload/download service**: FastAPI file APIs + HTTP static server for generated artifacts (`API/main.py:74-83`, `API/utils.py:494-510`, URL building in `API/utils.py:33-40`).
- **Report generation pipeline**: parses tagged conversation history into markdown report and persists it (`API/utils.py:254-470`).
- **Bundled but separate**: `SkyRL/skyagent` includes web tools (e.g., Jina/web summarization in `deepanalyze/SkyRL/skyagent/skyagent/tools/web_browser.py:12-275`), but this is not integrated into the primary DeepAnalyze API loop.

## 5. Notable Code Walkthrough

- `deepanalyze.py:10-147` - Minimal core runtime class (`DeepAnalyzeVLLM`) implementing multi-round tagged generation and code execution feedback; this is the clearest expression of DeepAnalyze’s agent behavior.
- `API/chat_api.py:44-387` - Production OpenAI-compatible chat endpoint with thread workspaces, streaming generation, code execution interleaving, and stop-on-`</Answer>` orchestration.
- `API/utils.py:91-127` - Message shaping layer that injects `# Instruction` + `# Data` (workspace file inventory), which strongly steers the model’s autonomous analysis behavior.
- `API/utils.py:130-219` - Safe execution backend (sync/async subprocess with timeout/environment control), the key “tool-use” mechanism for this agent.
- `deepanalyze/SkyRL/skyagent/skyagent/agents/react/react_runner.py:20-66` - Separate packaged agent runner framework showing ReAct trajectory generation/evaluation; useful context, but distinct from the core deployed DeepAnalyze path.

## 6. Use-Case Mapping

For the shipped DeepAnalyze runtime, the assigned label **Browser / Terminal Use** looks mostly off. The main system is a **workflow-automation data-analysis agent**: it ingests files, iteratively writes/runs Python analysis code, tracks artifacts, and returns report outputs (`API/chat_api.py`, `API/utils.py`, `deepanalyze.py`). It does use local execution, but not browser automation or generalized terminal command planning; execution is narrowly Python-script-based. Better fit: **Workflow Automation** (with some overlap to “RAG + Agents” only in a loose file-context sense, not vector-RAG).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, compact autonomous loop from model reasoning to executable action to feedback (`deepanalyze.py`, `API/chat_api.py`).
  - Practical OpenAI-compatible API wrapper with file/thread lifecycle support (`API/main.py`, `API/chat_api.py`).
  - Built-in artifact/report pipeline useful for reproducible analytic sessions (`API/utils.py:350-470`).
  - Async streaming execution path enables responsive long-running analyses (`API/chat_api.py:126-279`).

- **Limitations:**
  - Core path is single-agent; no explicit planner/critic/debate or multi-agent coordination.
  - Safety/isolation is limited: library path uses raw `exec` (`deepanalyze.py:38`), and API path executes arbitrary Python in workspace.
  - Tag-based protocol is brittle (depends on correct `<Code>/<Answer>` formatting).
  - Little evidence of robust policy/guardrails around tool permissions beyond timeout/environment defaults.

- **Research relevance:**
  - Good example of a **single-agent code-interpreter architecture** for autonomous data science.
  - Useful case of **LLM-to-execution feedback loops** in practical API products.
  - Evidence that many “agentic” systems in production are prompt/protocol-driven controllers, not full multi-agent societies.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
