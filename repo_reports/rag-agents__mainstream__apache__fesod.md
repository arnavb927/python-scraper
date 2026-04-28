---
repo_name: apache/fesod
url: "https://github.com/apache/fesod"
stars: 5978
forks: 494
contributors_count: 42
last_commit_date: "2026-04-17T13:14:42+00:00"
primary_use_case: RAG + Agents
user_tier: Mainstream
total_score: 5
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T13:13:42.632381+00:00"
model: auto
duration_s: 77.9
clone_size_kb: 105644
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`apache/fesod` is a Java library for high-performance, low-memory spreadsheet processing (Excel/CSV), not an LLM system. A user typically depends on `fesod-sheet` and runs APIs like `FesodSheet.read(...).sheet().doRead()` or `FesodSheet.write(...).sheet().doWrite(...)` to stream rows in and out of files or HTTP responses (`README.md:41-65`, `fesod-sheet/src/main/java/org/apache/fesod/sheet/FesodSheet.java:169-333`, `fesod-examples/fesod-sheet-examples/src/main/java/org/apache/fesod/sheet/examples/web/WebExampleController.java:116-145`). The core value is handling large files without OOM through event/SAX-style reading and cache-backed buffering (`fesod-sheet/src/main/java/org/apache/fesod/sheet/ExcelReader.java:40-70`, `fesod-sheet/src/main/java/org/apache/fesod/sheet/cache/Ehcache.java:50-190`). Outputs are parsed row events/maps/POJOs on read, and generated `.xlsx`/`.csv` content on write.

## 2. Agent Framework & Architecture

No agent framework is used. I found no imports/usages of LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, OpenAI, Anthropic, or MCP in the Java source (search over `*.java` returned no matches for those framework imports), and the dependency graph is spreadsheet/infra focused (`pom.xml:93-241`).

Architecture is a builder/facade plus execution-engine design for spreadsheet IO. `FesodSheet` is the static entry facade that constructs reader/writer builders (`fesod-sheet/src/main/java/org/apache/fesod/sheet/FesodSheet.java:42-175`, `:216-333`). `ExcelReader` and `ExcelWriter` are runtime orchestrators for read/write operations (`fesod-sheet/src/main/java/org/apache/fesod/sheet/ExcelReader.java:49-90`, `fesod-sheet/src/main/java/org/apache/fesod/sheet/ExcelWriter.java:53-110`).

On reads, `ExcelAnalyserImpl` chooses a concrete executor (`XlsSaxAnalyser`, `XlsxSaxAnalyser`, `CsvExcelReadExecutor`) based on file type and then runs it (`fesod-sheet/src/main/java/org/apache/fesod/sheet/analysis/ExcelAnalyserImpl.java:113-177`, `:192-201`). The “intelligence” here is deterministic format routing and resource management, not prompt/planner logic.

## 3. Orchestration Pattern

Closest match: **other (deterministic sequential pipeline / strategy dispatch)**, not multi-agent orchestration.

Control flow is linear: API facade -> builder -> reader -> analyzer -> format-specific executor.

```113:177:fesod-sheet/src/main/java/org/apache/fesod/sheet/analysis/ExcelAnalyserImpl.java
private void chooseExcelExecutor(ReadWorkbook readWorkbook) throws Exception {
    ExcelTypeEnum excelType = ExcelTypeEnum.valueOf(readWorkbook);
    switch (excelType) {
        case XLS:
            // ...
            excelReadExecutor = new XlsSaxAnalyser(xlsReadContext);
            break;
        case XLSX:
            excelReadExecutor = new XlsxSaxAnalyser(xlsxReadContext, null);
            break;
        case CSV:
            excelReadExecutor = new CsvExcelReadExecutor(csvReadContext);
            break;
    }
}
```

```118:124:fesod-sheet/src/main/java/org/apache/fesod/sheet/read/builder/ExcelReaderSheetBuilder.java
public void doRead() {
    if (excelReader == null) {
        throw new ExcelGenerateException("Must use 'FesodSheet.read().sheet()' to call this method");
    }
    excelReader.read(build());
    excelReader.finish();
}
```

There is no planner-worker split, no graph state machine of agents, and no runtime role coordination.

