---
repo_name: RobotecAI/rai
url: "https://github.com/RobotecAI/rai"
stars: 495
forks: 66
contributors_count: 26
last_commit_date: "2026-04-13T11:54:13+00:00"
primary_use_case: Simulation
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Simulation]
generated_at: "2026-04-27T16:16:34.080402+00:00"
model: auto
duration_s: 80.5
clone_size_kb: 62419
uses_mas: yes
final_use_case: Simulation
---
## 1. Overview

`RobotecAI/rai` is a ROS 2-centered agentic framework for embodied robotics, where users run Python agents (or ROS launch setups) that receive human instructions, call robot/simulation tools, and return actions or explanations. In practice, you run components like `ReActAgent`/state-based agents or launch files such as `src/rai_bringup/launch/sim_whoami_demo.launch.py`, then interact through CLI/Streamlit/HRI topics while the agent uses ROS interfaces and perception/navigation/manipulation tools. The codebase is organized as a monorepo (`rai_core`, `rai_sim`, `rai_whoami`, `rai_bench`, etc.) combining LLM orchestration with robot middleware. The end result is not just chat output: it is tool-driven robot behavior, environment querying, and scenario execution in real or simulated setups.

## 2. Agent Framework & Architecture

The actual framework stack is **LangChain Core + LangGraph** (not CrewAI). This is clear from imports and graph construction in files like `src/rai_core/rai/agents/langchain/core/react_agent.py:22-33`, `src/rai_core/rai/agents/langchain/core/plan_agent.py:16-20`, and `src/rai_core/rai/agents/langchain/core/megamind.py:25-35`.

Architecture-wise, there are multiple agent patterns implemented:
- A single-agent ReAct graph (`create_react_runnable`) with optional tool loop (`src/rai_core/rai/agents/langchain/core/react_agent.py:88-133`).
- A state-augmented agent that injects periodic world-state aggregations before each LLM step (`src/rai_core/rai/agents/langchain/core/state_based_agent.py:106-137`, `src/rai_core/rai/agents/langchain/state_based_agent.py:46-117`).
- A planner/executor/replanner graph (`create_plan_execute_agent`) (`src/rai_core/rai/agents/langchain/core/plan_agent.py:71-216`).
- A true multi-agent supervisor (`create_megamind`) that delegates to specialist executors via handoff tools (`src/rai_core/rai/agents/langchain/core/megamind.py:296-374`).

The “intelligence” lives primarily in prompt templates + graph transitions: planner/replanner prompts, specialist system prompts, and conditional routing (`tools_condition`, structured success checks, and `Command(goto=...)` handoffs).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker) graph orchestration**.

The clearest MAS implementation is `megamind`: one supervisor agent creates/updates plan steps and delegates each step to exactly one specialist executor agent, then receives control back (`src/rai_core/rai/agents/langchain/core/megamind.py:323-373`).

```304:356:src/rai_core/rai/agents/langchain/core/megamind.py
executor_agents[executor.name] = create_react_structured_agent(...)
handoff_tools.append(create_handoff_tool(agent_name=executor.name, ...))
...
megamind_agent = create_react_agent(
    megamind_llm,
    tools=handoff_tools,
    prompt=megamind_system_prompt,
)
```

Control transfer is explicit via LangGraph `Command` handoff tools:

```163:178:src/rai_core/rai/agents/langchain/core/megamind.py
def handoff_tool(task_instruction: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    return Command(
        goto=agent_name,
        update={"step": task_instruction, "step_messages": []},
        graph=Command.PARENT,
    )
```

This is layered on top of graph-style internal loops (LLM -> tools -> LLM) in the worker agents, so overall pattern is hierarchical manager-worker implemented as LangGraph state machines.

## 4. Tools & External Integrations

