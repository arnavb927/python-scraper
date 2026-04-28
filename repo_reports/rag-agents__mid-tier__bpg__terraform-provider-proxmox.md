---
repo_name: bpg/terraform-provider-proxmox
url: "https://github.com/bpg/terraform-provider-proxmox"
stars: 1975
forks: 272
contributors_count: 170
last_commit_date: "2026-04-21T01:41:37+00:00"
primary_use_case: RAG + Agents
user_tier: Mid-Tier
total_score: 4
architecture_labels: [CrewAI]
use_case_labels: [RAG + Agents]
generated_at: "2026-04-27T15:08:56.927462+00:00"
model: auto
duration_s: 76.0
clone_size_kb: 7405
uses_mas: no
final_use_case: Workflow Automation
---
## 1. Overview

`bpg/terraform-provider-proxmox` is a Terraform/OpenTofu provider that lets users manage Proxmox VE infrastructure declaratively (VMs, storage, networking, ACLs, HA, SDN, etc.). Users run standard Terraform workflows (`terraform plan/apply`) against this provider, and it translates desired state into Proxmox API and SSH operations. The codebase has two provider implementations (legacy SDK and newer Terraform Plugin Framework) muxed into one plugin binary. This repository solves infrastructure lifecycle automation for Proxmox clusters, not conversational or LLM-based tasks.

## 2. Agent Framework & Architecture

No LLM agent framework is used. I found no LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex/OpenAI/Anthropic-style runtime imports in Go source or `go.mod` (`go.mod:7-30`, `go.mod:32-102`), and the entrypoint is a Terraform plugin server (`main.go:209-258`).

Architecture is Terraform-provider-centric: `main.go` starts a mux server combining Framework and SDK providers (`main.go:217-237`), `fwprovider/provider.go` defines provider schema/config and registers resources/data sources (`fwprovider/provider.go:122-292`, `fwprovider/provider.go:558-730`), and resource handlers implement CRUD against Proxmox clients (example VM resource in `fwprovider/nodes/vm/resource.go:98-426`). Intelligence is deterministic domain logic (schema validation, retries, polling, state reconciliation), not prompts/planners/LLM routing.

The word “agent” in this repo refers to SSH agent authentication and QEMU guest agent features (e.g., `proxmox/ssh/client.go:95-107`, `proxmox/nodes/vms/custom_agent.go:18-23`), not AI agents.

## 3. Orchestration Pattern

Closest match: **sequential workflow automation** (deterministic request orchestration), not multi-agent orchestration.

Control flow is linear from Terraform RPC → provider/resource method → Proxmox API/SSH client calls. Example from plugin startup:

```go
providers := []func() tfprotov6.ProviderServer{
    providerserver.NewProtocol6(fwprovider.New(version)()),
    func() tfprotov6.ProviderServer { return upgradedSdkServer },
}
muxServer, err := tf6muxserver.NewMuxServer(ctx, providers...)
```

Source: `main.go:229-237`.

Example from VM lifecycle orchestration (create then read-back state):

```go
r.create(ctx, plan, &resp.Diagnostics)
exists := read(ctx, r.client, &plan, &resp.Diagnostics)
if !exists {
    resp.Diagnostics.AddError("VM does not exist after creation", "")
}
```

Source: `fwprovider/nodes/vm/resource.go:128-138`.

## 4. Tools & External Integrations

- **Terraform plugin protocols/framework** (core integration surface): plugin server + mux for SDK/Framework providers in `main.go:14-24`, `main.go:217-255`; provider/resource schema machinery in `fwprovider/provider.go:15-24`.
- **Proxmox VE HTTP API**: request construction, auth, retries, response validation in `proxmox/api/client.go:36-60`, `proxmox/api/client.go:149-307`.
- **SSH to Proxmox nodes**: remote command execution, SFTP/stream uploads, optional SSH-agent forwarding in `proxmox/ssh/client.go:60-75`, `proxmox/ssh/client.go:192-305`, `proxmox/ssh/client.go:307-592`.
- **Retry/poll subsystem** for resilient infra operations: task/API/poll operation wrappers in `proxmox/retry/retry.go:82-163`, `proxmox/retry/retry.go:165-256`.
- **QEMU guest agent integration** (Proxmox VM feature, not LLM): parsing/encoding agent config in `proxmox/nodes/vms/custom_agent.go:18-84`, plus VM agent network/status interactions in `proxmox/nodes/vms/vms.go` (agent endpoints).
- **LLM/RAG/vector DB/browser automation/MCP tools**: does not apply; no runtime wiring found in source.

## 5. Notable Code Walkthrough

- `main.go:209-258` — Provider binary entrypoint. Boots both Framework and legacy SDK implementations and serves as a Terraform registry plugin.
- `fwprovider/provider.go:295-556` — Provider `Configure` path: reads env/config, builds API credentials/connection, initializes SSH client and node resolvers, injects shared clients into resources/data sources.
- `fwprovider/nodes/vm/resource.go:98-247` — Representative resource CRUD flow (Create/Read/Update): transforms Terraform plan/state, calls Proxmox clients, reconciles computed fields.
- `proxmox/api/client.go:149-307` — Low-level Proxmox API execution path: request encoding, auth attachment, retry on transient transport issues, decode/validate responses.
- `proxmox/ssh/client.go:594-814` — SSH transport implementation including host key management, auth fallback (agent/private key/password), SOCKS5 proxy support.

## 6. Use-Case Mapping

The upstream label **“RAG + Agents”** appears incorrect for this repository. The code implements infrastructure provisioning workflows for Proxmox via Terraform, with deterministic control logic and API/SSH clients; there is no LLM invocation layer, retrieval pipeline, vector index, or coordinated AI agent runtime. A better category is **Workflow Automation**: users declare desired infra state, and the provider executes automated reconciliation against Proxmox APIs and node shells. This is automation-oriented orchestration, but not agentic-AI in the LLM sense.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Strong production-oriented integration breadth across Proxmox domains (VM, SDN, storage, HA, access) via modular clients/resources (`fwprovider/provider.go:558-730`).
  - Clear layered architecture (Terraform schema/resource layer over reusable API/SSH clients), which aids maintainability.
  - Robust retry/poll patterns for flaky infra operations (`proxmox/retry/retry.go:82-256`).
  - Backward compatibility strategy via SDK+Framework mux (`main.go:217-237`).

- **Limitations:**
  - No LLM/multi-agent runtime; unsuitable as evidence for agentic collaboration patterns.
  - “Agent” terminology can be misleading (SSH/QEMU agents only), increasing false positives in automated repo classification.
  - Complexity from dual-provider migration (SDK + Framework) may increase cognitive load for contributors.
  - Heavy reliance on external Proxmox environment for acceptance behavior makes isolated experimentation harder.

- **Research relevance:**
  - Useful evidence for **deterministic infrastructure workflow orchestration** in plugin ecosystems.
  - Good case study of reliability engineering (retries, polling, error taxonomy) in API-driven automation.
  - Illustrates migration architecture patterns (legacy/new framework coexistence) rather than multi-agent AI coordination.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Workflow Automation
