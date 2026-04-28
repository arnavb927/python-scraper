---
repo_name: splx-ai/agentic-radar
url: "https://github.com/splx-ai/agentic-radar"
stars: 953
forks: 127
contributors_count: 8
last_commit_date: "2025-11-27T15:28:30+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 6
architecture_labels: [LangGraph, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, Browser / Terminal Use]
generated_at: "2026-04-27T12:59:44.165671+00:00"
model: auto
duration_s: 81.0
clone_size_kb: 10149
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`agentic-radar` is a Python CLI security scanner for agentic workflow codebases, not an agent runtime itself. A user runs commands like `agentic-radar scan <framework> -i <project_dir> -o report.html`, and the tool statically analyzes source files (Python/JSON/notebooks) to reconstruct workflow graphs, tools, MCP servers, and potential vulnerability mappings (`agentic_radar/cli.py:62-195`). It supports multiple target ecosystems (LangGraph, CrewAI, OpenAI Agents, AutoGen AgentChat, n8n) through framework-specific analyzers (`agentic_radar/analysis/__init__.py:1-15`). The output is a generated HTML (or JSON graph) security report with graph visualization and vulnerability tables (`agentic_radar/report/report.py:55-105`).

## 2. Agent Framework & Architecture

This repo does **not** primarily use LangGraph/CrewAI/AutoGen as its own runtime orchestration framework; instead, it uses **custom static-analysis architecture** over Python AST/JSON plus a Typer CLI. Confirming imports: `typer`, `ast`, `pydantic`, `jinja2`, and framework-specific parser modules are central (`agentic_radar/cli.py:9-35`, `agentic_radar/analysis/langgraph/graph.py:1-7`).  

High-level architecture is adapter-based: the CLI chooses one analyzer class (`LangGraphAnalyzer`, `CrewAIAnalyzer`, `OpenAIAgentsAnalyzer`, `AutogenAgentChatAnalyzer`, `N8nAnalyzer`) and calls `analyze(root_directory)` (`agentic_radar/cli.py:111-133`). Each analyzer parses target code into a normalized internal `GraphDefinition` schema of nodes/edges/agents/tools (`agentic_radar/graph.py:37-75`). Then optional steps map vulnerabilities, harden prompts with OpenAI, and render HTML (`agentic_radar/cli.py:161-194`).

“Intelligence” here lives mainly in handcrafted parsing and conversion logic (AST visitors, graph converters, process inference), not in an LLM planner/router. Example: LangGraph analyzer resolves `add_node`, `add_edge`, `add_conditional_edges` from AST call records (`agentic_radar/analysis/langgraph/graph.py:136-177, 740-812`), while CrewAI infers agent connectivity from task/process metadata (`agentic_radar/analysis/crewai/crew_process.py:10-51`).

## 3. Orchestration Pattern

Closest match: **other (adapter-based sequential analysis pipeline)**, with light **hierarchical dispatch** (CLI manager -> framework analyzer). It is not a runtime multi-agent collaboration pattern.

Control flow excerpt 1 (`agentic_radar/cli.py:111-127`):
> if framework == AgenticFramework.langgraph: analyzer = LangGraphAnalyzer()  
> elif framework == AgenticFramework.crewai: analyzer = CrewAIAnalyzer()  
> ...  
> analyze_and_generate_report(..., analyzer=analyzer, ...)

Control flow excerpt 2 (`agentic_radar/cli.py:145-163`):
> graph = analyzer.analyze(input_directory)  
> sanitize_graph(graph)  
> map_vulnerabilities(graph)

Inside analyzers, flow remains pipeline-style: parse artifacts -> infer links -> convert to normalized graph. For CrewAI, this is explicit (`agentic_radar/analysis/crewai/analyze.py:50-72`).

## 4. Tools & External Integrations