- **ROS 2 topics/services/actions (native tools):** toolkit composes action/service/topic tools (`src/rai_core/rai/tools/ros2/generic/toolkit.py:22-50`), plus many concrete ROS tool modules under `src/rai_core/rai/tools/ros2/...`.
- **ROS 2 CLI subprocess tools:** agent-callable wrappers for `ros2 action/service/node/param/interface/topic` commands (`src/rai_core/rai/tools/ros2/cli.py:55-184`).
- **Simulation bridge integration:** simulation-specific tool reads scene entities/poses via `SimulationBridge` (`src/rai_sim/rai_sim/tools.py:21-62`).
- **Vector DB retrieval (RAG-like memory):** FAISS-backed query tool (`src/rai_whoami/rai_whoami/tools/vector_db.py:30-55`) and FAISS client in `src/rai_whoami/rai_whoami/vector_db/faiss.py`.
- **LLM providers:** OpenAI, AWS Bedrock, Ollama, Google Gemini selected via config (`src/rai_core/rai/initialization/model_initialization.py:179-217`).
- **Tracing/observability:** Langfuse and LangSmith callback wiring (`src/rai_core/rai/initialization/model_initialization.py:359-402`).
- **HRI transport connectors:** conversion between LangChain messages and multimodal HRI message objects (`src/rai_core/rai/communication/hri_connector.py:37-131`), with ROS2 connectors used by state-based agents.

No MCP server protocol integration is evident in the core runtime path.

## 5. Notable Code Walkthrough

- `src/rai_core/rai/agents/langchain/core/megamind.py:123-374` - Defines the multi-agent supervisor pattern: executor registration, handoff-tool creation, per-executor subagent graphs, planning loop, and parent graph assembly.
- `src/rai_core/rai/agents/langchain/core/plan_agent.py:71-216` - Implements planner/executor/replanner state machine; useful because it shows explicit plan decomposition and iterative replanning with structured outputs.
- `src/rai_core/rai/agents/langchain/core/tool_runner.py:33-171` - Central tool execution runtime: validates tool calls, executes with concurrency control, handles errors/artifacts, and appends `ToolMessage` outputs back into graph state.
- `src/rai_core/rai/agents/langchain/state_based_agent.py:46-187` - Production-style long-running agent wrapper: message buffering, threading, connector integration, and periodic state aggregation injected into LLM context.
- `src/rai_bench/rai_bench/examples/tool_calling_custom_agent.py:19-96` - Concrete MAS usage example where a supervisor delegates to manipulation and navigation specialists in benchmark scenarios.

## 6. Use-Case Mapping

The assigned label **Simulation** is directionally correct: the repo includes simulation-specific tooling (`src/rai_sim/rai_sim/tools.py`), O3DE/manipulation benchmarks, and launch setups combining simulator + agents (`src/rai_bringup/launch/sim_whoami_demo.launch.py`).  

However, the broader core is a **general robot workflow orchestration framework** (message handling, tool routing, state aggregation, multi-agent delegation) that runs across simulation and real ROS systems. If forced to pick one category from your list for whole-repo classification, **Workflow Automation** is also defensible because the central abstraction is tool-driven task workflows over robot middleware.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Implements both single-agent and coordinated multi-agent (supervisor-specialist) runtime graphs, not just conceptual docs.
  - Strong ROS 2 integration depth (topics/services/actions/CLI/connectors) suitable for embodied-agent evaluation.
  - Modular orchestration primitives (`create_react_runnable`, plan-execute, megamind) make comparative experiments straightforward.
  - Multimodal message plumbing (text/images/audio artifacts) is built into tool and connector layers.
  - Includes benchmark package (`rai_bench`) that operationalizes agent performance testing.

- **Limitations:**
  - Multi-agent `megamind` appears primarily showcased in benchmark/examples rather than clearly being the default production path.
  - Considerable complexity across subpackages may raise onboarding/integration cost for non-ROS users.
  - Security/safety controls for tool execution are present but limited (e.g., basic forbidden-character checks in CLI tools).
  - Prompt-based delegation logic is powerful but may be brittle without strict policy/verification layers.
  - Some components are marked as experimental in comments/docs, suggesting evolving stability.

- **Research relevance:**
  - Good evidence of **hierarchical multi-agent delegation** in embodied task settings.
  - Useful for studying **LLM-tool orchestration over real middleware APIs** (ROS 2 actions/services/topics).
  - Supports investigation of **stateful, event-driven agent loops** with periodic world-state aggregation.
  - Provides a practical benchmark harness for analyzing model/tool-calling robustness in robotic scenarios.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Simulation