## 4. Tools & External Integrations

- **Apache POI (Excel parsing/writing backend):** wired in dependency management and used in analyzers/metadata classes (`pom.xml:176-184`, `fesod-sheet/src/main/java/org/apache/fesod/sheet/analysis/ExcelAnalyserImpl.java:56-61`).
- **Ehcache (read cache for large files):** disk + in-memory caches via `CacheManagerBuilder` and per-run cache aliases (`fesod-sheet/src/main/java/org/apache/fesod/sheet/cache/Ehcache.java:36-43`, `:105-115`, `:118-190`).
- **Spring Boot Web (example integration only):** demo app/controller exposes file upload/download endpoints that call `FesodSheet` (`fesod-examples/fesod-sheet-examples/src/main/java/org/apache/fesod/sheet/examples/web/FesodWebApplication.java:28-51`, `WebExampleController.java:116-145`).
- **File system and streams:** direct file/input/output stream APIs in facade and reader/writer builders (`fesod-sheet/src/main/java/org/apache/fesod/sheet/FesodSheet.java:52-107`, `:183-277`).
- **LLM/RAG/external AI tools:** not present in source.

## 5. Notable Code Walkthrough

- `fesod-sheet/src/main/java/org/apache/fesod/sheet/FesodSheet.java:42-333` - Primary user-facing API facade; constructs read/write/sheet/table builders for files and streams, defining how users invoke the library.
- `fesod-sheet/src/main/java/org/apache/fesod/sheet/analysis/ExcelAnalyserImpl.java:113-177,192-213,220-313` - Core read-time dispatcher and lifecycle manager; selects executor by file type, runs parsing, and performs robust cleanup.
- `fesod-sheet/src/main/java/org/apache/fesod/sheet/cache/Ehcache.java:50-190` - Large-file buffering strategy using batched entries, disk persistence, active cache, and cache teardown.
- `fesod-sheet/src/main/java/org/apache/fesod/sheet/read/builder/ExcelReaderSheetBuilder.java:111-140` - Execution trigger for sheet reads (`doRead`/`doReadSync`), showing the explicit sequential invocation model.
- `fesod-examples/fesod-sheet-examples/src/main/java/org/apache/fesod/sheet/examples/web/WebExampleController.java:116-145` - Concrete integration example for HTTP download/upload flows using streaming IO plus listener-based row handling.

## 6. Use-Case Mapping

The assigned label **“RAG + Agents” is incorrect** for this repository based on actual code. The project is a spreadsheet processing library with deterministic parsers, builders, listeners, and cache layers; there are no LLM calls, embeddings, retrieval chains, prompt templates, or multi-agent coordination runtime. A better category from your taxonomy is **Workflow Automation**, since it automates high-volume spreadsheet ingestion/export pipelines (including web upload/download workflows) (`WebExampleController.java:116-145`, `ExcelAnalyserImpl.java:113-177`).

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong large-file focus via streaming/event read model and explicit cache subsystem (`ExcelReader.java:40-70`, `Ehcache.java:50-190`).
  - Clear API ergonomics through static facade + builder pattern (`FesodSheet.java:42-333`).
  - Format-aware execution strategy (XLS/XLSX/CSV) with graceful handling paths (`ExcelAnalyserImpl.java:113-177`, `:335-346`).
  - Practical integration examples (CLI-style examples and Spring web upload/download) (`NoModelReadExample.java:89-97`, `WebExampleController.java:116-145`).

- **Limitations:**
  - No LLM, agent, or RAG functionality; unsuitable for multi-agent AI benchmarking.
  - Some docs/comments still inherit EasyExcel-era framing; can blur project boundaries (`README.md`, file headers in core classes).
  - Limited orchestration abstraction beyond sequential builder/executor flow (no DAG/workflow engine).
  - Example web integration is demo-level and not a full production service template.

- **Research relevance:**
  - Useful evidence for **non-AI workflow automation** patterns in data engineering libraries.
  - Illustrates strategy-dispatch architecture for heterogeneous file formats under memory constraints.
  - Relevant to studies on API design for stream processing and listener-based ingestion.
  - Not suitable as evidence for multi-agent coordination or LLM tool-use behaviors.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
