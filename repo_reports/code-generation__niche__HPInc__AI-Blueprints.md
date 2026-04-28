---
repo_name: HPInc/AI-Blueprints
url: "https://github.com/HPInc/AI-Blueprints"
stars: 214
forks: 15
contributors_count: 38
last_commit_date: "2026-04-22T03:57:00+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 4
architecture_labels: [LangGraph, LangChain, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T15:46:41.721804+00:00"
model: auto
duration_s: 84.4
clone_size_kb: 88613
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`HPInc/AI-Blueprints` is a monorepo of runnable AI blueprints (mostly notebooks + MLflow model wrappers + optional Streamlit apps), not a single application. The agentic parts are concentrated in subprojects like `generative-ai/agentic-feedback-analyzer-with-langgraph`, `generative-ai/agentic-github-repo-analyzer-with-langgraph`, and `generative-ai/agentic-audio-rag-with-langgraph`, where users run a notebook or deployed endpoint to ask questions over documents/repos/audio and receive synthesized answers plus trace messages. In practice, a user supplies topic/question/input content, the graph executes multiple LLM-driven steps (relevance, rewrite, chunk reasoning, synthesis), and returns a final markdown answer. So the repo solves “build-and-deploy end-to-end AI workflows” more than a single narrow model task.

## 2. Agent Framework & Architecture

The implemented frameworks are **LangGraph + LangChain** (confirmed by imports like `from langgraph.graph import StateGraph` and LangChain document split/load classes). I did not find runtime `CrewAI` or `AutoGen` framework usage in source imports.

Architecture is graph-based, with role-specialized node functions acting as agents over shared state (`TypedDict` state objects). For example, the feedback/github analyzers build a graph with nodes such as `check_relevance`, `check_memory`, `rewrite_question`, `generate_answer_per_chunks`, and `generate_synthetized_answer` in `src/agentic_workflow.py`, while node behaviors/prompts live in `src/agentic_nodes.py`. The “intelligence” is mainly prompt engineering plus routing logic (conditional edges), not a learned planner model.

The audio blueprint uses a similar LangGraph pattern but swaps text-RAG chunks for retrieval over CLAP embeddings + reranking, then delegates final answer generation to a Qwen Omni adapter (`QwenOmniAgent`) before caching and output (`generative-ai/agentic-audio-rag-with-langgraph/src/agentic_workflow.py:28-197`, `.../src/qwen_agent.py:42-188`).

## 3. Orchestration Pattern

Closest match: **graph (LangGraph-style state machine)** with conditional branches and sequential stages.

Control flow is explicit via nodes/edges and routing functions:

```49:81:generative-ai/agentic-feedback-analyzer-with-langgraph/src/agentic_workflow.py
agentic_graph.add_edge(START, "ingest_question")
agentic_graph.add_edge("ingest_question", "check_relevance")

def route_relevance(state: AgenticState) -> Literal["irrelevant", "relevant"]:
    return "relevant" if state["is_relevant"] else "irrelevant"

agentic_graph.add_conditional_edges(
    "check_relevance",
    route_relevance,
    {"irrelevant": "output_answer", "relevant": "check_memory"},
)
```

Audio graph has a second conditional branch (memory hit vs retrieval path):

```182:195:generative-ai/agentic-audio-rag-with-langgraph/src/agentic_workflow.py
def after_memory(state: AudioState):
    return "output_answer" if state.get("from_memory") else "retrieve"

g.add_conditional_edges(
    "check_memory",
    after_memory,
    {"output_answer": "output_answer", "retrieve": "retrieve"},
)
g.add_edge("retrieve", "rerank")
g.add_edge("rerank", "generate_audio")
```

This is not swarm or peer-to-peer; it is a centrally defined DAG/state machine.

## 4. Tools & External Integrations

- **Local LLM inference via llama.cpp (`LlamaCpp`)**: initialized in MLflow model wrappers and injected into graph state (`generative-ai/agentic-feedback-analyzer-with-langgraph/src/mlflow/model.py:97-125`, similarly in github analyzer).
- **LangChain document processing**: loaders and recursive chunking for txt/pdf/docx/xlsx/csv/md/ipynb (`.../demo/streamlit/main.py:11-19`, `130-188`; chunking in `.../src/agentic_nodes.py:203-253`).
- **GitHub repository download (HTTP zip)**: Streamlit/notebook utility downloads `https://github.com/<owner>/<repo>/archive/refs/heads/main.zip` via `requests` (`generative-ai/agentic-github-repo-analyzer-with-langgraph/demo/streamlit/main.py:75-113`; also notebook code in `.../notebooks/run-workflow.ipynb` around the `download_github_repo` cell).
- **MLflow serving endpoint integration**: UI posts inference payload to local `/invocations` endpoint (`.../demo/streamlit/main.py:57`, `216-223`).
- **Audio retrieval stack (agentic-audio-rag)**: FAISS index + CLAP embeddings + MMR reranking (`generative-ai/agentic-audio-rag-with-langgraph/src/segment_audio_embeddings.py:16-33`, `173-195`, `316-387`).
- **Media preprocessing via ffmpeg/soundfile/torchaudio**: converts audio/video to WAV and segments windows before embedding (`.../segment_audio_embeddings.py:51-114`, `117-140`).
- **Qwen multimodal generation**: Qwen Omni processor/model used to answer from retrieved audio segments (`.../src/qwen_agent.py:114-163`).

No MCP servers, browser automation, or shell-executing agent tools are wired in these agentic pipelines.

## 5. Notable Code Walkthrough

- `generative-ai/agentic-feedback-analyzer-with-langgraph/src/agentic_workflow.py:31-83`  
  Defines the LangGraph topology (nodes + conditional edges) that drives the full feedback QA workflow from ingestion to final output.

- `generative-ai/agentic-feedback-analyzer-with-langgraph/src/agentic_nodes.py:53-116, 256-453`  
  Contains core agent behaviors and prompts: relevance classification, per-chunk answering, and final synthesis over grouped chunk responses.

- `generative-ai/agentic-feedback-analyzer-with-langgraph/src/mlflow/model.py:78-125, 172-225`  
  Production wrapper that initializes `LlamaCpp`, compiles the graph, and exposes `predict()` for batch/API invocation.

- `generative-ai/agentic-github-repo-analyzer-with-langgraph/demo/streamlit/main.py:75-113, 161-217`  
  Practical ingestion front-end: downloads a GitHub repo, loads supported files, concatenates content, and sends it to deployed agentic model endpoint.

- `generative-ai/agentic-audio-rag-with-langgraph/src/agentic_workflow.py:66-141, 160-197`  
  Audio-specific state graph combining relevance probe, cache lookup, retrieval/reranking, and Qwen-based answer generation.

## 6. Use-Case Mapping

Although the repository includes a `code-generation-with-langchain` blueprint, the **agentic** implementations inspected here are primarily orchestrated analysis pipelines (repo analysis, feedback analysis, audio QA) rather than autonomous code-writing agents. They realize the assigned use case only indirectly (e.g., analyzing code repositories as documents), while the dominant runtime pattern is multi-step automation of ingestion/retrieval/reasoning/synthesis. So the better top-level category for the repo’s multi-agent behavior is **Workflow Automation**, with secondary overlap into **RAG + Agents**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear, inspectable LangGraph orchestration with explicit routing and state transitions.
  - End-to-end packaging pattern (notebook -> MLflow model -> Streamlit UI) is reproducible across multiple blueprints.
  - Role-specialized prompts provide interpretable “agent” responsibilities (relevance, rewrite, chunk QA, synthesis).
  - Practical multimodal extension in audio blueprint (CLAP retrieval + Qwen answering + memory cache).
  - Uses local/open models (`LlamaCpp`) enabling offline-style deployment scenarios.

- **Limitations:**
  - “GitHub repo analyzer” graph code is largely template-reused from feedback analyzer; domain-specific repo reasoning is limited.
  - Multi-agent behavior is single-LLM role prompting, not independent agent entities with negotiation/planning.
  - Heavy logic is duplicated across blueprints, increasing maintenance risk.
  - Limited automated evaluation/tests around orchestration correctness and failure handling.
  - Notebook/Streamlit ingestion concatenates large corpora; scalability/token efficiency constraints are only partially addressed.

- **Research relevance:**
  - Good evidence of **graph-orchestrated, role-prompted MAS-like workflows** in applied enterprise templates.
  - Useful case for studying **conditional routing + memory gating** effects on agent pipeline efficiency.
  - Demonstrates **multimodal agentic RAG** design (audio retrieval + generation) in a practical stack.
  - Illustrates deployment-oriented agent engineering tradeoffs (traceability and modularity vs duplicated logic).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
