---
repo_name: rohitg00/awesome-ai-apps
url: "https://github.com/rohitg00/awesome-ai-apps"
stars: 757
forks: 158
contributors_count: 3
last_commit_date: "2026-02-10T23:20:36+00:00"
primary_use_case: Code Generation
user_tier: Niche
total_score: 4
architecture_labels: [LangChain, CrewAI]
use_case_labels: [Workflow Automation, Code Generation, RAG + Agents]
generated_at: "2026-04-27T15:30:09.000601+00:00"
model: auto
duration_s: 78.0
clone_size_kb: 193280
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`rohitg00/awesome-ai-apps` is a monorepo of many small, runnable AI demos rather than one unified agent system. A user typically runs an individual app (mostly Streamlit or React/Vite) from a subfolder, provides an API key, and gets task-specific outputs like chat responses, content plans, competitor analyses, or video-derived blog drafts (`Readme.md:9-16`, `starter-agents/openai-chat-assistant/app.py:58-140`). The repository spans starter assistants, RAG pipelines, multimodal processing, and one explicit multi-agent team example. In practice, it solves “how do I scaffold a practical AI workflow quickly” more than “how do I run one production-grade platform.”

## 2. Agent Framework & Architecture

The only confirmed runtime multi-agent framework is **CrewAI**, used in `multi-agent-teams/content-creation-team/app.py` (`from crewai import Agent, Task, Crew, Process` at `app.py:10`). That app also uses **LangChain**’s legacy `OpenAI` LLM wrapper as the model backend for each CrewAI agent (`app.py:11`, `app.py:32-36`).

Other subprojects use **LangChain** for RAG-style single-agent QA chains (e.g., `RetrievalQA`, `Chroma`, `OpenAIEmbeddings` in `rag-applications/content-management-system/app.py:10-15` and `rag-applications/competitive-intelligence-platform/app.py:10-14`) and Google Gemini SDK calls in TS services (e.g., `advanced-agents/blog-video-writer/services/blogWriterService.ts:29-31`, `rag-applications/contextual-video-rag/services/ragService.ts:47-55`). Those are usually multi-step pipelines but not true independent agent objects with delegated coordination.

High-level architecture is therefore **portfolio-style**: each folder is an isolated app with its own orchestration logic. “Intelligence” mostly lives in long prompt templates embedded directly inside methods (`content-management-system/app.py:137-182`, `competitive-intelligence-platform/app.py:136-181`) and in staged service methods for React apps (`blogWriterService.ts:33-55`).

## 3. Orchestration Pattern

Closest overall pattern: **other (collection of per-app orchestrators)**. Within the true MAS example, the orchestration is **sequential**.

The CrewAI team is explicitly sequential:

```python
226:245:multi-agent-teams/content-creation-team/app.py
self.crew = Crew(
    agents=[
        self.research_agent, self.writer_agent, self.editor_agent,
        self.seo_agent, self.social_media_agent, self.analytics_agent
    ],
    tasks=[research_task, writing_task, editing_task, seo_task, social_media_task, analytics_task],
    process=Process.sequential,
    verbose=True
)
```

Control is kicked off once, then flows task-by-task through assigned roles:

```python
247:253:multi-agent-teams/content-creation-team/app.py
result = self.crew.kickoff()

project_entry = {
    'id': len(self.projects) + 1,
    'timestamp': datetime.now().isoformat(),
    'details': project_details,
    'result': result,
}
```

By contrast, many “agentic” TS apps are linear staged function chains in one service class (single model instance), e.g., analyze → plan → research → draft → edit (`advanced-agents/blog-video-writer/services/blogWriterService.ts:41-55`).

## 4. Tools & External Integrations

- **LLM APIs**
  - OpenAI via LangChain/OpenAI SDK (`multi-agent-teams/content-creation-team/app.py:32-36`, `starter-agents/openai-chat-assistant/app.py:30-41`).
  - Google Gemini via `@google/generative-ai` and `@google/genai` (`advanced-agents/blog-video-writer/services/blogWriterService.ts:1-31`, `rag-applications/contextual-video-rag/services/ragService.ts:1-10`).
- **Agent framework**
  - CrewAI agents/tasks/crew orchestration (`multi-agent-teams/content-creation-team/app.py:10`, `app.py:112-245`).
- **RAG stack**
  - Chroma vector store + OpenAI embeddings + `RetrievalQA` in LangChain (`rag-applications/content-management-system/app.py:47-62`, `rag-applications/competitive-intelligence-platform/app.py:46-61`).
- **UI / workflow frontends**
  - Streamlit for Python apps (`.../app.py` files across starter/multi-agent/rag folders).
  - React/Vite frontends invoking service-layer orchestration (`advanced-agents/blog-video-writer/App.tsx:27-85`).
- **No explicit external execution tools**
  - No MCP server wiring, browser automation frameworks, shell execution agents, or database backends beyond local Chroma persistence are visible in inspected code.

## 5. Notable Code Walkthrough

- `multi-agent-teams/content-creation-team/app.py:22-263` - Core true multi-agent implementation: defines six CrewAI agents, maps six role-specific tasks, and executes them via one `Crew` with `Process.sequential`.
- `multi-agent-teams/content-creation-team/app.py:109-224` - Contains the substantive prompt/task contracts for each role (research, writing, editing, SEO, social, analytics), which is where most behavior is actually specified.
- `advanced-agents/blog-video-writer/services/blogWriterService.ts:33-79` - Implements a staged “agent-like” pipeline over a single Gemini model client; useful example of pseudo-agent workflow without a formal MAS framework.
- `rag-applications/content-management-system/app.py:39-64` - Shows LangChain RAG wiring (`OpenAIEmbeddings` + `Chroma` + `RetrievalQA`) for content operations; demonstrates retrieval-backed workflow automation.
- `starter-agents/openai-chat-assistant/app.py:28-43` - Baseline single-agent chat app using streaming OpenAI completions, helpful contrast with the multi-agent team example.

## 6. Use-Case Mapping

The assigned primary use case (**Code Generation**) does **not** match the observed center of gravity. Most runnable apps automate business/content workflows (content ops, market intelligence, video analysis, chat assistance), and even the multi-agent example is a content production pipeline, not a coding pipeline (`multi-agent-teams/content-creation-team/app.py:112-245`).  
A better repo-level label is **Workflow Automation**. There are code-adjacent capabilities (e.g., generic chat assistant could write code), but no dedicated software-engineering multi-agent codegen loop (e.g., planner/coder/tester/refiner over repositories) was found.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad, runnable coverage of agentic patterns across multiple stacks (Streamlit Python + React TS).
  - Includes one concrete CrewAI multi-agent coordination example with explicit role/task mapping.
  - Prompts and workflow steps are transparent and easy to inspect/modify for experimentation.
  - Quick-start UX is practical for demos (API key in sidebar, immediate execution paths).

- **Limitations:**
  - Repo is heterogeneous and loosely coupled; no shared core architecture across apps.
  - Many “agent” apps are sequential single-model pipelines rather than true coordinated MAS.
  - Heavy reliance on hardcoded long prompts; limited modular prompt/version management.
  - Minimal automated testing and limited robustness around parsing/validation in several services.

- **Research relevance:**
  - Evidence of how open-source projects operationalize “agent” terminology across true MAS and pseudo-agent pipelines.
  - Example of role-specialized sequential orchestration in CrewAI for task decomposition.
  - Useful for studying prompt-centric workflow design tradeoffs in low-infrastructure agent apps.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
