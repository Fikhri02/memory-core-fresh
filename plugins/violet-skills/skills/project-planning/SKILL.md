---
name: project-planning
description: "Triggers on 'new project plan', 'new project plan for [name]', 'plan this brainstorm', 'plan brainstorm [name]', 'resume project plan [name]', 'archive project plan [name]', 'mark project plan [name] done'. Runs structured phase-by-phase planning for UX/Product Design (8 phases) or Software Feature (4 phases). Imports context and tasks from brainstorm sessions."
---

# Project Planning — Skill Plugin
*Triggers on 'new project plan', 'new project plan for [name]', 'plan this brains...*

## Activation

When this skill activates, output:

`"_(activates silently)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "new project plan"** | ACTIVE |
| **User says "plan this brainstorm"** | ACTIVE |
| **User says "plan brainstorm"** | ACTIVE |
| **User says "resume project plan"** | ACTIVE |
| **User says "archive project plan"** | ACTIVE |
| **User says "mark project plan"** | ACTIVE |
| **Mid-conversation (no trigger context)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### init-scratch

- [ ] **Step 1**: Ask for project name
- [ ] **Step 2**: Ask project type: UX/Product Design or Software Feature
- [ ] **Step 3**: Ask for context: project targets, key initial features (free-form, 3–5 sentences)
- [ ] **Step 4**: Show recap: "Project: [name] | Type: [type] | Context: [summary] — confirm?"
- [ ] **Step 5**: On confirm → create `project-plans/active/{name}.md`
- [ ] **Step 6**: If `project-management/{name}/` exists, link the plan into it so it is reachable
      from the project without being duplicated:
      `ln -s "$(pwd)/project-plans/active/{name}.md" "project-management/{name}/Plans/{name}-plan.md"`
      Skip if the project folder does not exist, or if the link is already there.
- [ ] **Step 7**: Begin Phase 1

**File format to use when creating:**

```markdown
# {Project Name}
**Type**: UX/Product Design | Software Feature
**Status**: in-progress
**Created**: YYYY-MM-DD
**Imported From**: none
**Current Phase**: 1

---

## Context
{project targets, key features}

---

## Phase 1 — {Phase Name}
**Status**: in-progress
**Completed**:

### Checklist
- [ ] Item 1

