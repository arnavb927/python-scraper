---
repo_name: intel/confidential-computing.sgx
url: "https://github.com/intel/confidential-computing.sgx"
stars: 1422
forks: 561
contributors_count: 103
last_commit_date: "2026-04-15T07:34:48+00:00"
primary_use_case: Simulation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [Custom/Other]
use_case_labels: [Simulation]
generated_at: "2026-04-27T14:27:24.319187+00:00"
model: auto
duration_s: 78.4
clone_size_kb: 36552
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`intel/confidential-computing.sgx` is Intel’s production SGX software stack for Linux, containing the SDK, Platform Software (PSW), runtime libraries, signing/build tooling, and sample enclave applications. A user typically runs build targets like `make sdk`, `make psw`, or package targets from the top-level `Makefile`, then compiles/runs enclave apps (often in `SGX_MODE=SIM` for simulation mode) to create enclaves and execute trusted code. The codebase solves secure enclave lifecycle problems (create/load/init/ecall/attestation/package/deploy), not conversational AI problems. In practice, outputs are native binaries, shared libraries, and installers (`.deb/.rpm/.bin`) plus runnable sample SGX apps.

## 2. Agent Framework & Architecture

No LLM-agent framework is used here. I found no LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex/OpenAI/Anthropic-style runtime code or dependencies in core source; this repository is primarily C/C++ systems code with build orchestration.

Architecture-wise, the core logic is SGX runtime + simulator + service/toolchain components. For example, simulation-mode enclave lifecycle is implemented by classes like `EnclaveCreatorSim` (`sdk/simulation/urtssim/enclave_creator_sim.cpp`) and enclave tracking structures like `CEnclaveMngr` (`sdk/simulation/uinst/enclave_mngr.cpp`). Enclave instruction simulation (`ECREATE/EADD/EINIT/EENTER/ERESUME/EREMOVE`) is implemented in `sdk/simulation/uinst/u_instructions.cpp`, while trusted runtime ECALL dispatch and thread/TCS handling are in `sdk/trts/trts_ecall.cpp`.

The “intelligence” in this repo is deterministic systems logic (state checks, permission checks, dispatch tables, memory/thread control), not prompt-driven planning or model inference.

## 3. Orchestration Pattern

Closest match: **Other (deterministic runtime state machine / systems dispatch)**, not multi-agent orchestration.

Control flow is explicit instruction dispatch in simulation mode:

```407:418:sdk/simulation/uinst/u_instructions.cpp
// Master entry functions
LOAD_REGS_ATTRIBUTES
void _SE3(uintptr_t xax, uintptr_t xbx,
          uintptr_t xcx, uintptr_t xdx,
          uintptr_t xsi, uintptr_t xdi)
{
    switch (xax)
```

and ECALL dispatch in trusted runtime:

```305:314:sdk/trts/trts_ecall.cpp
void *addr = NULL;
status = get_func_addr(ordinal, &addr);
if(status == SGX_SUCCESS)
{
    ecall_func_t func = (ecall_func_t)addr;
    sgx_lfence();
    status = func(ms);
}
```

This is a low-level sequential/stateful execution model for enclave lifecycle operations, not planner-worker/swarm/graph LLM agents.

## 4. Tools & External Integrations

This repo does **not** wire LLM-agent tools (no MCP, browser agents, web-search tools, vector DB RAG, or model API tool-calling).

External integrations that do exist are systems/security/build integrations:

- Intel SGX runtime interfaces (`sgx_create_enclave`, enclave lifecycle) in sample apps, e.g. `SampleCode/LocalAttestation/App/App.cpp:58-93`.
- OpenSSL crypto initialization/use in simulation and signing paths, e.g. `sdk/simulation/urtssim/enclave_creator_sim.cpp:49-57`.
- OS signal/memory/thread primitives for instruction/emulation flow, e.g. `sdk/simulation/uinst/u_instructions.cpp:83-241`.
- Build/package automation via GNU Make, shell scripts, git submodules, and patching of external deps in `Makefile:50-145` and broader targets through `Makefile:77-569`.
- Attestation/service ecosystem integration (AESM/DCAP packaging targets) visible in installer/build targets in `Makefile:203-490`.

## 5. Notable Code Walkthrough

- `sdk/simulation/uinst/u_instructions.cpp:243-592` - Implements simulated SGX instruction handlers (`_ECREATE`, `_EADD`, `_EINIT`, `_SE3`, `_SE0`) and signal-handling behavior needed to emulate enclave transitions in software mode.
- `sdk/simulation/uinst/enclave_mngr.cpp:60-267` - Defines enclave identity generation and lifecycle bookkeeping (`CEnclaveSim`, `CEnclaveMngr`) used by simulation control paths to map addresses/TCS/pages to enclave instances.
- `sdk/simulation/urtssim/enclave_creator_sim.cpp:83-284` - Provides simulation-specific enclave creation/init/teardown and platform capability handling (`create_enclave`, `init_enclave`, `initialize`, `destroy_enclave`).
- `sdk/trts/trts_ecall.cpp:75-137` and `sdk/trts/trts_ecall.cpp:260-484` - Enforces ECALL authorization/dispatch and thread-context handling inside trusted runtime; central to runtime control flow.
- `SampleCode/LocalAttestation/App/App.cpp:58-94` - Representative user-facing flow: load enclaves, establish secure session, exchange messages, close session, destroy enclaves.

## 6. Use-Case Mapping

The assigned use case **Simulation** is partly valid: the repo includes explicit SGX simulation-mode runtime (`sdk/simulation/*`) and sample instructions to run apps in `SGX_MODE=SIM` (`README.md:392-399`). However, the repository is broader than simulation: it is a full SGX SDK/PSW production stack (hardware mode, packaging, attestation services, installers, etc.). For this agent-focused taxonomy, a better fit than “Simulation” is **Workflow Automation** at build/deployment level (large deterministic build/package workflows), but it is still **not** an LLM-agent system.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Mature, production-grade SGX lifecycle implementation with both hardware and simulation flows.
  - Clear separation of simulation runtime, trusted runtime, untrusted runtime, and installer packaging layers.
  - Strong low-level defensive checks (alignment, state, privilege, bounds) in enclave instruction and ECALL paths.
  - Comprehensive build/packaging coverage across distro/package targets (`.deb`, `.rpm`, installer binaries).
  - Includes practical sample applications demonstrating enclave creation and attestation/session flows.

- **Limitations:**
  - No LLM or agentic abstractions at all; unsuitable for studying modern MAS/LLM orchestration directly.
  - Large monorepo with heavy legacy/third-party footprint can make focused architectural comprehension difficult.
  - Significant complexity in platform/build matrix increases onboarding cost.
  - Many control paths are low-level C/C++ with manual state handling, raising maintenance and verification burden.

- **Research relevance:**
  - Useful evidence for deterministic secure-runtime orchestration (state-machine dispatch, trusted/untrusted boundary handling).
  - Relevant to enclave lifecycle simulation fidelity vs hardware execution behavior.
  - Good corpus for studying systems-level secure workflow automation (build/sign/package/deploy) rather than AI agents.
  - Can inform comparisons between rule-based runtime control and LLM-agent control paradigms.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
