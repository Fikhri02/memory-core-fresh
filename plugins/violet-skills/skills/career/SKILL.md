---
name: career
description: "Use when the user says 'career profile', 'update my profile', 'find jobs', 'search jobs', 'job search', 'tailor cv for [job]', 'tailor my cv', 'cover letter for [job]', 'job status', 'job tracker', 'applied to [job]', 'update application [job]', 'save career', 'save job search', or asks to analyse jobs, tailor a CV, or track job applications."
---

# Career — Skill Plugin

_Keeps one sourced career profile, finds and documents jobs, tailors applications from that profile only, and tracks every application._

## Activation

When this skill activates, output:

`"_(career activates)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "career profile"** or **"update my profile"** | ACTIVE → career-profile |
| **User says "find jobs"**, **"search jobs"**, **"job search"** | ACTIVE → job-search |
| **User says "tailor cv for {job}"**, **"tailor my cv"**, **"cover letter for {job}"** | ACTIVE → tailor |
| **User says "job status"**, **"job tracker"**, **"applied to {job}"**, **"update application {job}"** | ACTIVE → track |
| **User says "save career"**, **"save job search"** | ACTIVE → save |
| **Any mode, but `career/profile.md` does not exist** | ACTIVE → career-profile first run, then the requested mode |
| **Mid-conversation (no trigger context)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### career-profile

**First run** (no `career/profile.md`):

- [ ] **Step 1**: Read `career/_template/structure.yaml` and create every folder and file it lists under `career/`, filling files from their templates. Never hardcode the list
- [ ] **Step 2**: Gather sources, read-only: the CV files the user names (offer the newest `*CV*` / `*Resume*` PDFs in `~/Downloads` as candidates and ask which are current), `main/main-memory.md`, every `project-management/*/General.md`, public repos via `gh repo list`, and the profile data of a portfolio site if the user names one
- [ ] **Step 3**: Draft `career/profile.md`. Every achievement and figure gets a **Source** cell (CV name, file path, repo, or "user, {date}"). Anything that appears in only one old CV with no other evidence goes under **Needs confirmation**, not Experience
- [ ] **Step 4**: Interview for the gaps, **one question per message**: target roles, seniority, location priority, work mode, salary expectation, notice period, work authorisation, must-haves, deal-breakers, industries, and what contact details may appear on a CV
- [ ] **Step 5**: Show the full draft and wait for approval before writing it
- [ ] **Step 6**: Build the master CV source in `career/cv/master/` (HTML with print CSS, A4, at most two pages) from `profile.md` only, render it to `outputs/career-cv/master.pdf` with headless Chrome (`--headless=new --print-to-pdf`), open the PDF to check it, and show it to the user

**Later runs** (profile exists):

- [ ] **Step 1**: Re-read the sources from first run for anything newer than **Updated**; ask the user what changed
- [ ] **Step 2**: Propose additions and corrections as a list; on approval apply them, bump **Updated**, add a **Changelog** line, and re-render the master CV if anything on it changed

### job-search

- [ ] **Step 1**: Read **Preferences** in `career/profile.md`. Missing location priority, roles or salary floor → ask before searching
- [ ] **Step 2**: Build queries from role titles × locations × three or four core skills. Search tier by tier in the profile's location priority; the first tier gets most of the effort
- [ ] **Step 3**: Find live ads. What works and what does not (checked 2026-10-04):
  - **LinkedIn's public job API works** and is the best source: list with `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={q}&location={place}&f_TPR=r2592000&start={0,10,…}`, then fetch each ad with `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id}`. Fetch ads four at a time; it returns 429 when hurried
  - Employer hiring systems work: search with `allowed_domains` set to Greenhouse, Lever, Workable, SmartRecruiters, Ashby, Workday
  - **Malaysian boards cannot be read directly**: JobStreet, Indeed, Ricebowl, Maukerja, foundit and Glassdoor return 403; Hiredly's search page renders no listings, though its individual ad pages can be fetched (most Flutter ads found there were already closed). Cover them with one WebSearch per board using `allowed_domains` (`my.jobstreet.com`, `malaysia.indeed.com`, `ricebowl.my`, `maukerja.my`, `my.hiredly.com`) and treat what comes back as snippets. Recruiter ads (Randstad, Michael Page) are often already gone (410). A real browser (the Chrome browser skill) is the only way to read the blocked boards in full; offer it, never pretend they were covered
- [ ] **Step 3b**: Role types. Default to the profile's **Target roles**. When the user asks for more or more diverse options, widen to adjacent role types that `profile.md` has evidence for (for example integration, ERP / e-invoicing, mobile, payments, identity, solutions engineering, business analysis), and give every lead a `role_type` so the report can show the spread
- [ ] **Step 4**: Drop duplicates of anything already in `career/jobs/`, closed ads, ads under the salary floor, ads that break a deal-breaker, and ads the user cannot take (for example "candidates already in Singapore only"). Keep every drop, with its reason, for the report
- [ ] **Step 5**: Shortlist 10 by default; more when the user asks (a run may be extended with a second pass into the same `career/runs/{date}-leads.json`). Record how each ad was captured in `ad_captured` (`summary of the full ad` or `search snippet only`). For each, research the company: employee review ratings with their counts (Glassdoor, JobStreet, Indeed, Maukerja), size, ownership or listing, stability, and what reviewers praise and criticise. Every claim keeps its source URL; say "not found" rather than guess
- [ ] **Step 6**: Score each lead against `profile.md` only:
  - **Match suitability (fit)**: Strong / Possible / Weak from the requirement-to-evidence table, where each row is Meets (✓), Partly (~) or Gap (✗). A **snippet-only** lead is capped at Possible: its requirements are not known
  - **Deal-breakers include the business model, not just the job title**: check what the company does (a "bank" may be a crypto bank) and drop or flag accordingly; borderline cases (for example CFD brokers against "gambling") are kept, flagged in red flags, and put to the user
  - **Role score** 1–5: level against the target seniority, stack, growth, development versus support, stated or estimated pay against the floor
  - **Company score** 1–5: from the research in Step 5
  - **Overall** = fit points (Strong 5 · Possible 3 · Weak 1) × 0.4 + role × 0.3 + company × 0.3, rounded to one decimal. **Apply now** ≥ 4.2 · **Apply** ≥ 3.5 · **Consider** ≥ 3.0 · **Low priority** below
  - Write **why this job suits you** (two or three sentences tied to profile evidence) and **the reason for the rating** (one or two sentences naming what lifted and what held it back)
- [ ] **Step 7**: Write the run to `career/runs/{YYYY-MM-DD}-leads.json` (shape: `career/_template/leads-example.json`), then run `.venv/bin/python plugins/violet-skills/skills/career/scripts/build_report.py career/runs/{date}-leads.json`. It writes the job files, tracker rows, the search log, `outputs/career-jobs/{date}-job-search.xlsx` (Leads with live formulas, editable Scoring weights, Dropped, Run) and `outputs/career-jobs/{date}-job-search.html`. Safe to re-run: it never duplicates a job file, tracker row or log entry
- [ ] **Step 8**: Look at the HTML once, publish it as a private artifact (one new artifact per run), and report: the artifact link, the Excel path, the ranked list with each overall rating and recommendation, how many ads were summaries rather than verbatim, and what was dropped and why

### tailor

- [ ] **Step 1**: Find the job file; if several match, list them and ask
- [ ] **Step 2**: Map every requirement in the ad to evidence in `profile.md`; list the gaps plainly
- [ ] **Step 3**: Draft the tailored CV from the master source: choose, order and reword profile facts to match the ad. No fact, figure or skill that is not in `profile.md`. Use the ad's wording only where it describes something the profile already proves
- [ ] **Step 4**: If asked, draft a cover note (at most 200 words) under the same rule
- [ ] **Step 5**: Show the requirement map and what changed from the master CV; wait for approval
- [ ] **Step 6**: Render to `outputs/career-cv/{job-file-name}.pdf`, open it to check, link it in the job file's **Application** section, and set the status to `ready`

### track

- [ ] **"applied to {job}" / "update application {job}: …"**: append a dated line to the job file's **Log**, update its **Status**, and update the tracker row (status, last update, next action). Next action after applying: follow up after 10 working days unless the user gives a date
- [ ] **"job status" / "job tracker"**: summarise the tracker — counts by status, follow-ups due
      (applied 10+ working days with no reply), interviews coming up, offers awaiting a decision.
      Then read `career/timeline.md` and add the last three entries and these three numbers, each
      defined so two runs agree:
      **Applications sent** — count of `- Applied` bullets, total and within the last 14 days.
      **Reply rate** — count each applied-to job **once, at the furthest stage reached**
      (`- Replied`, `- Screening`, `- Interviewed`, `- Offered` or `- Rejected`), against the
      `- Applied` count; a rejection is a reply. Counting bullets instead would let one job that
      progressed through four stages report 400%. **Exclude any job whose thread opens with
      `- Sourced`** — an employer that was never applied to cannot be a reply, and leaving it in
      makes the rate exceed 100%. Report inbound separately: **Sourced** — count of `- Sourced`
      bullets, named.
      **Report "no applications yet" rather than a rate when the `- Applied` count is zero.**
      **Where it stalls** — the status in `tracker.md` holding the most rows, and the oldest
      `Last update` among `applied` rows. Skip the timeline half entirely when
      `career/timeline.md` is missing or has no entries

### save

- [ ] **Step 1**: Check career work actually happened this session — a search run, a tailored CV,
      a status change, a decision taken or reversed. If none, say "No career work this session.
      Nothing to save." and stop. Never write an empty entry
- [ ] **Step 2**: **First read the latest entry's `Open:` bullets and decide each one** —
      resolved this session → drop it; still unresolved → carry it. Then collect the session into
      flat bullets, verb-first, no sub-bullets. The **cap applies to new non-`Open:` bullets: max
      10**; carried `Open:` bullets are exempt, so an unresolved question can never be squeezed out
      by the cap. Record what was decided and why, not only what was run — the per-job `## Log` and
      `searches.md` already hold the mechanics
- [ ] **Step 3**: Any status change opens with its status verb: `Applied`, `Sourced`, `Replied`,
      `Screening`, `Interviewed`, `Offered`, `Rejected`, `Withdrew`, `Closed`. Use **`Sourced`**
      when an employer approaches first and no application was sent — it is an inbound lead, not a
      reply to anything. Any decision left to the user
      becomes an `Open:` bullet, live only in the most recent entry. **Carry an unresolved `Open:`
      bullet forward only when opening a new section.** On a same-day append the existing `Open:`
      bullets are already in today's section — leave them alone and add only newly raised ones,
      or they double and the briefing miscounts
- [ ] **Step 4**: If `career/timeline.md` does not exist,
      create it from `career/_template/timeline.md` first — a `career/` scaffolded before this
      mode existed has no
      timeline, and a header written from scratch loses the convention comment. Then append to
      today's `## YYYY-MM-DD` section if it exists; otherwise add a new section **at the end** of
      the file (oldest-first ordering)
- [ ] **Sync upload**: if `device/sync.md` exists, run the **Upload** in `session-briefing` Step 0s with the label `save career`
- [ ] **Step 5**: Report the bullets written and the file path

**This mode writes `career/timeline.md` and nothing else.** `tracker.md`, `jobs/*.md` and
`runs/*.json` belong to the modes that maintain them.

## Rules

1. **Applications use only `profile.md` facts.** Never invent, inflate, merge or round up a role, figure, skill or date. A gap is reported as a gap
2. **Every profile fact has a source.** Unsourced claims from old CVs stay under **Needs confirmation** until the user confirms them
3. **Never apply, send, email, message or log in on the user's behalf.** This skill finds, documents and drafts; the user submits
4. **Status moves past `ready` only on the user's word.** Never mark a job `applied`, `interview` or `offer` because it seems likely
5. **Search results are leads, not facts.** Every lead records its URL and the date it was seen; an ad that could not be fetched is marked snippet-only
6. **Location priority comes from the profile** and orders both the search effort and the report
7. **Employer confidentiality applies to every CV.** No security findings, internal endpoints, hosts, client data or internal screenshots; follow each role's **Confidential** line in `profile.md`
8. **Contact details on a CV follow the profile's "Public contact on CV" row.** Never add a phone number or address it does not allow
9. **`career/` is personal data.** Never copy it into a public repository, a shared document or the public memory-core template
10. **Generated PDFs go to `outputs/career-cv/`**; sources stay in `career/`
11. **Every rating has a written reason and every company claim has a source.** Ratings judge fit against `profile.md` and the company against cited research, never reputation from memory
12. **Search reports go out as an artifact and an Excel file.** Both come from the run's JSON through `scripts/build_report.py`, so the two always agree; never hand-edit one without the other

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| No CV file can be found | Build the profile from the other sources and the interview; say the CV evidence is missing |
| Two old CVs disagree (dates, titles, figures) | Put both under **Needs confirmation** with their sources and ask |
| A job board blocks fetching | Keep the search snippet, mark the job snippet-only, and say so in the report |
| The ad asks for something the profile lacks | List it under **Gaps**; do not reword the CV to imply it |
| The same job appears on several boards | One job file; list every source URL |
| The user says they applied to a job that is not tracked | Create the job file from what they tell you, status `applied`, source "told by user" |
| Salary not stated | Write "not stated"; never estimate one as if it were posted |

## Level History

- **Lv.1** — Base: sourced profile with first-run scaffold and interview, tiered web job search with ad snapshots and fit analysis, profile-only CV tailoring rendered to PDF, and an application tracker
- **Lv.2** — Job search adds sourced company research, a three-part score (fit, role, company) with an overall rating, recommendation band and written reason, and "why this job suits you"; each run is saved as `career/runs/{date}-leads.json` and `scripts/build_report.py` turns it into job files, tracker rows, the search log, an Excel workbook and an HTML report published as an artifact. Records which job sources can be read automatically, how to cover the blocked Malaysian boards, snippet-only leads capped at Possible, deal-breakers checked against the business model, and widening into adjacent role types with a `role_type` per lead
- **Lv.3** — Current behaviour: adds `save career`, a session timeline at `career/timeline.md`
  written deliberately rather than logged automatically, with status verbs and `Open:` bullets
  that `session-briefing` and `job status` read. Added after
  `save project` had no structure to write into