### Output
_(pending)_
```

---

### init-import

- [ ] **Step 1**: Load `brainstorming/active/{name}.md` — if not specified, use active brainstorm from current session
- [ ] **Step 2**: Pull Overall Summary → pre-fill as project context
- [ ] **Step 3**: Pull Task List → map unchecked tasks to relevant phases as pre-filled starting points
- [ ] **Step 4**: Ask project type: UX/Product Design or Software Feature
- [ ] **Step 5**: Show recap: "Importing from brainstorm: [name]. Context: [summary]. [N] tasks mapped across phases. Confirm?"
- [ ] **Step 6**: On confirm → create `project-plans/active/{name}.md`
- [ ] **Step 7**: If `project-management/{name}/` exists, link the plan into it so it is reachable
      from the project without being duplicated:
      `ln -s "$(pwd)/project-plans/active/{name}.md" "project-management/{name}/Plans/{name}-plan.md"`
      Skip if the project folder does not exist, or if the link is already there.
- [ ] **Step 8**: Begin Phase 1

---

### Phase Execution Loop

Runs for every phase in both project types:

1. AI presents phase name + checklist
2. For each checklist item: AI prompts → user provides input → AI assists/refines → mark item done
3. AI presents phase output summary
4. Ask: "Phase N complete — anything to adjust before we save and move on?"
5. On confirm → auto-save session notes to project plan file, notify: "Phase N notes saved — moving to Phase N+1"
6. Begin Phase N+1

---

### UX/Product Design — 8 Phases

**Phase 1 — Design Research & Problem Framing**
- [ ] Define user personas
- [ ] Identify core workflows
- [ ] Identify pain points, risks, and inefficiencies
- [ ] Create task breakdown per role
- [ ] Define key UX risks

Output: Personas · Workflow list · Pain points · Task matrix

**Phase 2 — UX Strategy**
- [ ] Define product design principles
- [ ] Define success metrics (speed, accuracy, error rate)
- [ ] Map high-level experience flows
- [ ] Define system constraints (offline, sync, validation)

Output: UX principles · Experience architecture · Feature prioritization (MVP vs future)

**Phase 3 — Interaction Design**
- [ ] Define full user flow
- [ ] Define UI state machine (idle, scanning, success, error, loading, offline, sync pending, retry)
- [ ] Define error scenarios and recovery paths
- [ ] Define feedback patterns (visual + behavioral)

Output: Flow diagrams · State machine definitions · Edge case handling

**Phase 4 — UI Design**
- [ ] Define screen structures
- [ ] Define layout hierarchy per screen
- [ ] Define visual priority
- [ ] Define mobile-first constraints

Output: Screen breakdown · Layout rules · UI hierarchy decisions

**Phase 5 — Design System**
- [ ] Define design tokens (colors, typography, spacing)
- [ ] Define reusable components
- [ ] Define component states

Output: Token system · Component inventory · Component specs

**Phase 6 — Prototyping & Testing**
- [ ] Define validation strategy
- [ ] Define usability test scenarios
- [ ] Define failure testing
- [ ] Define success criteria

Output: Test plan · Key usability scenarios

**Phase 7 — Engineering Handoff**
- [ ] Translate to engineering-ready specs (screen requirements, interaction rules, edge cases)
- [ ] Define API assumptions
- [ ] Define analytics events
- [ ] Define QA checklist

Output: Developer handoff spec

**Phase 8 — Implementation**
- [ ] Define technical requirements
- [ ] Break into engineering tasks
- [ ] Map to project plan

Output: Technical requirements · Engineering task list

---

### Software Feature — 4 Phases

**Phase 1 — Context Definition**
- [ ] Define the problem being solved
- [ ] Identify affected users/systems
- [ ] Define scope (what's in, what's out)
- [ ] List key constraints (tech stack, deadlines, dependencies)
- [ ] Define success criteria

Output: Problem statement · Scope definition · Constraints list · Success criteria

**Phase 2 — Requirements**
- [ ] Define functional requirements
- [ ] Define non-functional requirements (performance, security, reliability)
- [ ] Identify edge cases
- [ ] Define acceptance criteria per requirement
- [ ] Prioritize (must-have vs nice-to-have)

Output: Requirements list · Edge case log · Acceptance criteria · Priority matrix

**Phase 3 — Technical Architecture**
- [ ] Define system components and responsibilities
- [ ] Define data model / API contracts
- [ ] Define integration points
- [ ] Define error handling strategy
- [ ] Identify risks and mitigations

Output: Architecture overview · Data model · API contracts · Risk register

**Phase 4 — Implementation Spec**
- [ ] Break into engineering tasks
- [ ] Define task dependencies
- [ ] Estimate complexity per task
- [ ] Define QA/testing strategy
- [ ] Define rollout approach

Output: Engineering task list · Dependency map · Test strategy · Rollout plan

---

### resume

- [ ] **Step 1**: Load `project-plans/active/{name}.md`
- [ ] **Step 2**: Find last completed phase and current phase
- [ ] **Step 3**: Recap: "You're on Phase N — [phase name]. Last completed: Phase N-1. [X] checklist items remaining."
- [ ] **Step 4**: Continue from current phase

---

### status-transition

- [ ] **"archive project plan {name}"**:
  1. Prompt: "Reason for archiving?"
  2. Append `**Archive Reason**: {reason}` to the header block
  3. Move file to `project-plans/archived/{name}.md`
  4. Re-point any `project-management/*/Plans/{name}-plan.md` symlink at the new location, or remove
     it if the plan is no longer relevant to the project — never leave a dangling link
  5. Confirm: "Project plan {name} archived."

- [ ] **"mark project plan {name} done"**:
  1. Update `**Status**:` field to `complete`
  2. Move file to `project-plans/done/{name}.md`
  3. Re-point any `project-management/*/Plans/{name}-plan.md` symlink at the new location — never
     leave a dangling link
  4. Confirm: "Project plan {name} marked as done."

## Rules

1. Never skip phases — all phases must be completed in order
2. Never jump to UI or code without completing prior phases (UX type)
3. Always define requirements before architecture (Software type)
4. Stop on each phase for user confirmation before proceeding
5. Auto-save session notes after each phase approval with notification
6. Import pulls both Overall Summary AND Task List from brainstorm file
7. 'plan this brainstorm' with no active session brainstorm: prompt 'Which brainstorm?' and search brainstorming/active/
8. Always think in systems, not screens (UX type)
9. Only ever symlink a plan file that exists. A speculative symlink to a plan "that will be written
   later" just rots — create the link when the plan is created, and move it when the plan moves

## Level History

- **Lv.2** — Current behaviour, as described in the Protocol and Rules above
