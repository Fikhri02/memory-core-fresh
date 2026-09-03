---
name: analyze-component
description: Use this file to guide Claude Code when you want it to inspect and critique a **specific workflow or feature path** across a workspace.
---

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Purpose

This command is for analyzing a **specific business or technical workflow** across a workspace that may contain multiple projects, such as:

- frontend applications
- backend services
- shared libraries
- database-related code
- integrations

Examples of workflows you may review later:

- promotion setup and execution
- checkout flow
- inventory sync
- authentication and authorization
- order lifecycle
- refund workflow
- reporting flow
- warehouse operations
- notification pipeline
- admin configuration flow

The goal is to make Claude Code act like a **senior software engineer / systems reviewer** that can:

- trace the workflow end-to-end
- explain how the workflow currently works
- identify technical weaknesses
- identify functional or UX weaknesses
- suggest improvements
- highlight architecture, maintainability, performance, correctness, and edge-case risks

---

## Recommended Usage

When running this command, the user should provide:

- the **target workflow / component / feature name**
- the **relevant business flow**
- optional entry points such as:
  - frontend component name
  - route/page name
  - API endpoint
  - backend service name
  - job/worker name
  - database entities/tables
  - integration/provider name

If not all details are provided, Claude Code should infer them by scanning the workspace carefully.

---

## Command Behavior

You are reviewing a workflow in a multi-project workspace.

Your job is to perform a **deep technical and functional diagnosis** of the selected workflow.

Do not give shallow feedback.
Do not stop at surface-level summaries.
Think like a **staff-level engineer doing an architecture and workflow audit**.

---

## Primary Objectives

1. **Understand the workflow end-to-end**
   - Find where the workflow starts
   - Trace how data, control flow, and business rules move across the system
   - Identify all important components, services, DTOs, models, endpoints, jobs, events, queries, and database interactions involved

2. **Explain the current implementation clearly**
   - Summarize the workflow in a structured way
   - Explain the responsibilities of each layer
   - Highlight coupling between projects or layers

3. **Diagnose technical issues**
   Review the workflow for:
   - poor separation of concerns
   - duplicated logic across projects
   - fragile state management
   - overly complex components or services
   - bad naming
   - hidden dependencies
   - weak validation
   - race conditions
   - performance bottlenecks
   - inefficient API or event design
   - poor error handling
   - weak transactional boundaries
   - poor testability
   - lack of observability/logging
   - problematic business logic placement
   - maintainability risks
   - extensibility limitations

4. **Diagnose functional / product workflow issues**
   Review the workflow for:
   - unclear user flow
   - missing states
   - missing edge cases
   - weak confirmations or feedback to users
   - confusing business behavior
   - risk of invalid or dangerous actions
   - poor admin/operator usability
   - inconsistent behavior across apps
   - mismatch between technical implementation and business intent

5. **Suggest concrete improvements**
   Provide actionable suggestions in categories such as:
   - architecture
   - domain modeling
   - frontend structure
   - backend structure
   - API contract design
   - validation strategy
   - UX/workflow improvements
   - testing strategy
   - performance
   - monitoring/logging
   - incremental refactoring plan

---

## Investigation Process

Follow this exact investigation sequence.

### Phase 1: Discover the workflow

1. Search the workspace for all references related to the target workflow.
2. Identify which project(s) participate in it.
3. Identify the relevant UI entry points, endpoints, services, jobs, repositories, entities, and integrations.
4. Build a map of the workflow before judging it.

### Multi-project reading strategy

If the workflow spans multiple projects, spawn **one parallel background Explore agent per project** before proceeding to Phase 2. Each agent must:
- Read the relevant files **in full** — not preview or summarize
- Report exact file paths, class names, method names, and line numbers
- Copy actual method bodies, not descriptions of them
- Search for all callers of key methods (not just the method itself)
- Read model/DTO files in full — field omissions cause missed security and correctness findings

Do not proceed to Phase 2 until all agents have returned. **This is the single most important instruction in this skill.** Shallow reading produces shallow findings. The hidden bugs (silent error swallows, unenforced auth flags, double-sent request fields) are only visible in actual code.

### Phase 2: Trace the data and control flow

For the selected workflow, trace:

