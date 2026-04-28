---
repo_name: projectdiscovery/shuffledns
url: "https://github.com/projectdiscovery/shuffledns"
stars: 1614
forks: 215
contributors_count: 19
last_commit_date: "2026-01-20T21:07:50+00:00"
primary_use_case: Workflow Automation
user_tier: Mid-Tier
total_score: 3
architecture_labels: [Custom/Other]
use_case_labels: [Workflow Automation]
generated_at: "2026-04-27T15:58:57.612389+00:00"
model: auto
duration_s: 60.0
clone_size_kb: 2244
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`shuffledns` is a Go CLI utility that automates high-volume DNS subdomain discovery by wrapping the external `massdns` binary and adding post-processing logic. Users run `shuffledns` in one of three modes (`bruteforce`, `resolve`, `filter`) with inputs like domains, wordlists, resolvers, or existing MassDNS output, and receive deduplicated resolved hostnames (plain text or NDJSON). The tool is built for workflow-scale enumeration: it streams inputs in large batches, executes DNS resolution chunks, parses results, removes probable wildcard artifacts, and writes final output to stdout or file. In short, it is a DNS automation pipeline rather than an LLM system.

## 2. Agent Framework & Architecture

No LLM agent framework is used. A direct code scan shows no imports or runtime references to LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, OpenAI/Anthropic SDKs, prompt templates, or model-inference clients; dependencies in `go.mod` are networking, CLI, storage, and utility libraries (`go.mod:5-38`).

Architecture is custom procedural orchestration centered on a CLI runner and a MassDNS processing engine. The entrypoint parses flags, constructs a runner, and executes enumeration (`cmd/shuffledns/main.go:8-19`). The runner chooses one processing path based on mode/input (`pkg/runner/runner.go:75-95`) and instantiates a `massdns.Instance` with operational settings (`pkg/runner/runner.go:111-131`, `154-173`, `216-235`).

The “intelligence” is deterministic filtering/verification logic, not LLM planning: streamed chunk processing (`pkg/massdns/process.go:466-611`, `613-754`), MassDNS output parsing (`pkg/parser/parser.go:24-113`), wildcard detection via DNS probing and caches (`pkg/wildcards/resolver.go:91-185`), and IP-to-hostname aggregation in LevelDB (`pkg/store/store.go:20-39`, `72-129`).

## 3. Orchestration Pattern

Closest match: **sequential pipeline with concurrent worker stages** (not hierarchical multi-agent, graph, or swarm).

Control flow is mode-routed and linear: parse options -> pick processing function -> process chunks -> parse/store -> wildcard filtering -> write output. Example dispatch logic:

```75:95:pkg/runner/runner.go
func (r *Runner) RunEnumeration() {
    if r.options.MassdnsRaw != "" { r.processExistingOutput(); return }
    if r.options.Wordlist != "" { r.processDomain(); return }
    if r.options.SubdomainsList != "" || fileutil.HasStdin() {
        r.processSubdomains(); return
    }
}
```

Within each path, batch callbacks orchestrate chunk execution and immediate parsing:

```629:673:pkg/massdns/process.go
batcher.WithFlushCallback[string](func(subdomains []string) {
    chunkFile, _ := os.CreateTemp(instance.options.TempDir, fmt.Sprintf("chunk-%d-", chunkNum))
    // write chunk...
    stdoutFile, stderrFile, took, err := instance.runChunk(ctx, chunkFile.Name())
    // parse immediately into store
    err = instance.parseMassDNSOutputFile(stdoutFile, shstore)
})
```

So this is a workflow automation engine with internal goroutine parallelism (e.g., wildcard checks and output verification), but no coordinated LLM agents.

## 4. Tools & External Integrations

