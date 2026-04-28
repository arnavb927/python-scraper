---
repo_name: towardsai/agent-course-notebooks
url: "https://github.com/towardsai/agent-course-notebooks"
stars: 206
forks: 30
contributors_count: 3
last_commit_date: "2026-03-02T16:22:41+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 3
architecture_labels: [LangGraph, CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T16:46:55.322402+00:00"
model: auto
duration_s: 79.1
clone_size_kb: 15892
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

This repository is a **course notebook collection** for building agentic AI systems, not a single packaged application. In practice, users run Jupyter notebooks (mostly under `notebooks/`) that install supporting dependencies and then execute examples of ReAct agents, LangGraph workflows, and MCP-based multi-agent integration (e.g., `%pip install -q agentic-ai-engineering-course` in `notebooks/lesson_22_notebook.ipynb:48-55`, `notebooks/lesson_25_notebook.ipynb:52-58`). The concrete outcome is usually an automated content pipeline (research + article generation/editing), with progress streaming, review loops, and tool-calling behavior demonstrated in notebook cells. Several lessons also show end-to-end orchestration across two distinct agents/services (“Nova” and “Brown”) via MCP configuration and composed servers.

## 2. Agent Framework & Architecture

Frameworks actually evidenced in code snippets/imports are:

- **LangGraph** (`create_react_agent`, `entrypoint`, `task`, `RetryPolicy`, checkpoint savers) in `notebooks/lesson_11_notebook.ipynb:1900-2001`, `notebooks/lesson_23_notebook.ipynb:3296-3568`, `notebooks/lesson_24_notebook.ipynb:849-994`.
- **LangChain Core / LangChain model init** (`init_chat_model`, `BaseTool`, runnable abstractions) in `notebooks/lesson_22_notebook.ipynb:1406-1645`.
- **FastMCP / MCP** client-server composition in `notebooks/lesson_25_notebook.ipynb:211-258` and `notebooks/lesson_25_notebook.ipynb:596-687`.

I did **not** find actual `crewai`, `autogen`, or `llama_index` imports in repository code cells.

Architecturally, the notebooks teach a modular pattern where “intelligence” lives in: (a) system prompts, (b) tool binding (`bind_tools`), and (c) LangGraph task orchestration with retries/checkpointing. A representative pattern is an **orchestrator node** that calls worker tools (media generation jobs), followed by writer/reviewer/editor nodes coordinated in a deterministic workflow loop (`notebooks/lesson_22_notebook.ipynb:1716-1739`, `notebooks/lesson_23_notebook.ipynb:3424-3458`).

A key nuance: much production-style code (`brown.*`, `nova.*`) is referenced from external course packages or lesson directories; this repo stores the instructional notebooks and embedded code excerpts that define how those agents are wired.

## 3. Orchestration Pattern

Closest match: **Hierarchical (manager-worker) inside a sequential workflow**, implemented with LangGraph task orchestration.

- The manager/orchestrator delegates jobs via tool calls:
  
  `notebooks/lesson_22_notebook.ipynb:1716-1739`
  ```python
  model = model.bind_tools(self.toolkit.get_tools(), tool_choice="any")
  response = await self.model.ainvoke(inputs)
  if isinstance(response, AIMessage) and response.tool_calls:
      jobs = cast(list[ToolCall], response.tool_calls)
  ```

- The global flow is a staged pipeline with iterative review-edit loops:
  
  `notebooks/lesson_23_notebook.ipynb:3424-3458`
  ```python
  @task(retry_policy=retry_policy)
  async def generate_media_items(...): ...
  @task(retry_policy=retry_policy)
  async def write_article(...) -> Article: ...
  @task(retry_policy=retry_policy)
  async def generate_reviews(...) -> ArticleReviews: ...
  @task(retry_policy=retry_policy)
  async def edit_based_on_reviews(...) -> Article: ...
  ```

Control flow is therefore not a free-form swarm; it is mostly controlled orchestration with delegated specialized workers and retryable steps.

## 4. Tools & External Integrations

- **LLM providers via LangChain model abstraction** (`init_chat_model`, Gemini variants) in `notebooks/lesson_22_notebook.ipynb:1406-1446` and `notebooks/lesson_11_notebook.ipynb:1995-1998`.
- **LangGraph tool-calling ReAct agent** using a custom multimodal search tool (`@tool` + `create_react_agent`) in `notebooks/lesson_11_notebook.ipynb:1904-2001`.
- **MCP multi-server integration** (Nova + Brown servers, aggregated tools/resources/prompts) in `notebooks/lesson_25_notebook.ipynb:182-191`, `notebooks/lesson_25_notebook.ipynb:217-258`.
- **MCP composed server/proxy mounting** with FastMCP (`FastMCP.as_proxy`, `mcp.mount`, composed prompt) in `notebooks/lesson_25_notebook.ipynb:602-687`.
- **Checkpoint persistence** for workflows: in-memory and SQLite savers in `notebooks/lesson_23_notebook.ipynb:3506-3518` and `notebooks/lesson_23_notebook.ipynb:3540-3568`.
- **Local process orchestration** for agent services via subprocess (`uv ... mcp_server`) in `notebooks/lesson_25_notebook.ipynb:458-473`.

No in-repo evidence of Pinecone/Chroma/pgvector/browser automation frameworks in executable code cells for this set of lessons.

## 5. Notable Code Walkthrough

- `notebooks/lesson_11_notebook.ipynb:1900-2001`  
  Defines a concrete ReAct-style LangGraph agent with `create_react_agent`, a custom `@tool`, and Gemini model binding. This is the clearest runnable single-agent + tool loop example.

- `notebooks/lesson_22_notebook.ipynb:1618-1739`  
  Introduces base abstractions (`Toolkit`, `Node`) and orchestrator logic using `bind_tools` + `tool_calls`, showing how a manager agent emits jobs for workers.

- `notebooks/lesson_23_notebook.ipynb:3296-3458`  
  Shows full LangGraph functional orchestration (`entrypoint`, `@task`, retries) for article-generation workflow stages and iterative refinement loop.

- `notebooks/lesson_23_notebook.ipynb:3506-3568`  
  Adds short-term memory/checkpointing with `InMemorySaver` and `AsyncSqliteSaver`, making long workflows resumable and inspectable.

- `notebooks/lesson_25_notebook.ipynb:182-258,596-687`  
  Demonstrates multi-agent integration over MCP: one client connected to multiple servers and an alternative composed server that unifies capabilities + cross-agent workflow prompt.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is accurate. The dominant runtime pattern is automating a multi-step content pipeline: load context, orchestrate media generation, write article, review/edit iteratively, and persist outputs/checkpoints (`notebooks/lesson_23_notebook.ipynb:3330-3458`). The MCP lessons further automate cross-agent handoff between research and writing services (`notebooks/lesson_25_notebook.ipynb:182-191`, `notebooks/lesson_25_notebook.ipynb:644-687`).  

So while the repo is educational notebooks, its concrete implementations map strongly to automated workflow execution rather than chat-only assistance.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Demonstrates multiple orchestration styles (ReAct tool loop, task pipeline, manager-worker delegation) in one curriculum.
  - Uses practical reliability features (retry policies + checkpointing) often missing in toy agent demos.
  - Shows real multi-agent interoperability via MCP (multi-server client and composed server patterns).
  - Clear modular abstractions (`Toolkit`, node classes, config-driven model selection) support extensibility.
  - Emphasizes iterative review/edit loops aligned with production content workflows.

- **Limitations:**
  - Much “core system” logic is referenced from external packages/lesson paths, so this repo is partly a wrapper/tutorial layer.
  - Notebook-centric structure makes reproducibility and CI-style execution harder than a standalone Python package.
  - Limited in-repo hardening evidence (authz, security boundaries, cost controls) beyond instructional snippets.
  - Heavy dependence on external APIs/keys (Gemini, MCP services) for end-to-end execution.
  - Some code shown as markdown excerpts rather than fully local source modules.

- **Research relevance:**
  - Useful evidence for **hierarchical tool-using orchestration** (orchestrator emitting worker jobs).
  - Useful evidence for **hybrid deterministic-agentic pipelines** (fixed workflow skeleton + LLM decision points).
  - Useful case for **protocol-based multi-agent composition** (MCP federation/composition of independent agents).
  - Relevant for studies on **agent reliability techniques** (task-level retries, checkpoint-based resumability).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
