---
repo_name: Sri-Krishna-V/awesome-adk-agents
url: "https://github.com/Sri-Krishna-V/awesome-adk-agents"
stars: 286
forks: 43
contributors_count: 3
last_commit_date: "2026-03-02T20:34:22+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 3
architecture_labels: [LangGraph, LangChain, AutoGen, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T16:28:38.825989+00:00"
model: auto
duration_s: 72.5
clone_size_kb: 8262
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`Sri-Krishna-V/awesome-adk-agents` is primarily a hybrid repository: an “awesome list” plus a `my-adk-agents/` folder containing several runnable Google ADK agent projects. A user can run individual agents (for example, the education advisor, academic research assistant, interview simulator, or learning-content system) rather than one unified app. In practice, these apps take user goals (e.g., research topic, education planning request, interview prep) and produce structured outputs through coordinated sub-agents and tools. So the repo solves discovery *and* provides concrete ADK implementations, especially for workflow-oriented, domain-specific assistants.

## 2. Agent Framework & Architecture

The implemented framework is **Google ADK** (not LangGraph/LangChain/CrewAI/AutoGen in this codebase). This is verified by imports such as `google.adk.agents`, `google.adk.agents.llm_agent`, `google.adk.runners`, and ADK tool wrappers (e.g., `AgentTool`, MCP toolsets) in files like `my-adk-agents/education-path-advisor/education_advisor/agent.py:3-26`, `my-adk-agents/learning-content-system(WIP)/main.py:10-14`, and `my-adk-agents/academic-research-assistant/academic_research_assistant/agent.py:33-52`.

Architecture is project-centric: each subproject defines a `root_agent`, then composes specialized agents either as sub-agents or tools. For example, `education-path-advisor` uses a coordinator `LlmAgent` that delegates via `AgentTool` to four specialist agents (`data`, `pathway`, `implementation`, `risk`) (`.../education_advisor/agent.py:15-29`). `academic-research-assistant` defines a root agent with sub-agents (`profiler`, `searcher`, `comparison`) and the comparison stage itself is a nested `SequentialAgent` + `LoopAgent` (`.../academic_research_assistant/agent.py:42-54`, `.../comparison_root_agent/agent.py:24-38`).

The “intelligence” lives mostly in role-specific prompts and ADK composition primitives (Sequential/Parallel/Loop/Sub-agent delegation), with external tools providing grounding (Google Search, SerpAPI, Selenium scraping, MCP servers, calendar APIs).

## 3. Orchestration Pattern

Closest match: **hierarchical + sequential workflow orchestration** (with loop/parallel subpatterns in some apps).

In `education-path-advisor`, a coordinator agent calls specialist agents as tools (manager-worker pattern):

`my-adk-agents/education-path-advisor/education_advisor/agent.py:15-26`
```python
education_coordinator = LlmAgent(
    name="education_coordinator",
    ...
    tools=[
        AgentTool(agent=data_analyst_agent),
        AgentTool(agent=implementation_analyst_agent),
        AgentTool(agent=pathway_analyst_agent),
        AgentTool(agent=risk_analyst_agent),
    ],
)
```

In `learning-content-system(WIP)`, control is explicitly composed as sequential → parallel → loop:

`my-adk-agents/learning-content-system(WIP)/main.py:105-113`
```python
root_agent = SequentialAgent(
    name="LearningContentCreationSystem",
    sub_agents=[
        content_processing_pipeline,
        multi_format_generator,
        quality_refinement_loop
    ],
)
```

`academic-research-assistant` further confirms nested orchestration with iterative critique/refinement loops (`.../comparison_root_agent/agent.py:24-38`).

## 4. Tools & External Integrations

- **Google ADK built-in search tool** (`google_search`) used by education data analyst  
  - Wiring: `my-adk-agents/education-path-advisor/education_advisor/sub_agents/data_analyst/agent.py:3-16`
- **MCP tool servers (remote + stdio via `npx`)** for HuggingFace search, image generation, TTS, sentiment/general tools  
  - Wiring: `my-adk-agents/learning-content-system(WIP)/tools/mcp_config.py:11-87`
- **Google Calendar API** (schedule/list/update/cancel interviews) via custom calendar utilities  
  - Wiring: `my-adk-agents/job-interview-agent/app/interview_agent/tools/calendar_tools.py:16-499`
- **SerpAPI (Google Scholar)** for profile and paper retrieval fallback/search  
  - Wiring: `my-adk-agents/academic-research-assistant/academic_research_assistant/tools/serpapi_tools.py:24-217`
- **Selenium browser automation** for page navigation/screenshot/page interaction in research searcher module  
  - Wiring: `my-adk-agents/academic-research-assistant/academic_research_assistant/sub_agents/searcher_agent/agent.py:25-389`
- **Code execution tool** (`built_in_code_execution`) in the data-analyst/code assistant agent  
  - Wiring: `my-adk-agents/data-analyst/data_analyst_agent/agent.py:1-11`

## 5. Notable Code Walkthrough

- `my-adk-agents/learning-content-system(WIP)/main.py:69-113` - Defines the clearest end-to-end multi-agent topology: a sequential content pipeline, parallel format generation, and iterative quality loop, then exposes a runnable async orchestration function.
- `my-adk-agents/education-path-advisor/education_advisor/agent.py:15-29` - Shows manager-style delegation using `AgentTool` wrapping four specialist ADK agents; this is a compact canonical ADK multi-agent composition.
- `my-adk-agents/academic-research-assistant/academic_research_assistant/sub_agents/comparison_root_agent/agent.py:24-38` - Implements refinement loop (`LoopAgent`) plus final formatting (`SequentialAgent`), demonstrating iterative agent collaboration rather than one-shot generation.
- `my-adk-agents/learning-content-system(WIP)/tools/mcp_config.py:11-87` - Central integration point for MCP servers, showing how external model/tool providers are exposed into the agent runtime.
- `my-adk-agents/job-interview-agent/app/interview_agent/tools/calendar_tools.py:16-145` - Representative production-style tool function that converts natural-language scheduling intents into concrete Google Calendar events with timezone/reminder handling.

## 6. Use-Case Mapping

The upstream assigned primary use case (**Code Generation**) is only partially reflected. There is one code-focused agent (`data-analyst` with “senior software engineer” instruction and code execution tool in `.../data_analyst_agent/agent.py:5-11`), but most substantial implementations center on orchestrating business/education/research/interview workflows using multiple agents and tools.

A better overall classification for this repository is **Workflow Automation**: most featured runnable projects automate multi-step domain workflows (planning, research synthesis, scheduling, content assembly/refinement) through coordinated agents and tool calls.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Demonstrates multiple ADK orchestration primitives in real code (`SequentialAgent`, `ParallelAgent`, `LoopAgent`, `AgentTool`).
  - Includes practical tool integration patterns (MCP, SerpAPI, Selenium, Google Calendar).
  - Uses role-specialized sub-agents with explicit decomposition, useful for studying task partitioning.
  - Contains runnable project examples (not just conceptual architecture notes).
  - Covers diverse domains, showing portability of orchestration patterns.

- **Limitations:**
  - Repository is not a single cohesive system; it is a mixed awesome-list + sample collection, so architecture is fragmented.
  - Quality and maturity vary by subproject (e.g., one marked WIP, some minimal test coverage per project).
  - Some integrations depend on external credentials/services, reducing out-of-the-box reproducibility.
  - No unified benchmarking/evaluation layer across all included agents.
  - Limited evidence of cross-project shared abstractions; patterns are repeated in project-local ways.

- **Research relevance:**
  - Good evidence of **practical multi-agent workflow composition** in ADK rather than toy single-agent chatbots.
  - Useful for comparative analysis of orchestration styles (hierarchical, sequential, loop, parallel) in one repository.
  - Illustrates tool-grounded agent systems with heterogeneous integrations (API + browser + MCP).
  - Supports case-study research on domain-specific agent teams (education guidance, academic research, interview automation).

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
