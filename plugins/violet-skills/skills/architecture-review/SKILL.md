---
name: architecture-review
description: "Use when user says 'architecture review', 'review architecture', 'study architecture', 'document architecture', 'review tech stack', or 'assess tech stack'. Studies a repository's architecture and stack from real file evidence — inventories technologies, weighs the pros and cons of each in context, and ranks improvements — then writes the result to notes/architecture-review/{project}.md. Evidence before opinion: nothing is named that cannot be tied to a file."
---

# Architecture Review — Skill Plugin
*Reads a codebase and produces a grounded architecture document: what the stack actually is, what each choice costs, and what to fix first.*

## Activation

When this skill activates, output:

`"Reviewing the architecture..."`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "architecture review"** | ACTIVE → review-write |
| **User says "review architecture"** | ACTIVE → review-write |
| **User says "study architecture"** | ACTIVE → review-write |
| **User says "document architecture"** | ACTIVE → review-write |
| **User says "review tech stack"** | ACTIVE → review-write |
| **User says "assess tech stack"** | ACTIVE → review-write |
| **User says "list architecture reviews"** | ACTIVE → review-list |
| **Mid-conversation (no trigger context)** | DORMANT |

There is **no passive trigger**. A full review is an expensive read pass over a whole repository —
it runs when asked, never on its own initiative.

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

This skill is like `sync-git` and `log-debugging`: it reads a **code repository** (your working
directory) and writes to the **memory root**. Keep the two straight. The review document never
lands in the repository being reviewed.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Independence

This skill does **not** touch `project-management/`. It does not resolve a tracked project, does
not write a Timeline entry, and does not symlink itself anywhere. It reviews whatever repository
is in front of it and writes one file under `notes/architecture-review/`. A repo that has never
been documented as a project is reviewed exactly the same way as one that has.

## The core rule

**Evidence before opinion.** Never name a technology or make a claim you cannot tie to a file in
the repository. Inventory first, analyse second, write last. A stack you assume is present because
the framework usually ships with it is not evidence.

## Protocol

### review-write

- [ ] **Step 1 — Identify the subject.** Derive, in this order and stopping at the first hit:
      - **Project name**: the `name` field of a manifest at the repo root — `package.json`,
        `pyproject.toml` (`[project].name`), `Cargo.toml` (`[package].name`), `composer.json`,
        the last segment of `go.mod`'s `module` line — else the repo name from the git origin,
        else the directory basename
      - **Git repo link**: `git remote get-url origin`, normalised to an https URL (strip any
        embedded credentials; rewrite `git@host:owner/repo.git` as `https://host/owner/repo`).
        No remote means record the absolute local path instead
      - **Ref**: current branch and short HEAD SHA (`git rev-parse --abbrev-ref HEAD`,
        `git rev-parse --short HEAD`)
      - **Slug**: the project name lowercased and hyphenated — this is the filename
- [ ] **Step 2 — Check for an existing review.** If `notes/architecture-review/{slug}.md` exists,
      stop and ask before writing: overwrite it, or preserve the current one as
      `{slug}-{YYYY-MM-DD}.md` (its own `Reviewed` date) first. **Never silently overwrite** — a
      review is a dated snapshot, and the previous one is how drift becomes visible
- [ ] **Step 3 — Gather evidence.** Read before concluding. Collect, and note the path of each
      file that proves something:
      - **Dependency manifests & lockfiles** — `package.json`, `package-lock.json`, `yarn.lock`,
        `pnpm-lock.yaml`, `requirements.txt`, `pyproject.toml`, `poetry.lock`, `go.mod`,
        `pom.xml`, `build.gradle`, `Cargo.toml`, `Gemfile`, `composer.json`
      - **Runtime & infra** — `Dockerfile`, `docker-compose.yml`, Kubernetes/Helm manifests,
        Terraform/Pulumi, `Procfile`, serverless and platform configs
      - **CI/CD** — `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`
      - **Structure** — the directory tree 2–3 levels deep, entry points (`main`, `index`, `app`,
        server bootstrap), module boundaries
      - **Data layer** — schema files, migrations, ORM models, `*.sql`, security/access rules
      - **Config** — `.env.example`, config files, feature flags
      - **Docs** — `README`, `ARCHITECTURE.md`, ADRs under `docs/adr/`, diagrams
      Tag every technology **[observed]** (found directly in a manifest or config) or
      **[inferred]** (deduced from code patterns, with the pattern named)
- [ ] **Step 4 — Identify the pattern.** Name the overall architecture from the evidence:
      monolith, modular monolith, microservices, layered/n-tier, hexagonal/clean, event-driven,
      serverless, client-server, MVC. State what in the repo indicates it — folder layout, service
      boundaries, message brokers, API gateways. **"Mixed" and "unclear" are valid answers**; say
      so rather than forcing a label
- [ ] **Step 5 — Analyse.** For each major layer or choice, weigh advantages *and* disadvantages
      **as used in this project**, not as a textbook feature list. Then derive improvements ranked
      by impact against effort
