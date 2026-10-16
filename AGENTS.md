# AGENTS.md: read this first

This file is for **any AI coding agent** (Claude Code, Codex, Cursor, Copilot, ...) and for new human contributors.
The repository is the project's only memory. Chats are disposable; if something matters, it must be written down here.

## 1. Cold start: how to get fully in sync (about 5 minutes)

Read in this order, and do not start work until you have done all four:

1. [`README.md`](README.md): what the product is and how it is built.
2. [`docs/00-START-HERE.md`](docs/00-START-HERE.md): the map of the documentation and what is deliberately not in the repository.
3. [`docs/status/STATUS.md`](docs/status/STATUS.md): **current state**, what is in progress, the exact next step.
4. [`docs/decisions/README.md`](docs/decisions/README.md): the decision log. Read every *Accepted* decision that touches the
   area you will change (ADR-0003 and ADR-0008 first: they define what the product is).

Then verify the repository matches the documents (run the commands in section 4). If it does not, that is a documentation
bug: fix it or report it before building on it.

## 2. The project in five lines

- **What:** AskOverlay is a small desktop assistant. You ask a question about what is on your screen; a vision model answers
  and, as a later step, points at the control you should click. Python: FastAPI backend, LangGraph agent, PySide6 client.
- **Models:** `gemini-3.5-flash-lite` with `gemini-3.1-flash-lite` as fallback. Bring-your-own-key, plus a lifetime demo
  of 10 requests per device. No accounts and no payments.
- **Stateless server:** the client holds the conversation history (ADR-0007).
- **Scope is deliberately small.** The test-agent idea that grew out of this project is a *different* product,
  **SapienZero**, in its own repository (`github.com/brindeshwar/sapienzero`). See ADR-0009. Do not build it here.
- **Deployment (Docker, VM, HTTPS) is done last,** after the features.

## 3. Working agreement (rules, not suggestions)

- Work on a branch, never directly on `main`; `v1.1` is the integration branch until it is merged to `main`.
  One concern per branch and per commit. Conventional Commits: `feat(scope): ...`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore`.
- **Never commit or push code you have not run.** "It compiles" is not "it works". Run the tests and, for anything with a user
  interface or a network call, exercise it for real. (One owner-approved exception exists: the Docker edits in
  commit `0bbfef0` are untested on purpose and are rebuilt and tested when deployment work starts.)
- Change of behaviour = change of tests **and** docs in the same pull request.
- A decision that is hard to reverse, or that someone may later ask "why?" about, gets an ADR (template in
  `docs/templates/`). Never edit an accepted ADR's substance; write a new one that supersedes it.
- Pre-register measurements before running them (the pointing evaluation in `evals/pointing/` is the model). Report results with
  their uncertainty and limits.
- Say what you did **not** verify. If you find a flaw in the plan, the code or your own earlier work, say so and fix or record it.
- Prefer the simplest design that works.
- **Safety and privacy:** never commit secrets, keys, tokens or `.env` files. The private evaluation data in
  `evals/pointing/data/` is git-ignored on purpose; never print its content (screenshots, questions) into logs, chats, commits
  or CI output; report counts and aggregates only. CI uses fakes; real model calls cost quota and are explicit.
- **Working with the owner:** explain in plain language, one recommendation with its trade-off at each decision, one step at a
  time. Confirm before anything hard to reverse or outward-facing (push, publish, delete, deploy).

## 4. Commands (run from the repository root unless stated)

| Purpose | Command |
|---|---|
| Backend tests | `cd backend && python -m pytest -q` |
| Lint (backend, evals, tools) | `cd backend && python -m ruff check . ../evals ../tools --config ruff.toml` |
| Eval tests | `cd backend && python -m pytest -q ../evals/pointing` |
| Client tests | `python -m pytest -q client/tests` |
| Docs check | `python tools/check_docs.py` |
| Docs-check tests | `python -m pytest -q tools` |

Use the project virtual environments (backend: `backend/.venv-backend`, client: `client/.venv-client`). A command that "does
nothing" usually ran in the wrong directory: relative paths to the interpreter break after `cd`.

## 5. Documentation duties (what to update when)

| You changed... | Update |
|---|---|
| Anything a future reader needs to know the **state** | `docs/status/STATUS.md` (every session) |
| A decision or its status | A new or updated ADR, and the index `docs/decisions/README.md` |
| Something user-visible | `CHANGELOG.md` and `README.md` if the description changes |
| A lesson that cost time | `docs/06-process/lessons-learned.md` |

`python tools/check_docs.py` enforces the mechanical parts (ADR index in sync, no orphan documents, no broken internal links,
no dangling ids, status file fresh). It runs in CI; run it before you push.

## 6. End-of-session protocol (mandatory)

1. Run the tests and the docs check. Note anything you could not run.
2. Update `docs/status/STATUS.md`: state, what changed, what is verified, **the exact next step**, open questions.
3. Record any decision as an ADR; log any lesson.
4. Commit with a clear message; open or update the pull request.
5. **Push the branch** so the work exists off this machine (the first push of a branch needs the owner's approval).
6. Do **not** rely on chat history or any local "memory" file: if it is not in the repository, the next session does not know it.

## 7. Known pitfalls in this environment (Windows + Git Bash)

Full causes are in [`docs/06-process/lessons-learned.md`](docs/06-process/lessons-learned.md).

- Do not put backslash-heavy text (regexes, Windows paths, `\n` literals) through shell heredocs: it is mangled. Use the editor
  tools to write files.
- The `Write` tool keeps an existing file's encoding. A UTF-16 `requirements.txt` stayed UTF-16 (already fixed here); delete
  and recreate such files.
- A command chain split over two lines runs the second line even if the first failed. Use `&&`.
- Test a UI with a real layout and real input, not only scripted events. A preview pane can load local files as `data:` pages
  (no relative images, no localStorage) and emulated viewports may not fire resize events.
- Real API calls: use the fakes in tests; a key is read from settings (`backend/.env`), never printed.
