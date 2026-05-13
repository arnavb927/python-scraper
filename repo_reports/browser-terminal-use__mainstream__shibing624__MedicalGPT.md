---
repo_name: shibing624/MedicalGPT
url: "https://github.com/shibing624/MedicalGPT"
stars: 5287
forks: 743
contributors_count: 15
last_commit_date: "2026-04-23T02:32:22+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mainstream
total_score: 7
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-05-05T08:13:09.586764+00:00"
model: auto
duration_s: 69.3
clone_size_kb: 29400
mas_related: yes
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`MedicalGPT` is primarily a medical-domain LLM training and serving project, not an autonomous agent platform. Users run training scripts (SFT/DPO/RLHF variants) to fine-tune base models on medical dialog/instruction data, then run demos (`gradio`, FastAPI OpenAI-compatible endpoint, CLI inference) for chat and QA. The repo also includes data-generation utilities (including role-play synthetic data) and a lightweight RAG demo (`chatpdf.py`) for document-grounded responses. In practice, the output is a fine-tuned medical assistant model plus runnable inference services.

## 2. Agent Framework & Architecture

From code inspection, this repo does **not** use LangGraph, LangChain, CrewAI, AutoGen, or LlamaIndex as its core runtime framework. The core stack is custom Python + Hugging Face `transformers`/`trl`, with optional OpenAI-compatible APIs for data generation and serving (`role_play_data/llm_client.py`, `demo/openai_api.py`, `training/*.py`).

What it does have is **tool-calling format support** during training/inference formatting, implemented in a custom utility layer (`training/tool_utils.py`). This layer defines templates/parsers for function-call syntax across model families (default/GLM4/Llama3/Mistral/Qwen), but this is prompt/format handling, not a multi-agent graph.

High-level architecture is pipeline-oriented:
1) dataset preparation + formatting (`training/supervised_finetuning.py`, `training/dpo_training.py`),  
2) model optimization (LoRA/QLoRA/SFT/DPO/etc.),  
3) serving/inference via UI/API demos (`demo/gradio_demo.py`, `demo/openai_api.py`, `demo/chatpdf.py`).

## 3. Orchestration Pattern

Closest pattern: **sequential workflow automation** (data -> preprocess -> train -> serve), with **single-agent ReAct-style tool-call emulation** in one API endpoint. It is not hierarchical multi-agent, swarm, or graph-state orchestration.

Control flow for “tool use” is linear prompt transformation and response parsing inside one assistant loop:

```205:244:demo/openai_api.py
if tools:
    tools_text = []
    ...
    instruction = (REACT_INSTRUCTION.format(
        tools_text=tools_text,
        tools_name_text=tools_name_text,
    ).lstrip('\n').rstrip())
...
if instruction:
    query = f'{instruction}\n\nQuestion: {query}'
```

Then the model output is parsed for `Action`/`Action Input` and converted to one tool call payload:

```322:353:demo/openai_api.py
i = response.find('\nAction:')
j = response.find('\nAction Input:')
...
func_name = response[i + len('\nAction:'):j].strip()
func_args = response[j + len('\nAction Input:'):k].strip()
...
message=ChatMessage(
    role='assistant',
    content=response,
    tool_calls={'name': func_name, 'arguments': func_args},
)
```

## 4. Tools & External Integrations

- **OpenAI-compatible LLM APIs** (OpenAI, MiniMax, Doubao via OpenAI SDK abstraction) for synthetic data generation and provider switching: `role_play_data/llm_client.py:21-107`.
- **OpenAI-style chat completion server** (local model exposed as `/v1/chat/completions`): `demo/openai_api.py:152-610`.
- **Tool/function-calling formatting/parsing layer** for multiple prompt dialects (Default/GLM4/Llama3/Mistral/Qwen): `training/tool_utils.py:22-329`.
- **RAG components** using `similarities` (`BertSimilarity`, `BM25Similarity`, `EnsembleSimilarity`) and local document ingestion (PDF/TXT/Markdown/DOCX): `demo/chatpdf.py:19-203`, `demo/chatpdf.py:253-334`.
- **Training ecosystem integrations**: Hugging Face `transformers`, `datasets`, `peft`, `trl` DPO trainer, DeepSpeed/FSDP compatibility hooks in training scripts: `training/supervised_finetuning.py`, `training/dpo_training.py`.
- **Browser automation / terminal tools / MCP servers**: not present as runtime agent tools in this repo.

## 5. Notable Code Walkthrough

- `training/tool_utils.py:17-329`  
  Defines the repo’s core function-call abstraction (`FunctionCall`, formatters, extractors) and model-specific tool prompt grammars. This is central to “agent-style” tool-call data formatting during fine-tuning.

- `training/supervised_finetuning.py:442-577`  
  Converts ShareGPT-style conversation data (including `function_call` and `observation` turns) into tokenized training examples, injecting tool schemas into system prompts when configured.

- `training/dpo_training.py:287-409`  
  Builds DPO prompts from multi-turn conversations with optional tool formatting, mapping chosen/rejected outputs for preference optimization.

- `demo/openai_api.py:205-487`  
  Implements OpenAI-compatible chat serving over local HF models, including ReAct prompt construction and parsing model output into `tool_calls` metadata.

- `demo/chatpdf.py:341-419`  
  Demonstrates practical retrieval-augmented QA: retrieve top chunks from local corpus, build a grounded prompt, and stream generation.

## 6. Use-Case Mapping

The assigned primary use case (`Browser / Terminal Use`) looks **incorrect** for this repository. The code does not implement browser control agents, terminal-executing agents, or MCP-style tool runtime for environment manipulation.

A better fit is **Workflow Automation**: this repo automates a full LLM lifecycle (data transformation, supervised tuning, preference tuning, serving), with optional tool-call-aware prompt formatting and RAG QA. Secondary fit could be “RAG + Agents” only in a loose sense (single-model tool-call formatting + RAG), but not a true multi-agent runtime system.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - End-to-end practical pipeline from data prep to fine-tuning to deployment demos.
  - Strong support for multiple alignment stages (SFT, DPO, ORPO, GRPO, etc.).
  - Thoughtful tool-call format compatibility across major model prompt dialects.
  - OpenAI-compatible local serving path lowers integration friction.
  - RAG demo includes multilingual chunking and hybrid similarity retrieval.

- **Limitations:**
  - No true multi-agent coordination runtime (no planner-worker graph/team orchestration).
  - Tool-calling is largely formatting/parsing; actual external tool execution loop is minimal.
  - Agent logic is prompt-template-centric and brittle to output format deviations.
  - Browser/terminal operation capabilities are absent.
  - Core scripts are large monoliths; orchestration abstractions are limited.

- **Research relevance:**
  - Useful evidence for **agent-style data formatting** in instruction/preference training pipelines.
  - Useful as a case of **single-agent ReAct emulation** in OpenAI-compatible serving.
  - Relevant for studies on **medical-domain LLM lifecycle engineering** rather than MAS architecture.
  - Limited evidence for claims about multi-agent coordination techniques.

## 8. Machine-readable classification

MAS_RELATED: yes
USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
