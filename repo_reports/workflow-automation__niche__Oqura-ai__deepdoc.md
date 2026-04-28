---
repo_name: Oqura-ai/deepdoc
url: "https://github.com/Oqura-ai/deepdoc"
stars: 246
forks: 34
contributors_count: 3
last_commit_date: "2026-02-28T04:37:46+00:00"
primary_use_case: Workflow Automation
user_tier: Niche
total_score: 2
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T17:42:23.030964+00:00"
model: auto
duration_s: 65.1
clone_size_kb: 40185
uses_mas: yes
final_use_case: Workflow Automation
---
## 1. Overview

`deepdoc` is a CLI-based local research assistant that turns a folder of user documents into a structured long-form report. A user runs `python main.py`, enters a topic, an outline, and a local directory path, and the system ingests files (PDF/DOCX/PPTX/images/text), chunks and indexes them in Qdrant, then generates section-wise research content and a final Markdown report (`main.py:33-73`, `deepresearch/chunk_prep.py:161-266`). It is designed for “deep research on local knowledge,” not open web crawling, by combining LLM planning/writing with retrieval over the user’s own documents (`deepresearch/qdrant_setup.py:17-33`). The output is a compiled report displayed in terminal and exported to `output_folder/final_report_<timestamp>.md` (`main.py:62-73`).

## 2. Agent Framework & Architecture

The repo **actually uses LangGraph + LangChain**, not CrewAI. This is confirmed by imports and graph construction in `deepresearch/graph.py` (`from langgraph.graph import StateGraph`) and prompt/LLM chains in `deepresearch/nodes.py` (`ChatPromptTemplate`, `llm.with_structured_output(...)`).

Architecture-wise, there are two layers: a top-level workflow graph (`resource_setup -> report_structure_planner -> human_feedback -> section_formatter -> research_agent -> final_report_writer`) and a nested per-section research subgraph (`section_knowledge -> query_generator -> rag_search -> result_accumulator -> reflection -> final_section_formatter`) (`deepresearch/graph.py:7-40`). “Agent intelligence” mainly lives in role-specific system prompts (`deepresearch/prompts.py`) and structured state schemas (`deepresearch/schema.py`) rather than separate model instances.

Although all roles share one configurable base LLM client (`deepresearch/client_init.py:11-23`), they are functionally separated into planner, formatter, query generator, reflection evaluator, section writer, and final report assembler nodes (`deepresearch/nodes.py:29-181`). The section stage fans out into multiple concurrent per-section runs via `Send(...)`, then merges section outputs back for final synthesis (`deepresearch/nodes.py:62-80`, `deepresearch/schema.py:36`).

## 3. Orchestration Pattern

Closest match: **graph (LangGraph-style state machine)** with a **fan-out/fan-in map-reduce flavor** for section research.

Control flow is explicitly encoded as graph edges and compiled state graphs:

```1:10:deepresearch/graph.py
from langgraph.graph import StateGraph, END, START
...
research_builder = StateGraph(ResearchState, output=SectionOutput)
research_builder.add_node("section_knowledge", section_knowledge_node)
...
research_builder.add_edge(START, "section_knowledge")
research_builder.add_edge("section_knowledge", "query_generator")
```

Parallelized section dispatch is done with LangGraph `Send`, which routes each parsed section into the `research_agent` subgraph:

```62:80:deepresearch/nodes.py
def section_formatter_node(state: AgentState, config: RunnableConfig) -> Command[Literal["research_agent"]]:
    ...
    return Command(
        update={"sections": result.sections},
        goto=[
            Send(
                "research_agent",
                {
                    "section": s,
                }
            ) for s in result.sections
        ]
    )
```

There is also a loop/back-edge behavior inside the research subgraph through `reflection_feedback_node`, which conditionally routes to either `final_section_formatter` or back to `query_generator` (`deepresearch/nodes.py:139-159`).

## 4. Tools & External Integrations

