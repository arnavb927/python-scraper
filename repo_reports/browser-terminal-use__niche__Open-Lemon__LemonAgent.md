---
repo_name: Open-Lemon/LemonAgent
url: "https://github.com/Open-Lemon/LemonAgent"
stars: 52
forks: 6
contributors_count: 3
last_commit_date: "2026-02-10T02:54:54+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Niche
total_score: 3
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T17:11:57.745504+00:00"
model: auto
duration_s: 69.2
clone_size_kb: 2941
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

This repository currently appears to be a documentation-only placeholder for LemonAgent rather than a runnable codebase. A user cloning this repo gets architecture claims, benchmark charts, environment-variable guidance, and intended commands, but no `src/` or `benchmark/` implementation files to execute (`README.md:50-111`, `README.md:113-115`). The README describes LemonAgent as a multi-agent framework for GAIA-style complex task solving with planner-executor-memory coordination and adaptive scheduling (`README.md:14-18`, `README.md:25-35`). In practice, this clone provides project positioning and setup intent, not the actual agent runtime.

## 2. Agent Framework & Architecture

No concrete agent framework is verifiable from source code because there are no runtime modules or framework imports in this repository (only `README.md`, `README_zh.md`, and SVG assets). So LangGraph/LangChain/CrewAI/AutoGen usage cannot be confirmed from implementation.

From the docs, the claimed architecture is a custom multi-agent system with a `Planner–Executor–Memory` pattern, adaptive sub-agent scheduling, and high-concurrency DAG execution (`README.md:14-18`, `README.md:27`). The described “main agent” handles intent recognition, memory retrieval, task decomposition, routing, verification, and summarization, then delegates to sub-agent groups based on difficulty (`README.md:26-27`). “AgentCortex” is presented as the design framework/paradigm, but this is descriptive text only in the README, not inspectable executable code (`README.md:28-31`).

## 3. Orchestration Pattern

Closest match: **hierarchical (manager-worker)** with a **DAG-style executor** (documentation-claimed, not code-verified).

Control flow is described as:
1) main agent interprets and plans,  
2) routes decomposed steps to sub-agent groups,  
3) executes steps in parallel DAG form,  
4) writes back learned skill memory.

Example excerpt 1 (`README.md:26-27`):
> “main agent decomposes the task ... plans executable steps ... configures different sub-agent groups ... high-concurrency DAG execution among the sub-agents.”

Example excerpt 2 (`README.md:33-35`):
> “After the task is completed, the main agent extracts valuable information ... writes it back to Skill Memory ... All agents invoke tools via the MCP protocol.”

## 4. Tools & External Integrations

Because source files are absent, integrations are only identifiable from README configuration and run instructions:

- **MCP tool server**: claimed unified tool invocation layer via MCP; run command points to `src.mcp_tools.mcp_tool_server` (`README.md:35`, `README.md:98-103`).
- **Browser/web automation stack**: `crawl4ai` setup and Playwright browser install (`README.md:65-71`).
- **Search/scraping APIs**: `SERPER_API_KEY`, `JINA_API_KEY` (`README.md:77-80`).
- **Vision/LLM APIs**: Gemini and OpenAI keys/base URLs (`README.md:82-89`).
- **Data persistence**: MongoDB environment variable for memory storage (`README.md:89-90`).
- **Sandbox/compute integration hint**: `E2B_API_KEY` noted as minimal startup dependency (`README.md:74-76`).
- **Media/tooling dependency**: `ffmpeg` installation (`README.md:62-64`).

No concrete API client code, tool adapters, or MCP server implementation is present in this clone.

## 5. Notable Code Walkthrough

- `README.md:14-18` — Core architecture claim (Planner–Executor–Memory, adaptive scheduling, layered memory), which is the primary technical description available.
- `README.md:25-35` — Most detailed operational narrative of agent roles (main agent, sub-agent routing, DAG execution, memory writeback, MCP tool layer).
- `README.md:50-71` — Intended environment/bootstrap dependencies (`uv`, Node, crawl4ai, Playwright, ffmpeg), useful for inferring planned capabilities.
- `README.md:72-111` — Intended runtime surface (`src.mcp_tools.mcp_tool_server`, `benchmark/run_gaia_multi.py`) but referenced paths are not included in this repo snapshot.
- `README.md:113-115` — Explicit TODO indicates code is still under internal review and “coming soon,” explaining absence of implementation.

## 6. Use-Case Mapping

The assigned primary use case **Browser / Terminal Use** is only partially supported by documentation evidence (Playwright + crawl4ai + MCP tools). However, the dominant described objective is broader **workflow automation for GAIA-style multi-step reasoning tasks** with task decomposition, sub-agent scheduling, and memory reuse (`README.md:14-18`, `README.md:26-27`). Given the current repository contents (docs only, no runnable browser/terminal agent code), the better category is **Workflow Automation** at the intent level, but implementation evidence is not available.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear conceptual decomposition into planner/executor/memory and adaptive scheduling (`README.md:14-18`).
  - Explicit claim of hierarchical multi-agent delegation plus DAG concurrency (`README.md:26-27`).
  - Integrated memory lifecycle concept (retrieve before task, write back after completion) (`README.md:26`, `README.md:33`).
  - Tooling philosophy is unified (MCP protocol for all agents) (`README.md:35`).

- **Limitations:**
  - No executable source code to validate architecture, agent interactions, or benchmark claims.
  - Referenced modules/scripts (`src/...`, `benchmark/...`) are missing from repository contents.
  - No tests, configs, or dependency lockfiles to reproduce results.
  - No observable prompt templates, planner logic, routing policy, or failure handling implementation.

- **Research relevance:**
  - Useful as an example of **claimed** industrial MAS design goals (cost-aware scheduling, memory, tool use) in project documentation.
  - Not suitable as direct empirical evidence for implementation-level MAS techniques, since runtime code is unavailable.
  - Can be cited as a case of “announcement-stage” open-source where architecture is documented ahead of code release.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
