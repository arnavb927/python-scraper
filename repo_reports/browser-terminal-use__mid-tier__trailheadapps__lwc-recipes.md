---
repo_name: trailheadapps/lwc-recipes
url: "https://github.com/trailheadapps/lwc-recipes"
stars: 2848
forks: 3239
contributors_count: 45
last_commit_date: "2026-04-23T06:29:39+00:00"
primary_use_case: Browser / Terminal Use
user_tier: Mid-Tier
total_score: 5
architecture_labels: [CrewAI]
use_case_labels: [Workflow Automation, RAG + Agents, Browser / Terminal Use]
generated_at: "2026-04-27T13:58:21.479712+00:00"
model: auto
duration_s: 90.8
clone_size_kb: 4571
uses_mas: no
final_use_case: None
---
## 1. Overview

`trailheadapps/lwc-recipes` is a Salesforce sample app containing many small Lightning Web Components (LWC) and Apex examples that demonstrate platform APIs and UI patterns, not an agent runtime. A developer deploys it to a Salesforce org and interacts with tabs/components (data access, messaging, navigation, REST calls, workspace APIs, etc.) to learn implementation patterns through working code. The repo includes client-side LWC components, server-side Apex controllers, metadata, and Jest tests. What users get is a hands-on cookbook for Salesforce frontend/backend integration, plus walkthrough prompts embedded as Salesforce metadata.

## 2. Agent Framework & Architecture

No LLM-agent framework is used in this repository. I found no runtime imports or wiring for LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, OpenAI/Anthropic SDKs, or similar agent orchestration libraries in project dependencies (`package.json:6-55`) or application code.

The architecture is a Salesforce app architecture: LWCs on the client, Apex classes for server-side business/data access, and Salesforce platform services (wire adapters, Lightning Message Service, metadata-defined walkthrough prompts). For example, components call Apex methods (`compositionContactSearch` -> `ContactController.findContacts`) and subscribe/publish via Lightning Message Service (`lmsPublisherWebComponent`, `lmsSubscriberWebComponent`).

The files under `force-app/main/default/prompts/*.prompt-meta.xml` are Salesforce Prompt metadata for UI walkthrough panels (step text, display positions, navigation targets), not LLM prompts or autonomous planning logic (`HelloWalkThrough.prompt-meta.xml:3-106`, `DataWalkthrough.prompt-meta.xml:3-107`).

## 3. Orchestration Pattern

Closest match: **event-driven UI orchestration** (not multi-agent orchestration).

Control flow is driven by user events and framework events, then routed to platform APIs/Apex. Example: debounced input triggers an Apex call:

```11:26:force-app/main/default/lwc/compositionContactSearch/compositionContactSearch.js
handleKeyChange(event) {
    window.clearTimeout(this.delayTimeout);
    const searchKey = event.target.value;
    this.delayTimeout = setTimeout(async () => {
        try {
            this.contacts = await findContacts({ searchKey });
            this.error = undefined;
        } catch (error) {
            this.error = error;
```

Another event path uses publish/subscribe messaging between components:

```15:20:force-app/main/default/lwc/lmsPublisherWebComponent/lmsPublisherWebComponent.js
// Respond to UI event by publishing message
handleContactSelect(event) {
    const payload = { recordId: event.target.contact.Id };
    publish(this.messageContext, RECORD_SELECTED_CHANNEL, payload);
}
```

```50:67:force-app/main/default/lwc/lmsSubscriberWebComponent/lmsSubscriberWebComponent.js
subscribeToMessageChannel() {
    this.subscription = subscribe(
        this.messageContext,
        RECORD_SELECTED_CHANNEL,
        (message) => this.handleMessage(message)
    );
}
connectedCallback() {
    this.subscribeToMessageChannel();
}
```

## 4. Tools & External Integrations

This repo does **not** wire LLM-agent tools (no MCP servers, no browser automation stack, no vector DB, no RAG pipeline, no terminal-acting agent runtime).

External/platform integrations present in code:

- Salesforce Apex RPC from LWC via `@salesforce/apex/...` imports (`compositionContactSearch.js:1-27`, `lmsPublisherWebComponent.js:1-21`).
- Salesforce database access in Apex SOQL/DML (`ContactController.cls:2-67`).
- Lightning Message Service for inter-component pub/sub (`lmsPublisherWebComponent.js:4-20`, `lmsSubscriberWebComponent.js:6-67`).
- Lightning Data Service wire adapters (`lmsSubscriberWebComponent.js:2-43`).
- Direct browser `fetch` to Google Books API example (`miscRestApiCall.js:3-35`), with CSP note in code.
- GitHub source-linking helper component (`viewSource.js:4-11`) for navigating recipe source.

## 5. Notable Code Walkthrough

- `force-app/main/default/lwc/miscRestApiCall/miscRestApiCall.js:3-35` - Demonstrates client-side external REST integration using `fetch`, including loading/error handling and response parsing.
- `force-app/main/default/classes/ContactController.cls:2-67` - Core Apex controller exposing `@AuraEnabled` methods for querying/updating contacts; representative of server-side contract LWCs consume.
- `force-app/main/default/lwc/compositionContactSearch/compositionContactSearch.js:1-27` - Shows UI-to-Apex orchestration with debounce logic to avoid excessive server calls.
- `force-app/main/default/lwc/lmsPublisherWebComponent/lmsPublisherWebComponent.js:4-20` - Publishes selected record IDs over Lightning Message Service, illustrating decoupled component communication.
- `force-app/main/default/lwc/lmsSubscriberWebComponent/lmsSubscriberWebComponent.js:34-79` - Subscribes to message channel, reacts by loading record data via wire adapter, and reports errors with toasts.

## 6. Use-Case Mapping

The assigned primary use case **Browser / Terminal Use** looks incorrect for this repository. This project is a **Salesforce educational sample app**, not an agent that controls a browser or terminal.

It also does not implement multi-agent workflow automation, RAG, simulation, or code generation. The closest taxonomy outcome from the allowed list is therefore **None**: it is a UI/component recipe library demonstrating platform APIs and integration patterns rather than agentic behavior.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad, concrete coverage of Salesforce LWC/Apex integration patterns in runnable examples.
  - Clear separation between UI components and server methods (`LWC` + `@AuraEnabled` Apex).
  - Strong use of platform-native event/messaging patterns (LMS, wire adapters).
  - Includes test scaffolding/mocks for many components (`sfdx-lwc-jest` setup in `package.json`).
  - Metadata-driven walkthrough content helps guided learning in-app (`prompts/*.prompt-meta.xml`).

- **Limitations:**
  - No LLM integration, no agent policies, no planner/router, no coordinated multi-agent runtime.
  - No autonomous tool-use loop; all flows are user/UI-event initiated.
  - “Prompt” files are instructional UI metadata, not model prompts/execution chains.
  - Not designed as a general automation framework; tightly coupled to Salesforce runtime.
  - Limited relevance to agent safety/evaluation research beyond negative evidence (absence of agents).

- **Research relevance:**
  - Useful as a **non-agent baseline** when comparing agentic vs. traditional event-driven app architectures.
  - Evidence that heuristic repository labeling can misclassify “prompt”-containing repos as agentic.
  - Illustrates mature enterprise UI/service orchestration without LLMs (helpful control group).
  - Can support studies on platform-native orchestration patterns distinct from MAS paradigms.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: None
