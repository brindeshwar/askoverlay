# Documentation and memory policy

Status: Draft v0.1. Decision: [ADR-0010](../decisions/README.md). The goal is stated plainly: **if the chat history, the
laptop and the owner's memory are all lost, a new person or agent can clone the repository, read it, and continue exactly
where work stopped**, without guessing and without asking anyone to re-explain.

## 1. Principles

1. **The repository is the only memory, and only what is pushed counts.** Chats, local assistant memory, unpushed commits and
   heads are caches that may vanish. Pushing at the end of a session is part of the protocol.
2. **One fact, one home.** Each kind of information has a single source of truth (section 2); everywhere else links to it
   instead of copying it. Duplicates drift.
3. **Docs change with code, in the same pull request.** A change that makes a document false is not finished.
4. **Write for a cold reader.** Assume the reader has none of today's context. Define terms, date things, link sources.
5. **State uncertainty.** Mark assumptions, open questions and unverified claims. A confident wrong document is worse
   than an honest gap.
6. **Mechanical checks catch the mechanical mistakes; people and drills catch the rest.**

## 2. Where each kind of information lives

| Information | Single source of truth | Updated when |
|---|---|---|
| Why this exists, for whom, scope, goals | `docs/01-vision-and-scope.md` | Scope or goals change |
| What it must do (testable) | `docs/02-requirements.md` | A requirement is added, changed or dropped |
| Feature list and release plan, gates | `docs/03-features-and-roadmap.md` | Scope or gates change; each release |
| How it is built (structure, data, behaviour) | `docs/04-architecture/*` | The design changes |
| How we measure it; pass bars; results | `docs/05-evaluation/*` | An experiment is registered or finished |
| How we work (git, review, release, CI) | `docs/06-process/*`, `AGENTS.md` | A rule or pipeline changes |
| Why a decision was made | `docs/decisions/NNNN-*.md` | A decision is made, accepted or superseded |
| **Where we are now and the next step** | `docs/status/STATUS.md` | **End of every session** |
| What changed for users | `CHANGELOG.md` | Every user-visible change |
| Mistakes already paid for | `docs/06-process/lessons-learned.md` | Something cost time or surprised us |
| What is still undecided | `docs/07-open-questions.md` | A question appears or is answered |
| How agents must behave | `AGENTS.md` (and `CLAUDE.md` for Claude-specific notes) | The working agreement changes |
| Runbooks, incidents, settings exports | `docs/runbooks/` | Operations change |

## 3. Update triggers (what to touch when you change X)

| Change | Also update |
|---|---|
| New or changed behaviour | Tests; the matching requirement; the design doc if structure changed; `CHANGELOG.md` if user-visible |
| New dependency or technology | An ADR (if significant); the technology table in the HLD; the dependency note in the pull request |
| A decision (hard to reverse, or someone may ask "why?") | A new ADR; the ADR index; links from the affected docs |
| A measurement | Pre-registration **before**, a results file **after**, the experiment register |
| A release gate or scope change | Roadmap; requirements; STATUS |
| A bug that taught us something | `lessons-learned.md` |
| Anything that changes the next step | `STATUS.md` |

The pull-request template carries this as a checklist ("Docs impact"), and the Definition of Done requires it.

## 4. Decision records (ADRs)

- **When:** a choice that is expensive to reverse, that closes off alternatives, that someone will later ask "why?" about,
  or that changes a requirement, an interface, a technology, a process or the scope.
- **How:** copy `docs/templates/adr-template.md` to `docs/decisions/NNNN-short-title.md` (next number), fill it honestly
  including options considered and consequences, set the status, and add the row to `docs/decisions/README.md`.
- **Lifecycle:** *Proposed* (under review), *Accepted*, *Superseded* (by a later ADR, with a Related line), *Rejected*,
  *Deprecated*. **An accepted ADR is not edited in substance.** Changing your mind is a new ADR that supersedes the old one,
  so the history of reasoning stays intact. Typos and added links are fine.
- **Checked mechanically:** numbering without gaps, a status and a date in every file, and the index in sync.

## 5. The status file and the session handoff

