---
repo_name: tanishqkumar/beyond-nanogpt
url: "https://github.com/tanishqkumar/beyond-nanogpt"
stars: 1303
forks: 107
contributors_count: 3
last_commit_date: "2026-01-29T07:09:42+00:00"
primary_use_case: RAG + Agents
user_tier: Niche
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [RAG + Agents]
generated_at: "2026-04-27T15:23:37.481913+00:00"
model: auto
duration_s: 77.9
clone_size_kb: 2129
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`tanishqkumar/beyond-nanogpt` is primarily an educational deep-learning implementation repository, but it includes two runnable LLM-agent demos under `agents/`: a coding assistant and a web-search assistant. A user can run `agents/coding-agent/agent.py` for an interactive terminal agent that calls tools (search, file read/write, code execution), or `agents/basic-search-use/chat_search.py` for iterative web-grounded Q&A. The repo also contains a separate non-agent RAG evaluation script in `rag/intro_rag.py` that benchmarks retrieval-augmented prompting on SimpleQA. In practice, what users “get” is reference code showing how to build lightweight agent loops from raw completion APIs, not a production multi-agent platform.

## 2. Agent Framework & Architecture

The agent code is **custom orchestration**, not LangGraph/LangChain/CrewAI/AutoGen/LlamaIndex. The core imports use direct provider SDKs (`together`, `anthropic`) and internal tool abstractions (`agents/coding-agent/agent.py:9-20`, `agents/coding-agent/api.py:1-10`). I did not find framework imports such as `langgraph`, `langchain`, `crewai`, or `autogen` in the agent runtime files.

Architecture is single-LLM with tool loop. In `agents/coding-agent/agent.py`, one model response is parsed for `<tool_request>...</tool_request>`, local tools are executed, outputs are injected back into context, and the model is re-called until final `<output>` (`agents/coding-agent/agent.py:45-117`). The “intelligence” is split between prompt policy (`prompts/system_prompts.py`) and this control loop; tools are registered centrally in `tools/registry.py:16-29`. `agents/basic-search-use/chat_search.py` implements a simpler variant with two XML-tagged search actions (`<shallowSearchQuery>`, `<deepSearchQuery>`) and bounded iterative calls (`agents/basic-search-use/chat_search.py:142-224`).

No runtime coordination between multiple distinct LLM agents is implemented (e.g., planner/worker teams). Even where multiple models appear (student/teacher in `rag/intro_rag.py`), that is an eval pipeline, not agent-to-agent collaboration.

## 3. Orchestration Pattern

Closest match: **sequential single-agent tool loop** (“ReAct-style”), not hierarchical/graph/swarm.

Control flow in the coding agent is linear: model -> parse/execute tool calls -> model reflection -> repeat/finish.

```45:117:agents/coding-agent/agent.py
while contains_tool_calls(res_after_tools) and (not '<output>' in res_after_tools):
    res_after_tools = check_and_fix_tool_calls(res_after_tools) 
    for tool in ALL_TOOLS:
        res_after_tools = tool.call(res_after_tools)
    memory.local_tool_memory += res_after_tools + "\n\n\n"
    res_after_tools = api(... system_prompt=reflect_or_finalize_prompt)
    if not contains_tool_calls(res_after_tools):
        return finalize(res_after_tools, memory, client, model_name)
```

Tool dispatch itself is also sequential by scanning tool tags and replacing them with outputs:

```51:71:agents/coding-agent/tools/base_tool.py
def call(self, s: str) -> str:
    while True:
        res = self._parse(s)
        if not res:
            break
        for parsed in res:
            tool_output_json = self._execute(tool_input).model_dump()
            wrapped_output_s = f"<tool_output name='{self.name}' ...>" + output_s + f"</tool_output>"
            s = s[:start] + wrapped_output_s + s[end:]
```

## 4. Tools & External Integrations

