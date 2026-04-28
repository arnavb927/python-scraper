---
repo_name: huggingface/agents-course
url: "https://github.com/huggingface/agents-course"
stars: 28082
forks: 2026
contributors_count: 191
last_commit_date: "2026-04-15T10:16:37+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 9
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T09:06:17.376484+00:00"
model: auto
duration_s: 64.6
clone_size_kb: 4058
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`huggingface/agents-course` is primarily a curriculum repository (MDX lessons + notebooks) that teaches how to build LLM agents across multiple frameworks rather than a single production agent service. A user typically runs lesson code snippets or linked Colab notebooks to instantiate agents (e.g., `CodeAgent`, `AgentWorkflow`, LangGraph `StateGraph`) and solve tasks like web-assisted Q&A, tool-augmented assistant workflows, and agentic RAG. In Unit 3, learners assemble an “Alfred” assistant that combines retrieval over a guest dataset, web search, weather, and Hugging Face Hub stats. The output is working agent behavior demonstrations (tool calls, responses, and sometimes generated artifacts like maps), plus deployable project structure guidance (`tools.py`, `retriever.py`, `app.py`).

## 2. Agent Framework & Architecture

Framework usage is **real and explicit** in code snippets: `smolagents`, `LlamaIndex`, and `LangGraph`/LangChain are all imported and wired (`units/en/unit3/agentic-rag/agent.mdx:22-27`, `:61-79`, `:85-139`; `units/en/unit2/smolagents/multi_agent_systems.mdx:136-155`, `:241-314`). I did **not** find actual CrewAI runtime code in this repo.

Architecture is presented as parallel implementations of the same agentic task (“Alfred”) across frameworks. The “intelligence” sits in: (a) LLM-driven tool selection with tool metadata/descriptions, (b) prompts/system messages, and (c) orchestrators (manager-agent hierarchy in smolagents, or graph routing in LangGraph). In agentic-RAG lessons, retrieval is implemented as a tool (BM25-based over a custom invitee dataset), then composed with external tools into a single assistant (`units/en/unit3/agentic-rag/invitees.mdx:173-206`, `units/en/unit3/agentic-rag/agent.mdx:47-54`).

The repository also includes explicit **multi-agent hierarchy** examples where one `CodeAgent` manages another via `managed_agents=[web_agent]` (`units/en/unit2/smolagents/multi_agent_systems.mdx:241-252`, `:298-314`), which is the clearest runtime multi-agent coordination pattern shown.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)**, with additional graph-based ReAct loops in LangGraph examples.

In the multi-agent smolagents example, a manager delegates to a named worker agent:

```python
# units/en/unit2/smolagents/multi_agent_systems.mdx:241-252
web_agent = CodeAgent(..., name="web_agent", description="Browses the web to find information", ...)
```

```python
# units/en/unit2/smolagents/multi_agent_systems.mdx:298-314
manager_agent = CodeAgent(
    ...,
    managed_agents=[web_agent],
    planning_interval=5,
    final_answer_checks=[check_reasoning_and_plot],
)
```

LangGraph lessons show a **graph/state-machine loop** (`assistant -> tools -> assistant`) controlled by `tools_condition`, i.e., ReAct-style iterative orchestration (`units/en/unit3/agentic-rag/agent.mdx:123-139`; `units/en/unit2/langgraph/document_analysis_agent.mdx:162-177`).

## 4. Tools & External Integrations