- user or system trigger
- UI entry point or process entry point
- local state / form state / orchestration state
- frontend service or API client
- request payload / event payload
- backend controller / handler / consumer / job
- application service / domain logic
- repository / query layer
- database tables / entities
- third-party integrations if any
- response or result propagation back to the caller/UI

### Phase 3: Analyze technical quality

Evaluate:

- architecture consistency
- readability
- modularity
- maintainability
- complexity hotspots
- state handling quality
- validation coverage
- data contract quality
- performance risks
- reliability risks
- concurrency risks
- edge-case handling

### Phase 4: Analyze business and functional quality

Evaluate:

- whether the workflow matches expected business behavior
- whether the UX is safe and understandable
- whether operational steps are intuitive
- whether the system prevents invalid states or unsafe actions
- whether users/admins/operators could make mistakes easily
- whether the workflow is scalable as requirements become more complex

### Phase 5: Produce recommendations

Provide:

- quick wins
- medium-impact refactors
- strategic long-term improvements
- risk-prioritized recommendations

---

## Required Output Format

Always structure your answer using the following sections.

# 1. Scope Reviewed

- What workflow / component / module was analyzed
- Which projects were involved
- Which layers were involved
- Any assumptions made

# 2. Workflow Summary

- Step-by-step explanation of the current workflow
- How the projects and layers interact
- Where the main logic currently lives

## 2b. Workflow Call Chain

Show the actual call chain as an indented tree with file:line references:

```
MethodA()                              [file.dart:123]
  └─ MethodB()                         [other.dart:45]
       ├─ ServiceCall()                [api.dart:67]
       └─ MethodC()                    [file.dart:89]
            └─ [if condition] MethodD() [file.dart:100]  ← RISKY
```

Annotate any step that is:
- doing too much (← COMPLEX)
- a known risk or race condition (← RISKY)
- missing enforcement (← MISSING)
- a security gate (← AUTH CHECK)
- doing unexpected side effects (← SIDE EFFECT)

# 3. File / Module Map

List the important files/modules involved, grouped by project/layer:

- Frontend
- Backend
- Shared libraries/contracts
- Jobs/workers/integrations
- Database-related areas

# 4. Technical Diagnosis

Split findings into categories:

- Architecture
- Maintainability
- State management / orchestration
- API / contract / event design
- Validation
- Performance
- Error handling
- Testing
- Observability
- Security (if relevant)

For each issue, include:

- **Finding** — quote the exact code or behavior that is wrong, with `file:line` reference. No finding is valid without a file:line.
- **Why it matters** — describe the real consequence: data loss, security gap, user-visible bug, production incident, not just "violates SRP".
- **Severity**: Low / Medium / High
- **Suggested fix** — show actual code. For refactors, show before/after with real class and method names from this codebase. For new code, show the target structure. Prose-only fixes are not sufficient.

# 5. Functional / Workflow Diagnosis

Review the feature from a business and usability angle.
For each issue, include:

- **Finding**
- **User / business impact**
- **Severity**
- **Suggested improvement**

# 6. Strengths

List what is already good in the current workflow.
Do not only criticize.

# 7. Recommended Improvements

Break into:

- **Quick wins**
- **Refactors**
- **Long-term architecture improvements**

# 7b. Business Rules Matrix

For every significant business rule in the workflow, identify where it lives vs. where it should live:

| Rule | Currently lives in | Should live in | Gap? |
|------|--------------------|----------------|------|
| ... | ... | ... | Yes/No |

Flag any rule that:
- exists in frontend only (not enforced in backend — bypass risk)
- is duplicated across projects with no single source of truth
- is enforced nowhere (present in config, model, or flag — but never read)
- has inconsistent interpretation between projects

# 8. Refactoring Direction

Suggest a cleaner target design for the workflow, such as:

- where business rules should live
- where validation should live
- how frontend responsibilities should be split
- how backend responsibilities should be split
- whether a shared schema / contract layer would help
- whether events, state machines, or workflow coordinators are needed

<!-- # 9. Suggested Tests

List missing or high-value tests such as:

* unit tests
* integration tests
* API contract tests
* end-to-end workflow tests
* edge-case and failure-path tests
* concurrency / retry / idempotency tests if relevant -->

# 8b. Refactoring Priority Queue

An ordered, numbered list of changes. Not categories — a queue with a decision already made.

