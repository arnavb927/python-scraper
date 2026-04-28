---
repo_name: algorithmicsuperintelligence/optillm
url: "https://github.com/algorithmicsuperintelligence/optillm"
stars: 3437
forks: 266
contributors_count: 17
last_commit_date: "2026-03-19T02:43:58+00:00"
primary_use_case: Simulation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Simulation]
generated_at: "2026-04-27T13:45:15.103375+00:00"
model: auto
duration_s: 64.8
clone_size_kb: 5124
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`optillm` is an OpenAI-compatible inference proxy that users run as a Flask server (`python optillm.py`) and call via `/v1/chat/completions` to apply reasoning-time optimization methods before returning a normal chat-completions response. Instead of being a single fixed agent app, it routes each request through selectable “approaches” (e.g., `moa`, `mars`, `mcts`, plugins) based on model prefix, request fields, or prompt tags. The main value is improved answer quality/robustness through orchestration patterns like multi-sample critique/synthesis, multi-agent generation+verification, and iterative research loops. Users effectively get drop-in API compatibility plus advanced agentic inference workflows without changing their client stack much.

## 2. Agent Framework & Architecture

This repo uses **custom orchestration**, not LangGraph/LangChain/AutoGen/CrewAI as a runtime dependency. The primary control plane is `optillm/server.py`, which parses approach selection and dispatches to built-in modules or plugin `run()` functions (`optillm/server.py:396-483`, `optillm/server.py:697-849`). The architecture is “proxy + approach modules + plugin system,” where each approach encapsulates its own prompting/orchestration logic.

Two concrete multi-agent implementations are present. First, `moa` runs a multi-candidate generation and critique pipeline, then synthesizes a final answer (`optillm/moa.py:21-33`, `optillm/moa.py:117-188`). Second, `mars` is a fuller coordinated multi-agent system with multiple `MARSAgent` instances, parallel exploration, verification, iterative improvement, optional aggregation/strategy sharing, and final synthesis (`optillm/mars/mars.py:156-264`). The “intelligence” is primarily in prompt templates and orchestration code across `optillm/mars/*` and plugin modules, rather than an external agent framework graph DSL.

## 3. Orchestration Pattern

Closest match: **hierarchical manager-worker**, with parallel sub-phases (and optional pipeline/parallel composition at the proxy level).  
- `server.py` acts as top-level orchestrator/manager choosing approach and composition mode (`SINGLE`, `AND`, `OR`) (`optillm/server.py:486-533`).  
- In `mars`, a coordinator manages worker agents plus verifier/aggregator components (`optillm/mars/mars.py:156-239`).

Code excerpt 1 (manager dispatch + composition mode):
```396:424:optillm/server.py
def execute_single_approach(...):
    ...
    elif approach == 'moa':
        return mixture_of_agents(...)
    ...
    elif approach == 'mars':
        return multi_agent_reasoning_system(...)

def execute_combined_approaches(...):
    for approach in approaches:
        response, tokens = execute_single_approach(...)
```

Code excerpt 2 (MARS manager controlling multi-agent lifecycle):
```156:176:optillm/mars/mars.py
agents = []
for i in range(config['num_agents']):
    agent = MARSAgent(i, client, model, config)
    agents.append(agent)

with ThreadPoolExecutor(max_workers=max_workers) as executor:
    exploration_tokens = await _run_exploration_phase_parallel(
        agents, workspace, request_id, executor
    )
```

## 4. Tools & External Integrations

