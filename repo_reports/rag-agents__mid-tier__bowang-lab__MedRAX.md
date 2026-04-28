---
repo_name: bowang-lab/MedRAX
url: "https://github.com/bowang-lab/MedRAX"
stars: 1130
forks: 199
contributors_count: 5
last_commit_date: "2025-10-31T00:31:34+00:00"
primary_use_case: RAG + Agents
user_tier: Mid-Tier
total_score: 6
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T12:57:01.202786+00:00"
model: auto
duration_s: 70.7
clone_size_kb: 158411
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`bowang-lab/MedRAX` is a medical imaging assistant that lets users upload chest X-rays (including DICOM) and ask clinical questions through a Gradio UI (`main.py`, `interface.py`). At runtime, it uses a general-purpose LLM (default GPT-4o via OpenAI-compatible API) to decide when to call specialized imaging tools (classification, segmentation, report generation, grounding, VQA, image generation). The user runs `python main.py` for interactive use, or `python quickstart.py` for benchmark-style evaluation on ChestAgentBench examples. The output is a conversational answer plus optional structured tool outputs and generated images (e.g., segmentation overlays, grounded boxes, synthetic X-rays).

## 2. Agent Framework & Architecture

The codebase **does use LangGraph + LangChain**, confirmed by imports and runtime wiring in `medrax/agent/agent.py` (`StateGraph` from `langgraph.graph`, `BaseTool`/messages from `langchain_core`) and model binding via `ChatOpenAI` in `main.py`. I do **not** see CrewAI or AutoGen runtime usage in source; orchestration is custom around LangGraph.

Architecture is a **single LLM agent with tool-calling**, not multiple collaborating agents. `main.py` instantiates one `Agent` object, binds a selected toolset, and passes it to Gradio. The “intelligence” is split between: (a) the system prompt (`medrax/docs/system_prompts.txt`), (b) the LLM’s function-calling decisions (`self.model = model.bind_tools(tools)`), and (c) tool implementations in `medrax/tools/*`.

The control loop is implemented as a two-node state machine: `process` (LLM inference) and `execute` (tool invocation), repeating until no tool calls remain (`medrax/agent/agent.py`).

## 3. Orchestration Pattern

Closest match: **graph (LangGraph-style state machine)** with iterative tool-execution loop.

Control flow is explicit in `medrax/agent/agent.py:91-100`:

```python
workflow = StateGraph(AgentState)
workflow.add_node("process", self.process_request)
workflow.add_node("execute", self.execute_tools)
workflow.add_conditional_edges(
    "process", self.has_tool_calls, {True: "execute", False: END}
)
workflow.add_edge("execute", "process")
```

Tool calls are extracted from the latest model message and synchronously invoked one-by-one in `medrax/agent/agent.py:143-166`:

```python
tool_calls = state["messages"][-1].tool_calls
for call in tool_calls:
    if call["name"] not in self.tools:
        result = "invalid tool, please retry"
    else:
        result = self.tools[call["name"]].invoke(call["args"])
    results.append(ToolMessage(..., content=str(result)))
return {"messages": results}
```

The UI streams this graph execution (`self.agent.workflow.stream(...)`) and renders both model text and tool outputs in `interface.py:135-177`.

## 4. Tools & External Integrations

- **OpenAI-compatible LLM backend** (`main.py:76-84`, `main.py:113-129`): `ChatOpenAI` drives planning/tool choice; supports custom `OPENAI_BASE_URL`.
- **LangGraph memory checkpointing** (`main.py:75`): `MemorySaver` keeps per-thread conversation state.
- **Gradio frontend** (`interface.py:200-279`): chat UI, file upload, streaming responses.
- **DICOM parsing** via `pydicom` (`medrax/tools/dicom.py:58-94`): converts DICOM to PNG + metadata.
- **CXR classification** via `torchxrayvision` DenseNet (`medrax/tools/classification.py:55-59`, `:114-123`).
- **CXR segmentation** via `xrv.baseline_models.chestx_det.PSPNet` (`medrax/tools/segmentation.py:88-91`, `:255-292`), outputs overlay + organ metrics.
- **Report generation** via Hugging Face vision-encoder-decoder models (`medrax/tools/report_generation.py:66-85`, `:181-203`).
- **Medical VQA** via CheXagent (`medrax/tools/xray_vqa.py:76-88`, `:102-126`).
- **Grounding/localization** via MAIRA-2 (`medrax/tools/grounding.py:85-95`, `:157-234`).
- **Optional synthetic image generation** via Stable Diffusion/RoentGen path (`medrax/tools/generation.py:65-67`, `:95-121`).
- **Local file/temp I/O and plotting** across tools (`temp` paths, Matplotlib saves in segmentation/grounding tools).
- **Benchmark path only**: `quickstart.py` uses OpenAI chat completions + Hugging Face `datasets`, but this is evaluation script, not the main agent runtime.

No MCP, browser automation, shell tools, or vector database/RAG retriever stack found in runtime agent code.

## 5. Notable Code Walkthrough

- `medrax/agent/agent.py:48-194` - Core orchestrator. Defines the LangGraph state, loops model->tools->model, and logs tool calls to JSON for traceability.
- `main.py:20-87` - Assembly layer. Loads prompts, initializes selected tools, configures `ChatOpenAI`, and returns an `Agent` + tool registry.
- `interface.py:88-177` - Runtime interaction loop. Converts uploads/messages into multimodal user messages, streams graph events, and renders tool outputs in chat.
- `medrax/tools/segmentation.py:64-310` - Representative heavy tool. Runs segmentation model inference, computes organ metrics, and saves visualization artifacts for downstream agent explanation.
- `medrax/tools/xray_vqa.py:27-187` - Specialized multimodal reasoning tool using CheXagent; demonstrates how external foundation models are wrapped as LangChain tools.

## 6. Use-Case Mapping

Despite the upstream label “RAG + Agents,” the code does **not** implement a retrieval pipeline (no embedding index/vector DB/retriever-to-generator loop in main runtime). Instead, it is a **tool-orchestrated medical workflow assistant**: one LLM coordinates multiple domain models over uploaded images and synthesized intermediate artifacts. So the better category is **Workflow Automation** (LLM-driven orchestration of specialized tools), with multimodal reasoning but no concrete retrieval component.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, auditable orchestration loop using LangGraph (`process`/`execute`) rather than opaque chaining.
  - Strong modular tool wrappers for heterogeneous medical models (classification, segmentation, grounding, VQA, report generation).
  - Practical clinical file handling (DICOM conversion + metadata) integrated into agent workflow.
  - Streaming UI integration gives transparent intermediate tool outputs instead of only final answers.
  - Tool-call logging to disk supports debugging and post-hoc analysis.

- **Limitations:**
  - Not a true multi-agent system; only one planner/executor LLM agent.
  - “Parallel tool calls” is suggested in prompt text, but execution loop is sequential in code.
  - No explicit safety/verification layer for medical claims beyond prompt guidance.
  - Fragile parsing in UI (`eval(message.content)` in `interface.py`) and minimal structured output contracts.
  - No native RAG subsystem despite repository/use-case framing around agentic reasoning.

- **Research relevance:**
  - Good example of **single-agent tool orchestration** in high-stakes multimodal domain workflows.
  - Useful evidence for evaluating LLM-as-controller over specialized medical foundation models.
  - Demonstrates practical integration tradeoffs (latency, model loading, artifact handoff via files) in real-world agent systems.
  - Suitable baseline when comparing single-agent tool use vs true multi-agent collaboration in medical AI.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