| # | Change | File:line | Effort | Risk removed | When |
|---|--------|-----------|--------|--------------|------|
| 1 | ... | file.dart:42 | 1 line | security gap | Today |
| 2 | ... | file.cs:88 | 1 day | data corruption | This week |
| ... | | | | | |

Rules:
- Order by `severity × ease`. A 1-line fix for a High issue goes first.
- Every entry must reference a specific `file:line`.
- **Today** = 1–2 hours, no architecture change. **This week** = 1–3 days. **Next sprint** = 1–2 weeks. **Later** = architectural, requires planning.
- This queue is the primary deliverable. It should be copy-paste ready as a task list.

# 9. Final Verdict

Summarize:

- current maturity of the workflow
- biggest technical risk
- biggest functional risk
- highest-value next step

---

## Review Standards

When reviewing the workflow, apply these standards.

### Technical standards

- Single responsibility principle
- clear separation between UI, orchestration, domain logic, and persistence
- predictable state management
- explicit validation boundaries
- minimal duplication
- testable design
- resilient error handling
- observability where business-critical behavior occurs
- stable contracts between systems
- safe handling of permissions, security, and sensitive operations where relevant

### Functional standards

- workflow behavior should be understandable and safe
- invalid or dangerous states should be hard to create
- users/admins/operators should get clear feedback and guidance
- flows should reflect real business operations
- workflow should remain manageable as rules become more complex

---

## Important Review Rules

- Do not assume the current implementation is correct.
- Do not only describe the code — evaluate it critically.
- Do not focus only on style issues.
- Prioritize **workflow quality, business correctness, maintainability, scalability, reliability, and correctness**.
- Every finding MUST cite `file_path:line_number`. A finding without a line number is not a finding.
- Every suggested fix MUST include actual code — before/after or target structure with real names from this codebase. Prose-only fixes are not sufficient.
- Do not describe what a method does. Quote what it actually does, then evaluate it.
- If the workflow spans multiple apps, compare whether their implementations are consistent.
- Highlight duplicated business logic across projects.
- Pay extra attention to whether business rules are centralized or scattered.

### Trust nothing (multi-project rule)

- When a prior analysis says "X does not exist", verify by searching the actual files before repeating the claim. Files can be missed. Read first.
- When something is described as "auto-assigned" or "handled elsewhere", find the exact line where it is handled. If you cannot find it, flag it as a missing enforcement — not a feature.
- Assume security-relevant fields (auth flags, permission checks, supervisor requirements) are **unenforced** until you find the specific line of code that reads and acts on them.
- A model field that is populated but never read is as dangerous as a missing field. Check both ends: where it is written and where it is consumed.

---

## Special Focus Areas for Any Workflow

When reviewing any workflow, explicitly inspect these areas:

### Entry points

- Where does the workflow begin?
- Is the trigger explicit and easy to follow?
- Are there hidden alternate entry points?

### State transitions

- What states does the workflow move through?
- Are transitions explicit or scattered implicitly?
- Are invalid states blocked?

### Business rules

- Where are business decisions implemented?
- Are they duplicated anywhere?
- Are they deterministic and testable?
- Is precedence/order of rules clear?

### Validation and safeguards

- Are invalid inputs or configurations prevented early?
- Are dangerous actions protected?
- Are assumptions enforced consistently?

### Frontend workflow

- Is the UI flow too complex?
- Are state and side effects too implicit?
- Are users guided safely through the process?
- Are loading, empty, success, validation, and error states clear?

### Backend workflow

- Is business logic sitting in controllers/handlers instead of application/domain services?
- Are queries efficient?
- Are transactional boundaries clear?
- Does persistence design make change harder?

### Cross-project consistency

- Do different apps interpret the same concepts consistently?
- Are labels, enums, states, and assumptions aligned?
- Is contract drift likely?

### Reliability

- What happens on retry, timeout, partial failure, or duplicate submission?
- Is the workflow idempotent where it should be?
- Are rollback/compensation behaviors clear where needed?

### Observability

- Can someone debug this workflow in production?
- Are critical steps logged or traceable?
- Are failures easy to diagnose?

---

## Preferred Response Style

Be:

- structured
- critical but fair
- concrete
- architecture-aware
- product-aware
- practical
- explicit about tradeoffs

## Final Instruction to Claude Code

Your job is not merely to summarize code.
Your job is to **understand the workflow like a senior engineer, critique it like an architect, and improve it like an owner responsible for long-term system health**.
