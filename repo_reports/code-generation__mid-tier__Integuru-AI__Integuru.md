---
repo_name: Integuru-AI/Integuru
url: "https://github.com/Integuru-AI/Integuru"
stars: 4574
forks: 360
contributors_count: 7
last_commit_date: "2026-04-14T01:39:02+00:00"
primary_use_case: Code Generation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T13:23:57.014672+00:00"
model: auto
duration_s: 71.8
clone_size_kb: 27913
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`Integuru` is a CLI tool that takes a user intent (for example, “download utility bills”), a browser HAR capture, and cookies, then reverse-engineers the internal API call chain needed to execute that action. The user runs `integuru` via `click` (`integuru/__main__.py:10-57`), and the runtime builds a dependency DAG of requests by tracing dynamic identifiers/tokens across responses (`integuru/agent.py:292-403`). It can optionally generate runnable Python integration code from that DAG (`integuru/util/print.py:339-451`). In practice, this is an “integration reconstruction” pipeline: infer endpoint, infer dependencies, then synthesize code.

## 2. Agent Framework & Architecture

The repo **actually uses LangGraph + LangChain OpenAI**, not CrewAI. Evidence: `StateGraph`/`END` imports in `integuru/graph_builder.py:1-2`, and `ChatOpenAI` in `integuru/util/LLM.py:1-15`. There is no CrewAI import in runtime code.

Architecture is a **single orchestrated IntegrationAgent** class with multiple LLM-driven stages, rather than multiple independent agent instances. The “intelligence” mostly lives in prompt templates + function-calling schemas inside methods like `end_url_identify_agent`, `dynamic_part_identifying_agent`, `input_variables_identifying_agent`, and `get_simplest_request` (`integuru/agent.py:38-290`). Persistent state is maintained in a typed LangGraph state object (`integuru/models/agent_state.py:3-9`) and a NetworkX DAG manager (`integuru/models/DAGManager.py:6-60`).

The pipeline starts with selecting the action URL from HAR metadata, converts that to a master request node, repeatedly discovers dynamic parts, finds upstream requests/cookies that produce them, and appends edges until no unresolved nodes remain (`integuru/graph_builder.py:22-53`, `integuru/agent.py:227-403`).

## 3. Orchestration Pattern

Closest match: **graph/state-machine orchestration (LangGraph-style) with iterative loop**.

Control flow is explicitly encoded as a directed graph with a conditional back-edge:

```28:50:integuru/graph_builder.py
graph_builder.add_node("IntegrationAgent", agent.end_url_identify_agent)
graph_builder.set_entry_point("IntegrationAgent")
graph_builder.add_node("urlTocurl", agent.url_to_curl)
graph_builder.add_edge("IntegrationAgent", "urlTocurl")
graph_builder.add_node("dynamicurlDataIdentifyingAgent", agent.dynamic_part_identifying_agent)
graph_builder.add_edge("urlTocurl", "dynamicurlDataIdentifyingAgent")
graph_builder.add_node("findcurlFromContent", agent.find_curl_from_content)
graph_builder.add_conditional_edges(
    "findcurlFromContent",
    partial(check_end_condition, agent=agent, to_generate_code=to_generate_code),
    {"end": END, "continue": "dynamicurlDataIdentifyingAgent"},
)
```

The loop condition is queue-based: continue while unresolved nodes remain.

```7:19:integuru/graph_builder.py
def check_end_condition(state, agent, to_generate_code):
    agent.dag_manager.detect_cycles()
    if len(state.get("to_be_processed_nodes", [])) == 0:
        print("------------------------Successfully analyzed!!!-------------------------------", flush=True)
        print_dag(agent.dag_manager.graph, agent.global_master_node_id)
        visualize_dag(agent.dag_manager.graph)
        print_dag_in_reverse(agent.dag_manager.graph, to_generate_code=to_generate_code)
        return "end"
    else:
        print("Continuing execution", flush=True)
        return "continue"
```

## 4. Tools & External Integrations