- **Target framework code parsing (LangGraph/CrewAI/OpenAI Agents/AutoGen/n8n):** wired via analyzer adapters in `agentic_radar/analysis/*/analyze.py`.
- **Python AST parsing:** core mechanism for Python frameworks (`agentic_radar/analysis/langgraph/graph.py`, `agentic_radar/analysis/autogen/agentchat/analyze.py`, `agentic_radar/analysis/openai_agents/parsing/*.py`).
- **MCP server detection:** parses OpenAI Agents and other framework code for MCP constructors/config (`agentic_radar/analysis/openai_agents/parsing/mcp.py:9-27, 92-242`; also framework-specific MCP parsers).
- **OpenAI/Azure OpenAI API (optional):** prompt hardening step uses `OpenAI`/`AzureOpenAI` chat completions (`agentic_radar/prompt_hardening/steps/openai_generator.py:3-79`).
- **Runtime test harness for OpenAI Agents workflows:** monkey-patches `agents.Agent` and `agents.Runner` to register/test workflows (`agentic_radar/test/launchers/openai_agents_launcher.py:20-95`).
- **HTML report generation:** `jinja2` + graph rendering and static assets (`agentic_radar/report/report.py:55-105`).
- **No browser automation / terminal-control agent tools in core scanner runtime:** no Playwright/Browserbase-style control in scanner engine.

## 5. Notable Code Walkthrough

- `agentic_radar/cli.py:62-195` - Main entrypoint for `scan` and report pipeline; selects framework analyzer, runs analysis, maps vulnerabilities, optionally hardens prompts, and emits HTML/JSON.
- `agentic_radar/analysis/langgraph/graph.py:8-177, 667-814` - Most representative parser logic: AST visitor tracks graph instance calls (`add_node`, `add_edge`, `add_conditional_edges`) and reconstructs workflow edges.
- `agentic_radar/analysis/crewai/crew_process.py:10-140` - Infers inter-agent links from CrewAI process types (`sequential`, `hierarchical`), translating task ordering into explicit graph edges.
- `agentic_radar/analysis/openai_agents/graph.py:17-113` - Converts parsed agent assignments into normalized graph with tool-call, handoff, guardrail, and MCP relationships.
- `agentic_radar/report/report.py:55-105` - Final rendering layer that transforms normalized graph data into shareable HTML report with counts, vulnerabilities, and dependency assets.

## 6. Use-Case Mapping

The assigned use case **Browser / Terminal Use** looks inaccurate for this repository’s core behavior. The project is best categorized as **Workflow Automation**: it automates static security analysis of agentic codebases, graph extraction, vulnerability mapping, and reporting (`agentic_radar/cli.py:62-195`, `agentic_radar/analysis/*`, `agentic_radar/report/report.py:55-105`).  

There is some terminal-oriented execution (CLI command invocation) and optional runtime testing launcher, but no primary in-repo browser-driving or terminal-manipulating LLM agent loop.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Multi-framework adapter design with a common graph schema (`agentic_radar/analysis/__init__.py:1-15`, `agentic_radar/graph.py:69-75`).
  - Practical AST-based reconstruction of orchestration edges (including conditional branches) for LangGraph (`agentic_radar/analysis/langgraph/graph.py:740-792`).
  - Security-focused output pipeline (tool/MCP detection + vulnerability mapping + report generation) (`agentic_radar/cli.py:161-194`).
  - Includes both static scan and optional runtime testing workflow path (`agentic_radar/cli.py:197-255`).
  - Explicit handling of MCP integration visibility across frameworks (`agentic_radar/analysis/openai_agents/parsing/mcp.py:92-242`).

- **Limitations:**
  - No native multi-agent runtime implemented; it analyzes other projects rather than showcasing internal agent collaboration.
  - Parsing is heuristic and can miss dynamic/metaprogrammed patterns (heavy reliance on static AST extraction).
  - Prompt hardening and some advanced features depend on external OpenAI/Azure APIs (`agentic_radar/prompt_hardening/steps/openai_generator.py:60-79`).
  - Framework support for runtime `test` is currently limited (notably OpenAI Agents in CLI branching) (`agentic_radar/cli.py:238-252`).
  - Vulnerability/tool categorization quality depends on predefined mappings and extraction completeness.

- **Research relevance:**
  - Useful evidence for **security analysis tooling around agentic ecosystems**, especially static graph extraction from framework code.
  - Demonstrates a **cross-framework normalization strategy** for comparing different agent orchestration libraries.
  - Illustrates practical **MCP/tool surface auditing** in agent workflows.
  - Relevant to studies on **agent observability and governance tooling**, more than to studies of emergent multi-agent coordination algorithms.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