- [ ] **Step 6 — Write** `notes/architecture-review/{slug}.md` in the document format below
- [ ] **Step 7 — Verify.** Do not skip:
      - Cross-check every technology in the document against a real dependency or config file.
        Remove or re-tag anything unprovable
      - Confirm every major choice carries both an advantage and a disadvantage
      - Confirm improvements are ranked, not a flat wish list
      - Confirm section 6 states what could not be determined and what was not examined
- [ ] **Step 8 — Report** the path written, the tech count, and the top three recommendations

### review-list

- [ ] List `notes/architecture-review/*.md`, one line each — slug, project name, reviewed date,
      branch/commit. Dated snapshots (`{slug}-{date}.md`) group under their current review

## Document Format

```markdown
# Architecture Review: {Project Name}

**Project**: {project name}
**Git repo link**: {https origin URL, or the absolute local path when there is no remote}
**Branch / commit**: {branch} @ {short SHA}
**Reviewed**: YYYY-MM-DD
**Reviewer**: Claude

---

## 1. Executive summary

{2–4 sentences: what the system is, its dominant architecture pattern, and the single most
important finding.}

## 2. Architecture pattern

{The overall pattern(s), with the concrete files and structure that indicate it.}

{A Mermaid or plain-text diagram of the main components and how they connect — include one only
when the component boundaries are genuinely visible in the evidence. A single-box diagram of a
flat repo adds nothing; say the structure is flat instead.}

## 3. Tech stack inventory

| Layer | Technology | Version | Evidence (file) | Confidence |
|-------|-----------|---------|-----------------|------------|
| Frontend | | | | observed |
| Backend | | | | observed |
| Data | | | | observed |
| Infra/Deploy | | | | observed |
| CI/CD | | | | observed |
| Observability | | | | inferred |
| Testing | | | | observed |
| Auth | | | | observed |

{Group by layer. Omit a layer entirely rather than inventing a row for it.}

## 4. Advantages & disadvantages

### {Technology / choice}

**Advantages**
- {grounded in how it is used here}

**Disadvantages / risks**
- {grounded in how it is used here}

## 5. Recommended improvements

| # | Recommendation | Area | Impact | Effort | Rationale |
|---|----------------|------|--------|--------|-----------|
| 1 | | | High | Low | |

{Order: quick wins (high impact / low effort) first, then strategic bets, then nice-to-haves.}

## 6. Open questions & not examined

- **Could not be determined**: {…}
- **Assumptions made**: {…}
- **Not examined**: {…}
```

## Rules

1. **No unproven tech.** If it is not in a manifest, a config, or plainly in the code, it does not
   go in the table — or it goes in tagged `[inferred]` with the reason stated
2. **Balance is mandatory.** Every major choice gets both an advantage and a disadvantage. No pure
   praise, no pure criticism. A choice you cannot fault is a choice you have not examined
3. **Context over textbook.** "Advantages of Postgres" must be about *this* project's usage. Generic
   feature lists are padding and get cut
4. **Prioritise, don't dump.** Improvements are ranked by impact × effort with a one-line rationale
   each. An unranked list of twelve ideas is not a recommendation
5. **State scope, always.** Record what was examined and what was not. Sampling is fine; silent
   sampling is not
6. **Separate fact from opinion.** Inventory and pattern are fact and get cited. Pros, cons, and
   improvements are judgment and get reasoned
7. **Read-only on the code repo.** This skill inspects code and writes one memory file. It changes
   nothing in the repository under review
8. **Never overwrite a review unasked.** Step 2 asks. The previous snapshot is what makes drift
   legible
9. **Never touches `project-management/`.** No project resolution, no Timeline entry, no symlink —
   see **Independence** above

## Scope Handling

| Repo shape | Behaviour |
|-----------|-----------|
| **Monorepo** | Identify each package or service, give each its own stack rows, note shared tooling once, and say in section 6 which packages were sampled |
| **Very large repo** | Prioritise entry points, shared libraries, and dependency manifests; list explicitly what was sampled versus skipped |
| **Sparse repo / no manifests** | Fall back to code patterns and imports, tag findings `[inferred]`, and lower the stated confidence |
| **Polyglot repo** | One inventory table, layer rows grouped by language; name the boundary between the runtimes in section 2 |

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| Review for this slug already exists | Ask: overwrite, or preserve the old one as `{slug}-{date}.md` first. Never decide alone |
| Working directory is not a git repository | Record the absolute path as the repo link; leave branch and commit blank |
| No remote named `origin` | Use the first remote listed; if there are none, record the local path |
| Repo has no manifest of any kind | Derive the name from the directory basename and run the sparse-repo path — the review still gets written |
| Uncommitted changes in the working tree | Note it under the `Branch / commit` line — the review describes the tree as read, not as committed |
| Two projects live in one repo | Review the repo once, split section 3 per package, and say so in section 6. Do not write two files |
| A technology appears in a lockfile but nowhere in the code | Tag it `[inferred]`, note it as possibly dead weight, and consider it for section 5 |
| User asks to review a repo that is not the working directory | Ask for the path first; never guess which checkout is meant |

## Level History

- **Lv.1** — Base: evidence-first inventory with observed/inferred tagging, architecture-pattern
  identification, balanced per-choice analysis, impact × effort ranked improvements, and a verify
  pass; writes `notes/architecture-review/{project}.md` with project name and git URL in the header;
  independent of `project-management/`