- **LLM providers (OpenAI/Anthropic/Google/Ollama)**: dynamically selected in `init_llm()` and used for all agent roles (`deepresearch/client_init.py:1-23`, wired in `deepresearch/nodes.py:16-20`).
- **Vector store / RAG backend (Qdrant + FastEmbed document vectors)**: collection creation, upsert, and filtered semantic retrieval by `group_id` (`deepresearch/qdrant_setup.py:8-16`, `17-33`, `52-62`).
- **Local filesystem ingestion pipeline**: scans a user directory, reads bytes, converts files, and chunks content (`deepresearch/chunk_prep.py:161-266`).
- **Document conversion stack**: DOC/DOCX/PPTX/TXT/Image to PDF via `python-docx`, `python-pptx`, PIL, and PyMuPDF (`deepresearch/converters.py:13-99`).
- **OCR service (Mistral OCR API)**: optional OCR path for PDF text extraction when API key/client available (`deepresearch/chunk_prep.py:55-63`, `105-114`).
- **Terminal UI/output tooling**: Rich + PyFiglet for interactive UX and report rendering (`main.py:5-12`, `33-77`).
- **Notably absent at runtime**: no web search calls are wired in core nodes despite `tavily-python` in requirements (`requirements.txt:8`).

## 5. Notable Code Walkthrough

- `deepresearch/graph.py:7-40` - Defines the full LangGraph topology, including a nested research subgraph and top-level orchestration graph. This file is the control-plane backbone for multi-agent coordination.
- `deepresearch/nodes.py:22-181` - Implements all agent-role behaviors (setup, planner, formatter, query generation, retrieval, reflection, section/final writing). It is where prompts, structured outputs, and routing decisions are executed.
- `deepresearch/prompts.py:1-490` - Contains the role prompts for each agent stage; this is where most behavioral policy/intelligence is encoded (planning, reflection criteria, synthesis requirements).
- `deepresearch/chunk_prep.py:161-266` - Performs local document ingestion, conversion, extraction, chunking, and preprocessing summary/confirmation, enabling the downstream RAG flow.
- `deepresearch/qdrant_setup.py:17-33` and `52-62` - Wires retrieval and indexing against Qdrant, including per-thread isolation via `group_id`, which is key for query-time document scoping.

## 6. Use-Case Mapping

The assigned use case **Workflow Automation** is accurate. The repository automates an end-to-end research workflow: ingest local files, structure report plan, collect/retrieve evidence, run iterative reflection, and compile a final report without manual orchestration by the user (`main.py:33-37`, `deepresearch/graph.py:34-40`, `deepresearch/nodes.py:62-80`).  

It also has strong **RAG + Agents** characteristics (Qdrant-backed retrieval + multi-role generation), but functionally the primary value is workflow automation of research/report production from local knowledge bases.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Clear graph-based decomposition of roles into reusable nodes/subgraphs (`deepresearch/graph.py`).
  - Practical fan-out per report section, enabling scalable section-level parallelism (`deepresearch/nodes.py:70-79`).
  - Strong prompt modularity: each stage has explicit objectives and output constraints (`deepresearch/prompts.py`).
  - Real local-document pipeline with format conversion + optional OCR + vector indexing (`deepresearch/chunk_prep.py`, `deepresearch/converters.py`, `deepresearch/qdrant_setup.py`).
  - Human-in-the-loop checkpoint before deep generation (`deepresearch/nodes.py:46-58`).

- **Limitations:**
  - Reflection routing logic appears inconsistent: condition may prematurely accept content because `reflection_count < num_reflections` leads to finalize path (`deepresearch/nodes.py:150-154`).
  - Potential syntax/robustness issue in `rag_search_node` string interpolation around nested quotes for `page_content` (`deepresearch/nodes.py:122`).
  - Minimal error handling/retries around LLM and Qdrant calls; failures could halt long workflows (`deepresearch/nodes.py`, `deepresearch/qdrant_setup.py`).
  - Some config/deps appear unused in runtime path (e.g., Tavily), suggesting drift between intent and implementation (`requirements.txt:8`).
  - No explicit citation/provenance stitching in final report despite retrieval pipeline.

- **Research relevance:**
  - Good real-world example of **single-LLM multi-role orchestration** using prompt-specialized agents in a state graph.
  - Demonstrates **hierarchical graph composition** (top-level workflow + per-task subgraph) for long-form generation.
  - Shows **agentic RAG over private/local corpora** with human feedback gates.
  - Useful evidence for studying tradeoffs between prompt-defined role separation and true heterogeneous-agent systems.

## 8. Machine-readable classification

USES_MAS: yes
FINAL_USE_CASE: Workflow Automation
