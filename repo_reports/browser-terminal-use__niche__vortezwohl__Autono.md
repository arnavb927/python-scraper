---
repo_name: vortezwohl/Autono
url: "https://github.com/vortezwohl/Autono"
stars: 209
forks: 38
contributors_count: 6
last_commit_date: "2026-03-19T04:52:04+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [LangChain, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:45:36.202639+00:00"
model: auto
duration_s: 67.5
clone_size_kb: 299
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`Autono` is a Python framework for building ReAct-style autonomous agents that choose actions from a set of callable abilities, execute them, store summarized memory, and iterate until they conclude a task. A user typically runs scripts like `demo/single_agent.py`, `demo/mcp_agent.py`, or `demo/multi_agent.py`, each of which creates one or more agents, assigns a natural-language request, and calls `.just_do_it()`. The runtime repeatedly asks an LLM to decide the next move (`NextMovePrompt`), executes either local Python functions or MCP tools, and then uses another LLM pass to summarize outcomes into memory. The result returned to the user is a final conclusion text plus execution metadata (`time_used`, `step_count`) rather than just raw tool output.

## 2. Agent Framework & Architecture

This repo is **primarily a custom agent framework** built in `autono/*`, with **LangChain model interfaces** (`BaseChatModel`, `ChatOpenAI`, `ChatTongyi`) used as the LLM backend abstraction (`autono/brain/lm/openai.py:1-24`, `autono/brain/lm/dashscope.py:1-21`). It is **not** LangGraph/AutoGen/CrewAI in code structure. MCP support is integrated via the Python `mcp` SDK (`autono/util/mcp_session.py:4-75`, `autono/brain/mcp_agent.py:23-40`).

Architecture-wise, `BaseAgent` holds abilities, request decomposition, and self-introduction generation (`autono/brain/base_agent.py:27-163`). `Agent` adds the core ReAct loop with memory and probabilistic stopping (`autono/brain/agent.py:99-158`, `195-208`). “Intelligence” lives mostly in prompt classes (`autono/prompt/next_move_prompt.py`, `executor_prompt.py`, `introspection_prompt.py`) rather than a graph planner: the LLM is prompted to decide one ability at a time, then prompted again to summarize and eventually conclude.

Multi-agent behavior is implemented through **agentic abilities**: wrapping one agent as a callable ability of another using `@agentic`, which internally creates `AgenticAbility`/`McpAgenticAbility` and relays request + memory (`autono/util/agentic.py:11-14`, `autono/ability/agentic_ability.py:18-66`). So MAS is achieved by nested agent calls rather than a dedicated coordinator graph engine.

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker), ReAct loop-based**.

The top-level agent runs a sequential think-act-observe loop and can delegate to subordinate agents via agentic abilities. Control is centralized in `Agent.just_do_it()` / `McpAgent.just_do_it()`, where each iteration asks `NextMovePrompt` for one action, executes it, memorizes summary, and repeats (`autono/brain/agent.py:112-141`, `autono/brain/mcp_agent.py:87-116`).

```122:140:autono/brain/agent.py
next_move = NextMovePrompt(
    request=combined_request,
    abilities=self._abilities,
    history=self.memory
).invoke(self._model)
if isinstance(next_move, BeforeActionTakenMessage):
    ...
    if action.name.startswith(AGENTIC_ABILITY_PREFIX):
        args = {
            'request': self._request,
            'request_by_step': self._request_by_step,
            'memory': self.memory,
            ...
        }
    __after_execution_msg = self.execute(args=args, action=action)
```

Delegation wiring in demo shows a manager (`mcp_agent`) granted worker-agent abilities (`jack`, `tylor`) and then executing one unified request:

```47:66:demo/multi_agent.py
@agentic(jack)
def agent1():
    return

@agentic(tylor)
def agent2():
    return

mcp_agent = await McpAgent(session, model, 'mcp_agent').fetch_abilities()
mcp_agent.grant_abilities([agent1, agent2])
return (await mcp_agent.assign(request).just_do_it(...)).conclusion
```