- **Web search/browsing tools**: `DuckDuckGoSearchTool`, `GoogleSearchTool`, `VisitWebpageTool`, and LangChain `DuckDuckGoSearchRun` are wired in agent constructors (`units/en/unit3/agentic-rag/tools.mdx:18-25`, `:61-66`; `units/en/unit2/smolagents/multi_agent_systems.mdx:136-152`).
- **Hugging Face Hub API**: `huggingface_hub.list_models` powers a custom “hub stats” tool (`units/en/unit3/agentic-rag/tools.mdx:181-209`, `:260-281`).
- **RAG retrieval pipeline**: dataset loading via `datasets.load_dataset("agents-course/unit3-invitees")` + BM25 retriever (`langchain_community` or `llama_index`) wrapped as agent tool (`units/en/unit3/agentic-rag/invitees.mdx:80-98`, `:179-206`, `:223-238`, `:255-273`).
- **Vector store integration**: LlamaIndex `ChromaVectorStore` + `chromadb.PersistentClient` + `VectorStoreIndex` shown in tools lesson (`units/en/unit2/llama-index/tools.mdx:52-69`).
- **Model providers/inference APIs**: Hugging Face inference endpoints (`InferenceClientModel`, `HuggingFaceInferenceAPI`, `HuggingFaceEndpoint`, `ChatHuggingFace`) and examples using Together/OpenAI-compatible endpoints (`units/en/unit3/agentic-rag/agent.mdx:22-23`, `:61-63`, `:91`, `units/en/unit2/smolagents/multi_agent_systems.mdx:237-239`, `:261-266`).
- **MCP (documented integration path)**: LlamaIndex MCP toolspec usage (`BasicMCPClient`, `McpToolSpec`) is shown as optional integration (`units/en/unit2/llama-index/tools.mdx:101-129`).

## 5. Notable Code Walkthrough

- `units/en/unit3/agentic-rag/agent.mdx:47-54, 75-79, 123-139`  
  Defines “Alfred” agent assembly in three frameworks; this is the central end-to-end composition point where retrieval + web + utility tools become a usable assistant.

- `units/en/unit3/agentic-rag/invitees.mdx:80-98, 173-206, 289-337`  
  Implements the RAG core: loads custom invitee dataset, converts to documents, builds BM25 retriever, exposes it as a tool, then injects it into the agent.

- `units/en/unit3/agentic-rag/tools.mdx:89-117, 179-209, 298-343`  
  Builds auxiliary tools (weather, HF Hub stats, web search) and wires them into Alfred; this is the practical tool-integration layer.

- `units/en/unit2/smolagents/multi_agent_systems.mdx:241-252, 298-314, 378-394`  
  Shows true multi-agent runtime coordination (`manager_agent` + `web_agent`) with planning and final-output validation hooks.

- `units/en/unit2/langgraph/document_analysis_agent.mdx:49-53, 126-146, 162-177`  
  Demonstrates explicit graph orchestration with typed state, tool node, conditional routing, and iterative assistant/tool loop.

## 6. Use-Case Mapping

The repository does realize **RAG + Agents** concretely in Unit 3: it builds a retriever tool over domain-specific guest data, then lets an LLM agent decide when to call retrieval vs web/weather/hub tools (`units/en/unit3/agentic-rag/invitees.mdx:166-206`, `units/en/unit3/agentic-rag/agent.mdx:47-54`). However, at repository level this is an educational catalog spanning many patterns (single-agent tool use, graphs, multi-agent manager-worker, evaluation), not one narrowly scoped RAG system.

So the upstream “RAG + Agents” label is valid for a major unit, but the **best repo-level categorization** is broader instructional **Workflow Automation**: orchestrating tools, retrieval, and subagents to complete multi-step tasks.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Demonstrates the same agentic workflow across three frameworks, enabling comparative analysis.
  - Includes genuine multi-agent hierarchy examples (`managed_agents`) rather than only single-agent demos.
  - Shows concrete tool engineering patterns (schema/design, custom tools, retrieval tools, graph routing).
  - Provides realistic integration surfaces (HF Hub API, web search, Chroma, optional MCP).
  - Emphasizes memory/state handling and orchestration logic, not only prompt text.

- **Limitations:**
  - Most code is in instructional `.mdx` snippets, not a cohesive, tested production package.
  - Limited automated tests/benchmarks for the specific snippets in-repo; reproducibility depends on external notebooks/providers.
  - Some examples use dummy/mock tools (e.g., weather), which weakens real-world reliability claims.
  - Heavy dependency on external APIs/keys and model providers; behavior can vary by runtime environment.
  - Multi-agent examples are illustrative and relatively small-scale (not long-running distributed MAS infrastructure).

- **Research relevance:**
  - Useful evidence for **design patterns** in practical agent engineering (tool-calling, graph loops, manager-worker delegation).
  - Useful for studying **framework-level orchestration tradeoffs** (smolagents vs LlamaIndex vs LangGraph).
  - Supports analysis of **agentic RAG as tool-mediated retrieval**, especially BM25/vector-tool compositions.
  - Relevant as a pedagogical artifact for how mainstream ecosystems operationalize “agent” abstractions.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