`docs/status/STATUS.md` answers four questions for a cold reader: *What phase are we in? What exists and does it work?
What was decided and what is proposed? What is the single next step?* It also lists open questions, known risks and
housekeeping. It is rewritten (not appended) at the end of every session and carries a `Last updated:` date that the docs
check reads (a stale or future date fails CI). The handoff template (`docs/templates/session-handoff-template.md`) is
pasted into the pull request description so the *story* of a session is in the git history too.

## 6. What is deliberately not in the repository

| Item | Why | Recovery |
|---|---|---|
| Secrets, keys, tokens, `.env` | Must never be committed | Recreate in the provider console; names listed in `.env.example` |
| Private evaluation data (screenshots, labels, judgments) | Personal screen content | Aggregates are in the repo; regeneration steps are in `evals/pointing/README.md`; keep an encrypted private backup if wanted |
| Infrastructure and its credentials | Secrets and state | `DEPLOYMENT.md` and, later, infrastructure-as-code in the repo |
| GitHub settings | Not under git | The checklist in the engineering handbook; dated exports in `docs/runbooks/` |
| Assistant-local memory | Machine-local, not authoritative | Not needed |

The rule for the local memory of any assistant: **short pointers only** ("see STATUS.md"). If it contains a fact that is not in
the repository, that fact is at risk; move it into the right document.

## 7. The cold-start drill (the test that this policy works)

**Purpose:** prove that the repository alone is enough. **When:** before every release, after any large documentation change,
and at least quarterly.

**Procedure**

1. Start a **fresh** agent session with only a clean checkout (no prior chat, no assistant memory).
2. Give it exactly this prompt: *"Read AGENTS.md and follow its cold-start steps. Then answer: (a) what this project is in
   three sentences; (b) the current phase and the exact next step; (c) three decisions in force and why; (d) how to run the
   tests and the docs check; (e) what is not in the repository and how to recover it; (f) which release gate we are working
   toward and what it requires."*
3. Compare each answer with the documents. **Pass = all six correct without asking a human anything.**
4. Give it one small task, for example *"Add a requirement for X"* or *"Record that decision Y"*, and check that it edits
   the **right** documents (requirement, roadmap if needed, ADR and index, STATUS) and runs the docs check.
5. Record the date, commit, result and the gaps found in `docs/status/drills.md`; fix every gap in the documents (the gap
   is the documentation's bug, not the agent's).

## 8. What automation enforces (`tools/check_docs.py`, in CI)

- Every ADR file: contiguous numbering, a `Status:` from the allowed set, a `Date:`, and a matching row in the index.
- `docs/status/STATUS.md`: required headings present; `Last updated:` is a real date, not in the future, and not older than
  the newest change to code (warning level at first, a failure later).
- **No orphans:** every document under `docs/` (except templates) is linked from `docs/00-START-HERE.md`.
- **No broken internal links:** every relative Markdown link points to an existing file.
- **No dangling references:** every requirement id (`FR-nn`, `NFR-nn`), decision id (`ADR-nnnn`), open-question id (`OQ-nn`)
  and lesson id (`L-nn`) mentioned anywhere is defined in its home document.
- Mermaid diagram blocks are non-empty and start with a known diagram type (their *syntax* is checked by parsing with the real
  library whenever diagrams change; see lessons L-23).
- `AGENTS.md` exists with its required sections, and `CLAUDE.md` imports it.

Humans and drills check what a script cannot: that the content is *true*, *clear* and *complete*.

## 9. Style

- Plain language, short sentences, concrete examples. Define a term the first time it appears in a document.
- Dates are absolute (`2026-10-12`), never "yesterday" or "recently".
- Tables for facts that have the same shape; prose for reasoning; diagrams (Mermaid) where structure is the point.
- Every document starts with a title and a one-line status; draft documents say "Draft".
- Link rather than copy. If you must repeat a number, link to where it is defined.
- Label assumptions and estimates as such, with how they will be checked.
- No marketing language. Say what is measured and what is not.

## 10. Anti-patterns to avoid

A changelog that says "misc fixes"; an ADR written after the fact that hides the alternatives; "TODO: document this" without
an issue; copying a table into two files; documentation in chat messages only; a status file nobody updates; a decision
that exists only as a code comment; claims without a source or a measurement.
