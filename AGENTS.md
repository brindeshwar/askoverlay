# AGENTS.md: read this first

This file is for **any AI coding agent** (Claude Code, Codex, Cursor, Copilot, ...) and for new human contributors.
The repository is the project's only memory. Chats are disposable; if something matters, it must be written down here.

## 1. Cold start: how to get fully in sync (about 10 minutes)

Read in this order, and do not start work until you have done all five:

1. [`docs/00-START-HERE.md`](docs/00-START-HERE.md): what this project is, and a map of every document.
2. [`docs/status/STATUS.md`](docs/status/STATUS.md): **current state**, what is in progress, the exact next step.
3. [`docs/decisions/README.md`](docs/decisions/README.md): the decision log. Read every *Accepted* and *Proposed* ADR
   that touches the area you will change.
4. [`docs/03-features-and-roadmap.md`](docs/03-features-and-roadmap.md): which release we are building and its exit gate.
5. The design document for your area under [`docs/04-architecture/`](docs/04-architecture/).

Then verify the repository matches the documents (section 4). If it does not, that is a documentation bug: fix it or
report it before building on it.

## 2. The project in five lines

- **What:** an AI test agent. You write a test in plain English; it runs the test in an isolated, headless browser in
  the background and returns a verdict (passed / failed / inconclusive / blocked / error) with evidence.
- **How it is used:** standalone from the command line or CI, **or** driven and supervised by another agent over MCP.
  The user chooses who supervises (autonomous, a coding agent, or a human).
- **Principles:** measure before building; the verdict is computed from executed assertions, never from the model's
  opinion; safe by default; local-first; the repository is the memory.
- **Status:** the product direction is *proposed* in ADR-0009 and is under review. See `docs/status/STATUS.md`.
- **Legacy:** `backend/`, `client/`, `evals/pointing/` come from the earlier "AskOverlay" overlay product. They are
  kept, tested and documented until the review decision; see ADR-0009 for what happens to them.

## 3. Working agreement (rules, not suggestions)

**Process**
- Work on a branch, never directly on `main`. One concern per branch, one concern per commit.
- Conventional Commits: `feat(scope): ...`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore`.
- **Never commit or push code you have not run.** "It compiles" is not "it works". Run the tests and, for anything
  with a user interface or a network call, exercise it for real.
- Change of behaviour = change of tests **and** docs in the same pull request.
- Before building anything non-trivial, write the plan (issue or PR description): goal, approach, how you will check it.
- Keep changes small. If a change touches more than one concern, split it.

**Decisions and measurements**
- A decision that is hard to reverse, or that someone might later ask "why?", gets an ADR (template in
  `docs/templates/`). Never edit an accepted ADR's substance; write a new one that supersedes it.
- **Pre-register measurements.** Before running any evaluation, commit the question, the data, and the pass bar
  (`docs/templates/experiment-preregistration-template.md`). Do not move the bar after seeing results.
- Report results with their uncertainty and their limits. Never claim more than the evidence supports. A small or
  one-judge sample is stated as such.

**Honesty**
- Say what you did **not** verify. If a check was skipped, say so.
- If you find a flaw in the plan, the code or your own earlier work, say so and fix or record it.
- Prefer the simplest design that works ("why two?" before adding a second model, framework or abstraction).

**Safety and privacy**
- Never commit secrets, keys, tokens, `.env` files, or private datasets (`evals/pointing/data/` is git-ignored on
  purpose). Never print private user content (screenshots, questions) into logs, chats, commits or CI output; report
  counts and aggregates.
- Real LLM calls cost quota and can send data to a third party. CI uses fakes; real-model runs are explicit, budgeted
  and recorded.
- The test agent must never be pointed at a site that is not on the run's allow-list.

**Working with the owner (the human)**
- Explain in plain language. Give a recommendation with its trade-off at every decision point, not a menu.
- One step at a time. Confirm before anything hard to reverse or outward-facing (push, publish, delete, deploy).
- The owner is strong in Python, backend, agents and Docker, and learning frontend: teach when touching UI.

## 4. Commands (all run from the repository root unless stated)

These exist today (legacy code); the new package will add its own and this table will be updated in the same PR.

| Purpose | Command |
|---|---|
| Backend tests | `cd backend && python -m pytest -q` |
| Lint (backend, evals, tools) | `cd backend && python -m ruff check . ../evals ../tools --config ruff.toml` |
| Eval tests | `cd backend && python -m pytest -q ../evals/pointing` |
| Client tests | `python -m pytest -q client/tests` |
| Docs check | `python tools/check_docs.py` |
| Docs-check tests | `python -m pytest -q tools` |
| Diagram syntax | Mermaid blocks are parsed with the real library when changed (see lessons-learned L-23) |

Use the project's virtual environment (backend: `backend/.venv-backend`). A command that "does nothing" usually ran
in the wrong directory: relative paths to the interpreter break after `cd`.

## 5. Documentation duties (what to update when)

| You changed... | Update |
|---|---|
| Anything a future reader needs to know the **state** | `docs/status/STATUS.md` (every session) |
| A decision or its status | A new or updated ADR, and the index `docs/decisions/README.md` |
| Scope, requirements, a release gate | `docs/02-requirements.md`, `docs/03-features-and-roadmap.md` |
| Architecture, interfaces, data model | The matching file in `docs/04-architecture/` |
| How we build, review, release, or run CI | `docs/06-process/` |
| Something user-visible | `CHANGELOG.md` |
| A lesson that cost time | `docs/06-process/lessons-learned.md` |

`python tools/check_docs.py` enforces the mechanical parts (ADR index in sync, no orphan documents, no broken
internal links, status file fresh). It runs in CI; run it before you push.

## 6. End-of-session protocol (mandatory)

1. Run the tests and the docs check. Note anything you could not run.
2. Update `docs/status/STATUS.md`: state, what changed, what is verified, **the exact next step**, open questions.
3. Record any decision as an ADR; log any lesson.
4. Commit with a clear message. Open or update the pull request using the handoff template.
5. **Push the branch** so the work exists off this machine (the first push of a branch needs the owner's approval). Work
   that is only on one laptop is not recoverable.
6. Do **not** rely on chat history or any local "memory" file: if it is not in the repository, the next session
   does not know it.

## 7. Known pitfalls in this environment (Windows + Git Bash)

Short list; the full version with causes is in [`docs/06-process/lessons-learned.md`](docs/06-process/lessons-learned.md).

- Do not put backslash-heavy text (regexes, Windows paths, `\n` literals) through shell heredocs: it is mangled.
  Use the editor tools to write files.
- The `Write` tool keeps an existing file's encoding. A UTF-16 `requirements.txt` stayed UTF-16; delete and recreate
  such files.
- A chain split over two lines runs the second line even if the first failed. Use `&&`, or `set -e`.
- Never test a page only with scripted events: test with a real layout and real input. A preview pane can load local
  files as `data:` pages (no relative images, no localStorage) and emulated viewports may not fire resize events.
- Real API calls: use the fakes in tests; a key is read from settings, never printed.