- **LLM provider APIs** (OpenAI, Azure OpenAI, Cerebras, LiteLLM fallback) wired in `get_config()` and used throughout approaches (`optillm/server.py:62-130`).
- **MCP servers/tools/resources/prompts** via Model Context Protocol (`mcp` Python SDK), including stdio/SSE/WebSocket transports and model tool-calling loop (`optillm/plugins/mcp_plugin.py:22-27`, `optillm/plugins/mcp_plugin.py:472-499`, `optillm/plugins/mcp_plugin.py:866-957`).
- **Web search automation** through Selenium + ChromeDriver for Google results (`optillm/plugins/web_search_plugin.py:6-16`, `optillm/plugins/web_search_plugin.py:562-625`).
- **URL content fetching/parsing** through `requests` + BeautifulSoup (`optillm/plugins/readurls_plugin.py:27-55`, `optillm/plugins/readurls_plugin.py:115-125`).
- **Code execution tool** by executing generated Python in Jupyter kernel (`nbconvert.ExecutePreprocessor`) (`optillm/plugins/executecode_plugin.py:25-47`, `optillm/plugins/executecode_plugin.py:67-116`).
- **Model routing classifier** using HuggingFace Transformers + safetensors to choose inference approach (`optillm/plugins/router_plugin.py:30-63`, `optillm/plugins/router_plugin.py:92-141`).
- **Deep research pipeline** composes `web_search` + `readurls` tools and iterative synthesis (`optillm/plugins/deep_research/research_engine.py:17-19`, `optillm/plugins/deep_research/research_engine.py:967-1099`).

## 5. Notable Code Walkthrough

- `optillm/server.py:287-395, 396-533, 697-941`  
  Central API proxy and orchestrator: loads plugin approaches dynamically, parses approach composition (`&`/`|`), dispatches execution, and formats OpenAI-compatible responses.

- `optillm/moa.py:21-33, 117-188, 192-227`  
  Implements Mixture-of-Agents style workflow: generate multiple candidate completions, critique them, then synthesize a final optimized response.

- `optillm/mars/mars.py:76-99, 156-264, 325-377`  
  Core multi-agent reasoning loop: initializes multiple agents, runs exploration in parallel, verifies/iteratively improves solutions, and performs final synthesis.

- `optillm/mars/agent.py:43-83, 153-212, 227-277`  
  Defines per-agent behaviors (generate, verify, improve) and reasoning-effort control; this is where worker-agent prompting and API calls happen.

- `optillm/plugins/deep_research/research_engine.py:967-1099, 1108-1229`  
  Iterative “deep research” denoising workflow combining decomposition, retrieval, gap-targeted search, synthesis, citation validation, and report finalization.

## 6. Use-Case Mapping

The assigned label **Simulation** looks inaccurate for the repository as a whole. The core product is an **inference workflow orchestrator/proxy** that chains multiple reasoning strategies and plugins around LLM API calls (`optillm/server.py:697-849`), with multi-stage pipelines like `moa`, `mars`, and deep research loops. While `mcts` and some search-style algorithms have simulation-like internals, the dominant practical use is automating response optimization workflows across tools/providers. A better category is **Workflow Automation** (with secondary overlap into RAG + Agents via deep research).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong modular architecture: approach dispatch + plugin loading enables rapid extension (`optillm/server.py:287-341`).
  - Real runtime multi-agent coordination in `mars` (parallel generation, verification, improvement, synthesis) (`optillm/mars/mars.py:156-264`).
  - Rich integration surface (MCP, browser search, URL ingestion, code execution) for agent tool use.
  - OpenAI-compatible API wrapper lowers adoption friction for existing clients.
  - Supports sequential and parallel composition of strategies at request time (`optillm/server.py:486-533`).

- **Limitations:**
  - Heavy reliance on prompt-engineered control; limited formal guarantees or learned coordination policies.
  - `deep_research` includes explicitly “not yet implemented” paper features (component evolution used for tracking but not behavior control) (`optillm/plugins/deep_research/research_engine.py:286-289`, `944-951`).
  - Tooling robustness depends on brittle external surfaces (Google DOM/CAPTCHA, website parsing variability).
  - No unified agent state graph abstraction; orchestration logic is spread across many modules, increasing maintenance complexity.
  - Some modules use synchronous calls wrapped in thread pools, which may be less efficient than native async end-to-end.

- **Research relevance:**
  - Useful evidence of **production-oriented MAS orchestration** in an API proxy context (manager-worker + parallel phases).
  - Illustrates **hybrid reasoning pipelines** combining multi-agent deliberation, verification, and synthesis.
  - Demonstrates practical **tool-augmented agent workflows** (MCP/tool calling + web retrieval + code execution).
  - Shows tradeoffs between extensibility and formal coordination rigor in real-world agent systems.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
