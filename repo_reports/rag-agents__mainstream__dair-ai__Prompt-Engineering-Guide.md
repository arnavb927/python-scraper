---
repo_name: dair-ai/Prompt-Engineering-Guide
url: "https://github.com/dair-ai/Prompt-Engineering-Guide"
stars: 73702
forks: 7950
contributors_count: 212
last_commit_date: "2026-03-11T20:07:25+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 7
architecture_labels: [Custom/Other]
use_case_labels: [RAG + Agents]
generated_at: "2026-04-27T10:09:11.557604+00:00"
model: auto
duration_s: 101.5
clone_size_kb: 150506
uses_mas: no
final_use_case: None
---
## 1. Overview

`dair-ai/Prompt-Engineering-Guide` is primarily a Next.js + Nextra documentation site for prompt engineering, RAG, and agentic design patterns, with supporting notebooks for hands-on examples. A user typically runs `pnpm dev` to browse the guide locally, while API routes mostly serve/clean content files for the docs UI (`package.json:5-8`, `pages/api/getPageContent.ts:3-57`). The repository’s core deliverable is educational content (MDX + notebooks), not a deployable multi-agent runtime service. What users get is a knowledge base with runnable tutorial snippets (e.g., LangChain ReAct, OpenAI function calling, RAG with Chroma) rather than a production agent platform.

## 2. Agent Framework & Architecture

The **runtime web app framework** is Next.js/Nextra, not an agent framework (`next.config.js:1-26`, `pages/_app.tsx:8-27`).  
Actual LLM-agent code appears in **tutorial notebook/MDX examples**, especially LangChain ReAct usage (`pages/techniques/react.en.mdx:120-155`, `notebooks/react.ipynb` cells 1-3).

Where framework usage is explicit:
- **LangChain agents** in examples: `from langchain.agents import load_tools, initialize_agent` and `initialize_agent(..., agent="zero-shot-react-description")` (`pages/techniques/react.en.mdx:131-149`; mirrored in `notebooks/react.ipynb`).
- **OpenAI tool/function calling** examples in notebooks (`notebooks/pe-function-calling.ipynb`, e.g. lines around 40-47, 95-101).
- **RAG pipeline pieces** in notebooks using Chroma + sentence-transformers (`notebooks/pe-rag.ipynb`, e.g. ~565-577, ~690-695).

So architecture is: a docs site serving static/explanatory content plus notebook code samples. The “intelligence” mostly lives in prompts/snippets embedded in docs, not in repository-level orchestrator code that executes a coordinated agent system at runtime.

## 3. Orchestration Pattern

Closest match: **Other (educational content + single-agent tool loop examples)**, not a true multi-agent orchestration system.

The key control flow shown in code is a **single ReAct agent** with iterative tool-use managed by LangChain’s executor:

`pages/techniques/react.en.mdx:146-154`
```python
llm = OpenAI(model_name="text-davinci-003" ,temperature=0)
tools = load_tools(["google-serper", "llm-math"], llm=llm)
agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)
...
agent.run("Who is Olivia Wilde's boyfriend? ...")
```

And the execution trace confirms a Thought/Action/Observation loop inside one agent:

`pages/techniques/react.en.mdx:160-176`
```yaml
> Entering new AgentExecutor chain...
Action: Search
Observation: ...
Action: Calculator
Observation: ...
Final Answer: ...
> Finished chain.
```

No repository code defines planner/worker agent teams, inter-agent message buses, graph state machines, or supervisor hierarchies.

## 4. Tools & External Integrations

- **Docs web stack**: Next.js + Nextra (`package.json:20-34`, `next.config.js:1-26`).
- **GitHub raw content fetch** (for page text retrieval API): `fetch()` against `raw.githubusercontent.com` in `pages/api/getPageContent.ts:20-27`.
- **Local filesystem APIs** for indexing docs metadata/content (`pages/api/contentFiles.js:2-27`, `pages/api/promptsFiles.js:2-45`).
- **LangChain tools in examples**: `google-serper`, `llm-math` loaded via `load_tools` (`pages/techniques/react.en.mdx:147`; also `notebooks/react.ipynb`).
- **OpenAI API in examples**: chat completions and tool-calling flow (`notebooks/pe-function-calling.ipynb` ~40-47, ~95-101).
- **RAG stack in examples**: ChromaDB persistent client + sentence-transformers embeddings + retrieval query (`notebooks/pe-rag.ipynb` ~565-577, ~690-695).

No MCP server wiring, browser automation framework, terminal/shell-agent execution loop, or production vector DB service integration is implemented in app runtime code.

## 5. Notable Code Walkthrough

- `pages/techniques/react.en.mdx:114-188` — Core educational ReAct walkthrough, including LangChain agent initialization, tool configuration (`google-serper`, `llm-math`), and executor trace; this is the clearest concrete “agent code” in the repo.
- `notebooks/react.ipynb` (cells 1-3; JSON lines ~25-29, ~46, ~93) — Runnable notebook version of the same single-agent ReAct example, showing dependencies, API keys, `initialize_agent`, and `agent.run(...)`.
- `notebooks/pe-rag.ipynb` (~565-577, ~628-652, ~690-695) — Demonstrates a RAG workflow with embedding generation, Chroma persistence, and retrieval queries; important because it is actual executable RAG code.
- `notebooks/pe-function-calling.ipynb` (~40-47, ~95-101, ~361+) — Shows OpenAI tool/function-calling mechanics (including parallel tool calls), relevant to agent tool-use patterns.
- `pages/api/getPageContent.ts:13-53` — Production app route that fetches and sanitizes MDX content from GitHub raw; representative of what this repository actually runs in deployment (content delivery, not agent orchestration).

## 6. Use-Case Mapping

The assigned label `RAG + Agents` is **partially true only at tutorial/example level**: there are separate notebook examples for RAG (`notebooks/pe-rag.ipynb`) and single-agent/tool-use patterns (`notebooks/react.ipynb`, `notebooks/pe-function-calling.ipynb`). However, the repository itself does **not** implement an integrated runtime agentic-RAG system where multiple agents coordinate.

Given what is actually implemented as software, this repo is better categorized as **Workflow Automation** for content publishing/documentation delivery (Next.js APIs + MDX pipeline), with embedded educational materials about agents/RAG.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
- Broad, well-maintained corpus of agent/RAG concepts with multilingual coverage in source MDX.
- Includes executable notebooks that demonstrate practical APIs (LangChain, OpenAI tools, Chroma).
- Clearly separates conceptual guidance from runnable snippets, making onboarding easier.
- Documentation architecture is lightweight and reproducible (`next dev` + static content conventions).

- **Limitations:**
- No production multi-agent runtime implementation in repository code (mostly explanatory/tutorial content).
- Agent examples are largely single-agent; no true coordinated MAS execution engine.
- Tool integrations (search, weather function, RAG) are tutorial-grade, not hardened service abstractions.
- Limited test/evaluation infrastructure for the notebook-based agent examples.

- **Research relevance:**
- Useful as evidence of how agent concepts are taught and operationalized in developer education.
- Provides concrete single-agent ReAct/tool-use exemplars suitable for pedagogical benchmarking.
- Offers practical RAG notebook pipelines that can support reproducibility studies of instructional material.
- Less suitable as evidence for claims about deployed multi-agent system architecture/performance.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