- **OpenAI LLM API via LangChain `ChatOpenAI`**: core reasoning and code synthesis (`integuru/util/LLM.py:1-37`, used throughout `integuru/agent.py` and `integuru/util/print.py:247-266`).
- **LangGraph runtime**: stage orchestration and stateful event stream (`integuru/graph_builder.py:1-53`, invoked in `integuru/main.py:20-35`).
- **HAR + cookie local files**: primary data source for reverse engineering (`integuru/util/har_processing.py:92-243`).
- **NetworkX DAG + Matplotlib visualization**: dependency graph storage and rendering (`integuru/models/DAGManager.py:10-60`, `integuru/util/print.py:71-93`).
- **Playwright (data capture helper script)**: records HAR and cookies before agent execution (`create_har.py:3-34`).
- **No vector DB / retrieval store / external MCP / browser-use at runtime**: runtime logic is HAR/cookie-driven plus LLM calls; browser automation is pre-processing only.

## 5. Notable Code Walkthrough

- `integuru/graph_builder.py:22-53` - Defines the LangGraph state machine, including the conditional loop that repeatedly resolves dependencies until completion; this is the orchestration backbone.
- `integuru/agent.py:38-75` - `end_url_identify_agent` uses function-calling to map user intent to one concrete action URL from HAR-derived candidates.
- `integuru/agent.py:146-225` - `dynamic_part_identifying_agent` detects server-validated dynamic fields in cURL requests, then updates DAG node metadata that drives dependency discovery.
- `integuru/agent.py:292-403` - `find_curl_from_content` searches prior responses/cookies for unresolved values, creates upstream nodes, and adds edges; this is the core reverse-engineering step.
- `integuru/util/print.py:138-266` and `339-451` - traverses the DAG in dependency order and asks an LLM to generate per-node Python request functions, then aggregates into runnable code.

## 6. Use-Case Mapping

Although it outputs generated Python, the core system behavior is better categorized as **Workflow Automation** than pure Code Generation. The main value is automated reconstruction of a multi-step API workflow from traffic traces: identify action endpoint, infer dependency chain, and sequence calls (`integuru/agent.py:227-403`, `integuru/graph_builder.py:45-50`). Code generation is downstream packaging of that discovered workflow (`integuru/util/print.py:401-451`), not the primary reasoning objective. So the assigned “Code Generation” label is understandable but secondary to workflow automation.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Uses explicit graph state + queue loop rather than opaque single-shot prompting, improving traceability (`integuru/graph_builder.py:22-53`).
  - Combines symbolic dependency graphing (NetworkX) with LLM extraction decisions, a pragmatic neuro-symbolic pattern (`integuru/models/DAGManager.py:6-60`, `integuru/agent.py:292-403`).
  - Structured function-calling schemas constrain several LLM outputs (`integuru/agent.py:42-55`, `86-107`, `162-185`).
  - End-to-end path from traffic capture to executable integration artifact is operationally complete (`create_har.py:6-34`, `integuru/util/print.py:444-451`).

- **Limitations:**
  - Not truly multi-agent at runtime; it is one agent pipeline with staged methods, so role diversity is limited.
  - Heavy dependence on prompt heuristics and brittle string matching in responses (`integuru/agent.py:329-341`), which may fail on noisy/encoded payloads.
  - `Request.to_curl_command` mutates `self.url` when query params are present, risking repeated side effects (`integuru/models/request.py:19-22`, `53-56`).
  - Limited automated validation of generated code; tests mostly mock individual methods (`tests/test_integration_agent.py:22-69`).
  - Model fallback logic is narrow/OpenAI-specific (`integuru/util/LLM.py:5-35`), reducing portability.

- **Research relevance:**
  - Useful example of LLM-guided API reverse engineering with explicit intermediate structure (dependency DAG).
  - Demonstrates practical LangGraph loop orchestration for iterative dependency resolution in real-world traces.
  - Illustrates hybrid symbolic graph construction + generative synthesis for integration automation tasks.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