## 4. Tools & External Integrations

- **LLM providers via LangChain chat models**: OpenAI-compatible, DeepSeek (OpenAI-compatible endpoint), DashScope Qwen (`autono/brain/lm/openai.py:3-24`, `deepseek.py:3-24`, `dashscope.py:3-21`).
- **MCP client integration (stdio/SSE/websocket)**: session lifecycle decorator and transport selection (`autono/util/mcp_session.py:39-75`).
- **MCP tool execution wrapper**: converts MCP `Tool` specs into callable abilities and calls `session.call_tool(...)` (`autono/ability/mcp_ability.py:12-38`).
- **Browser automation via Playwright MCP server (demo)**: local MCP server exposes tools such as `playwright_navigate`, `playwright_click`, `playwright_fill`, `playwright_screenshot`, HTML/text extraction (`demo/mcp_server/playwright-plus-python-mcp.py:52-158`, `363-387`).
- **Filesystem writes (local Python ability examples)**: e.g., `write_file` abilities in demos (`demo/single_agent.py`, `demo/mcp_agent.py:24-28`, `demo/multi_agent.py:33-37`).
- **No built-in vector DB / RAG datastore**: no Chroma/Pinecone/pgvector wiring found in runtime source.

## 5. Notable Code Walkthrough

- `autono/brain/agent.py:37-158` - Core synchronous autonomous loop: next-action selection, hook interception, action execution, memory updates, and final introspective response generation.
- `autono/prompt/next_move_prompt.py:40-240` - The main policy prompt; forces structured output (`args` + `ability`), retries on format errors, and performs fuzzy matching for ability/argument robustness.
- `autono/ability/agentic_ability.py:18-66` - Implements cross-agent delegation by wrapping another agent as an ability and relaying shared memory + hooks.
- `autono/brain/mcp_agent.py:23-138` - Async agent variant that discovers MCP tools and executes async abilities, enabling external tool ecosystems.
- `demo/multi_agent.py:40-79` - Best end-to-end MAS example combining MCP tools plus two specialized worker agents under one orchestrating MCP agent.

## 6. Use-Case Mapping

The assigned label **Browser / Terminal Use** is only partially accurate: this repo can do browser tasks through MCP (notably the Playwright demo server), but browser control is an optional integration, not the core design center. The core framework is broader autonomous task orchestration over arbitrary abilities (math, file I/O, MCP tools, delegated sub-agents), with stepwise planning/execution loops and memory-based progress tracking (`autono/brain/agent.py`, `autono/prompt/*`). A better primary category is **Workflow Automation**, while Browser/Terminal use is a showcased tool domain via MCP demos.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear modular separation of decision (`NextMovePrompt`), execution (`ExecutorPrompt`), and reflection (`IntrospectionPrompt`).
  - Built-in multi-agent delegation through `@agentic` with memory transfer, enabling hierarchical collaboration.
  - Robustness tricks: output-format retries and fuzzy matching for ability names/params in `NextMovePrompt`.
  - Unified ability abstraction spans local Python functions and MCP tools.
  - Hook system (`BeforeActionTaken`, `AfterActionTaken`) improves observability/intervention.

- **Limitations:**
  - No formal test suite; demos are the main validation path.
  - Heavy reliance on prompt-format compliance and string parsing can be brittle.
  - Termination logic is heuristic/probabilistic rather than guaranteed convergence.
  - No first-class long-term storage, retrieval, or vector-backed memory/RAG.
  - Multi-agent coordination is hierarchical delegation only; no richer peer negotiation/swarm protocol.

- **Research relevance:**
  - Useful example of prompt-centric ReAct orchestration with explicit memory summarization loops.
  - Demonstrates practical hierarchical MAS composition via “agent-as-tool” abstraction.
  - Shows integration of MCP as a tool substrate for embodied/browser actions in agent frameworks.
  - Illustrates lightweight robustness mechanisms (retry/fuzzy recovery) for structured LLM action outputs.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
