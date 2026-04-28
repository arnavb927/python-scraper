---
repo_name: nf-core/rnaseq
url: "https://github.com/nf-core/rnaseq"
stars: 1264
forks: 863
contributors_count: 115
last_commit_date: "2026-04-09T16:50:26+00:00"
primary_use_case: RAG + Agents
user_tier: Mid-Tier
total_score: 6
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation, RAG + Agents]
generated_at: "2026-04-27T12:52:18.727538+00:00"
model: auto
duration_s: 59.0
clone_size_kb: 19582
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`nf-core/rnaseq` is a production bioinformatics workflow for processing RNA-seq data with Nextflow DSL2, not an LLM application. A user runs `nextflow run nf-core/rnaseq ...` with a samplesheet and reference inputs, and the pipeline executes preprocessing, alignment/pseudoalignment, quantification, QC, and reporting steps. The main outputs are expression quantification files, QC artifacts, and a consolidated MultiQC report, plus execution metadata (trace/report/timeline). The code is organized as composable Nextflow subworkflows and modules that orchestrate external genomics tools at scale.

## 2. Agent Framework & Architecture

No LLM-agent framework is used in the runtime code. There are no imports/usages of LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, OpenAI/Anthropic SDKs, prompt templates, or retrieval pipelines in core workflow files; the execution model is Nextflow workflow orchestration (`main.nf`, `workflows/rnaseq/main.nf`).

Architecture is a DSL2 pipeline graph built from subworkflows/modules, where control logic lives in conditional branches and channel transformations rather than “agent reasoning.” The top-level `workflow` runs initialization, main pipeline, then completion hooks (`main.nf:152-190`). The core `RNASEQ` workflow wires many subworkflows (alignment modes, quantification modes, QC modules, contaminant screening) and routes data via Nextflow channels (`workflows/rnaseq/main.nf:69-878`).

So this is a custom workflow automation architecture (dataflow DAG with branching), not an intelligent multi-agent system.

## 3. Orchestration Pattern

Closest match: **other (dataflow workflow automation / DAG orchestration)**.

Control flow is deterministic and parameter-driven: branches are selected by flags like `params.aligner`, `params.skip_alignment`, `params.contaminant_screening`, then channels are merged/joined to drive downstream processes. Example branch dispatch:

```26:33:main.nf
workflow {
    main:
    PIPELINE_INITIALISATION ( ... )
    NFCORE_RNASEQ ()
    PIPELINE_COMPLETION ( ... )
}
```

```264:272:workflows/rnaseq/main.nf
if (!params.skip_alignment && (params.aligner == 'star_salmon' || params.aligner == 'star_rsem')) {
    ALIGN_STAR (
        ch_strand_inferred_filtered_fastq,
        ch_star_index.map { item -> [ [:], item ] },
        ch_gtf.map { item -> [ [:], item ] },
        params.star_ignore_sjdbgtf,
```

Channel-based aggregation and per-sample bundling also show DAG-style orchestration rather than manager/worker agents (`workflows/rnaseq/main.nf:245-258`, `594-603`, `809-833`).

## 4. Tools & External Integrations

This repo integrates many **bioinformatics tools/services**, but not LLM tools:

- **Nextflow + nf-schema plugin** for parameter/schema validation and input parsing (`nextflow.config:468-476`, `workflows/rnaseq/main.nf:51`, `subworkflows/local/utils_nfcore_rnaseq_pipeline/main.nf:76-86`).
- **Alignment/quantification tools** (STAR, HISAT2, Bowtie2, Salmon, RSEM, Kallisto, StringTie, Picard, SAMtools) wired via modules/subworkflows (`workflows/rnaseq/main.nf:18-24`, `53-62`, `264-385`, `417-472`, `515-548`, `758-795`).
- **QC/reporting stack** (FastQC, RSeQC, Qualimap, dupradar, preseq, RustQC, MultiQC) wired into per-sample bundles and final report generation (`workflows/rnaseq/main.nf:559-631`, `805-833`; defaults in `nextflow.config:102-131`).
- **Contaminant screening** with Kraken2/Bracken/Sylph (`workflows/rnaseq/main.nf:706-752`; config includes in `nextflow.config:512-515`).
- **Container/runtime backends** (Docker, Singularity, Podman, Apptainer, Conda/Mamba, Wave) as execution environments (`nextflow.config:184-283`).
- **Notification/webhook integration** via `hook_url` and `imNotification` on completion (`nextflow.config:139`, `subworkflows/local/utils_nfcore_rnaseq_pipeline/main.nf:162-164`).
- No MCP servers, browser automation, vector DB, or RAG retrieval components found.

## 5. Notable Code Walkthrough

- `main.nf:55-144` — Defines `NFCORE_RNASEQ` workflow: prepares references, computes QC tool list, invokes the main RNASEQ workflow, and emits status/report outputs. This is the pipeline entrypoint orchestration.
- `main.nf:152-190` — Top-level run lifecycle (`PIPELINE_INITIALISATION` -> `NFCORE_RNASEQ` -> `PIPELINE_COMPLETION`), showing explicit workflow phases and completion handling.
- `workflows/rnaseq/main.nf:69-878` — Core analytical DAG: input channel construction, branching by alignment mode, quantification paths, QC/contaminant screening, software version collation, and MultiQC generation.
- `subworkflows/local/utils_nfcore_rnaseq_pipeline/main.nf:28-99` — Initialization logic for CLI/help/schema validation and custom parameter validation entrypoint.
- `subworkflows/local/utils_nfcore_rnaseq_pipeline/main.nf:248-437` — Dense domain validation logic (`validateInputParameters`) that enforces mutually compatible modes/inputs; this is key “control intelligence,” but rule-based, not LLM-based.
- `nextflow.config:184-283` — Execution profile matrix for containers/package managers and cloud/HPC portability; critical for reproducible workflow automation at scale.

## 6. Use-Case Mapping

The assigned label **`RAG + Agents` is incorrect** for this repository based on source inspection. There is no runtime LLM, no retrieval/indexing over knowledge for generation, and no multi-agent coordination logic. Instead, this project is a deterministic, parameterized scientific workflow orchestrator that automates end-to-end RNA-seq analysis across many external tools and environments. A better category is **Workflow Automation**.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Mature, modular DSL2 architecture with clear separation of initialization, core analysis, and completion phases.
  - Extensive conditional pathways (multiple aligners/quantifiers/QC stacks) while preserving a unified output/report pattern.
  - Strong parameter validation and safety checks reduce invalid experimental configurations.
  - Rich ecosystem integration (containers, conda/mamba, Wave, multiple contaminant/QC tools) for portability/reproducibility.
  - Thoughtful channel joins/per-sample aggregation for robust MultiQC reporting across optional branches.

- **Limitations:**
  - No LLM or agentic components; unsuitable as evidence for modern agent orchestration techniques.
  - Complexity of branching/channel joins can increase maintenance burden and make reasoning/debugging harder.
  - Heavy dependence on external genomics tools and reference assets; setup/compute costs can be high.
  - Limited “adaptive intelligence”: logic is rule-driven via params, not dynamic planning or learned decision-making.
  - Some behavior assumptions are documented as potentially fragile (e.g., metadata consistency in bundle joins).

- **Research relevance:**
  - Good exemplar of large-scale **workflow orchestration** in scientific computing (dataflow DAG + modular subworkflows).
  - Useful for studies on reproducibility/portability patterns in computational pipelines.
  - Relevant to comparisons between deterministic pipelines and agentic/LLM systems as a non-agent baseline.
  - Demonstrates practical integration engineering across heterogeneous command-line bioinformatics tools.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