- **External DNS engine (`massdns` binary via shell execution):** invoked with `exec.CommandContext` and runtime flags in `pkg/massdns/process.go:53-79` and `177-203`.
- **DNS client library (`dnsx`) for trusted verification + wildcard probing:** created in `pkg/wildcards/resolver.go:40-49` and used in output verification in `pkg/massdns/process.go:377-421`.
- **Public suffix extraction (`publicsuffix-go`) for auto root-domain inference:** `pkg/massdns/process.go:254-277`.
- **Local embedded database (LevelDB) for IP-hostname aggregation/state:** initialized and used in `pkg/store/store.go:20-39`, `72-129`.
- **Filesystem + temp files for chunked streaming pipeline:** temp directories/files used across runner and massdns processing (`pkg/runner/runner.go:36-44`, `pkg/massdns/process.go:491-543`, `638-690`).
- **No LLM/model APIs, MCP servers, browser automation, vector DBs, or RAG stack:** not present in source imports or runtime code.

## 5. Notable Code Walkthrough

- `cmd/shuffledns/main.go:8-19` - Minimal CLI bootstrap that parses options, constructs the runner, triggers enumeration, and cleans temp resources.
- `pkg/runner/options.go:56-144` - Defines CLI contract and execution modes; this is where users configure the workflow (inputs, resolvers, output format, batch sizing, wildcard behavior).
- `pkg/runner/runner.go:75-252` - Central orchestrator selecting bruteforce/resolve/filter paths and wiring options into `massdns.Instance`.
- `pkg/massdns/process.go:466-754` - Core streaming pipeline: chunk batching, MassDNS execution per chunk, parse-as-you-go ingestion, wildcard filtering, and final output write.
- `pkg/wildcards/resolver.go:91-185` - Wildcard detection algorithm using randomized wildcard permutations, DNS probing, and caches to reduce redundant checks.

## 6. Use-Case Mapping

The assigned category **Workflow Automation** is correct for this repository. `shuffledns` automates a repeatable, high-throughput operational workflow (subdomain input -> DNS resolution -> filtering -> normalized output) with configurable execution modes and concurrency controls (`pkg/runner/validate.go:34-60`, `pkg/massdns/process.go:466-754`). It coordinates tools, files, and verification steps to produce reliable output artifacts for security/recon pipelines, but does not implement LLM-based or multi-agent reasoning.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Efficient streaming/chunk architecture reduces memory pressure on large inputs (`pkg/massdns/process.go:479-546`, `626-694`).
  - Practical wildcard-removal logic with caching and parallel checks (`pkg/massdns/process.go:279-350`, `pkg/wildcards/resolver.go:127-177`).
  - Flexible operational modes (`bruteforce`, `resolve`, `filter`) with validation guardrails (`pkg/runner/validate.go:34-60`).
  - Supports trusted-resolver revalidation before final emit, improving output quality (`pkg/massdns/process.go:377-421`).
  - Uses LevelDB-backed aggregation for scalable intermediate state (`pkg/store/store.go:20-39`, `108-129`).

- **Limitations:**
  - Hard dependency on external `massdns` binary availability/path; failures block core workflow (`pkg/runner/runner.go:28-33`, `52-73`).
  - No native DNS resolution fallback if `massdns` is missing.
  - Error handling inside batch flush callbacks logs and returns locally, but does not always abort whole pipeline deterministically (`pkg/massdns/process.go:515-534`, `662-681`).
  - Concurrency around shared counters/maps in output writing appears unsynchronized (`resolvedCount++`, `uniqueMap`) and could risk races under heavy parallelism (`pkg/massdns/process.go:372-450`).
  - Not an agentic architecture despite “automation” behavior; no planning/adaptation layer.

- **Research relevance:**
  - Useful evidence for **non-LLM workflow orchestration** patterns in security tooling.
  - Demonstrates practical pipeline engineering: streaming batches, external tool delegation, and post-processing filters.
  - Illustrates deterministic “intelligence” (rule/caching-based filtering) as an alternative to agentic reasoning.
  - Not suitable as evidence of multi-agent LLM coordination at runtime.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