- **LLM inference APIs (Together + Anthropic):** unified wrapper in `agents/coding-agent/api.py:6-53`; interactive agent config in `agents/coding-agent/agent.py:192-196`.
- **Web search (Google Custom Search JSON API):** wired in `agents/coding-agent/tools/search_tool.py:18-33`; optional page scraping via `requests` + `BeautifulSoup` in `search_tool.py:12-16,55-71`.
- **Shell/Python execution tool:** subprocess-based runner in `agents/coding-agent/tools/run_code_tool.py:24-67` (supports `"python"` and `"shell"`).
- **Filesystem tools:** read/write wrappers in `agents/coding-agent/tools/read_file_tool.py:22-58` and `agents/coding-agent/tools/write_file_tool.py:25-67`, scoped to `agent_scratch`.
- **Tool registry/composition:** `agents/coding-agent/tools/registry.py:16-29`.
- **Basic-search agent external integration:** Google Custom Search + scraping in `agents/basic-search-use/chat_search.py:98-139`.
- **RAG stack (non-agent script):** `SentenceTransformer` bi-encoder + `CrossEncoder` reranker in `rag/intro_rag.py:68,324-326`; dataset via Hugging Face `load_dataset` in `rag/intro_rag.py:66,312`.

No MCP servers, browser automation stacks (Playwright/Browserbase), or vector DB services (Chroma/Pinecone/pgvector) are wired.

## 5. Notable Code Walkthrough

- `agents/coding-agent/agent.py:45-123` - Main orchestration loop: detects tool calls, executes registered tools, invokes reflection/finalization prompts, and enforces max tool-call budget.
- `agents/coding-agent/tools/base_tool.py:19-72` - Shared tool protocol layer: parses XML-wrapped JSON requests, validates with Pydantic types, and injects standardized `<tool_output>` blocks back into model context.
- `agents/coding-agent/tools/search_tool.py:18-117` - Concrete external tool implementation for Google search with shallow (snippets) and deep (scraped content) modes.
- `agents/basic-search-use/chat_search.py:186-224` - Minimal standalone agent loop showing iterative search-query tags and repeated LLM calls until no further search request.
- `rag/intro_rag.py:241-374` - Retrieval+rerank+prompting pipeline and async eval loop; important for RAG pedagogy, but not a multi-agent runtime.

## 6. Use-Case Mapping

The upstream assignment `RAG + Agents` is **partially accurate but overstated** for this repository as a whole. The repo contains:
1) single-agent tool-use demos (`agents/`) and  
2) a separate RAG evaluation script (`rag/intro_rag.py`) that does retrieval augmentation without agent orchestration.

Because the code does not implement coordinated multi-agent runtime behavior, the best overall category is **Workflow Automation** (interactive single-agent automation with tools and iterative control). If categorizing submodules separately: `agents/*` fits Workflow Automation, while `rag/intro_rag.py` fits classic RAG experimentation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Very transparent, minimal agent loops that expose core mechanics without framework abstraction (`agents/coding-agent/agent.py`).
  - Clean tool interface pattern via `BaseTool` + typed inputs/outputs (`tools/base_tool.py`).
  - Demonstrates iterative tool-reflection cycles and memory compression in compact code (`memory.py`, `system_prompts.py`).
  - Includes both lightweight search agent and richer coding/tool agent variants for comparison.
  - Practical external integrations (LLM providers + Google search + shell/file ops).

- **Limitations:**
  - Not a true multi-agent system; no planner-worker or graph of collaborating agents.
  - Heavy reliance on prompt-format discipline (`<tool_request>` JSON), brittle to formatting failures.
  - Security model is limited (subprocess shell execution, partial path protections, prompt/runtime mismatch about sandbox guarantees).
  - No formal state machine, retry policies, or robust observability for complex long-horizon tasks.
  - RAG module is disconnected from agent runtime; no integrated “RAG agent” architecture.

- **Research relevance:**
  - Good evidence of **single-agent tool-use orchestration** from first principles (ReAct-like loops).
  - Useful as a pedagogical baseline for studying prompt-scaffolded tool calling vs framework-based agents.
  - Illustrates practical memory summarization and context-management tradeoffs in iterative agents.
  - Not strong evidence for emergent multi-agent coordination or decentralized MAS behavior.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
