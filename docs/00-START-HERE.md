# Start here

Status: current. Last reviewed: 2026-10-16.

This is the entry point to the documentation. If you have lost your chat history, your laptop, or your memory of how things
work, **this page plus the repository is enough to continue**.

## What this project is, in plain words

AskOverlay is a small desktop assistant. You ask about what is on your screen and a vision model answers; a later step makes it
point at the control to click. It is bring-your-own-key (with a lifetime demo of 10 requests per device), has no accounts and
no payments, and the server keeps no conversation: the client holds the history. Stack: FastAPI, LangGraph, PySide6.
Product description and architecture: the root [`README.md`](../README.md).

## Documentation map

| Document | Read it to learn |
|---|---|
| [`README.md`](../README.md) | What the product is, how it is built, how to run it |
| [Current status](status/STATUS.md) | **Where we are right now and the exact next step** (read every session) |
| [Decision log](decisions/README.md) | Every significant decision and why (ADRs 0001 to 0009) |
| [Lessons learned](06-process/lessons-learned.md) | Mistakes already paid for, with the rule that prevents each |
| [Pointing evaluation](../evals/pointing/README.md) | How the pointing experiment was run and how to repeat it |
| [Deployment notes](../DEPLOYMENT.md) | The Azure VM, how to start and stop it |
| [`AGENTS.md`](../AGENTS.md) | Rules for any AI agent or new contributor; cold-start steps; commands |

Templates for new decisions and handoffs are in `docs/templates/`: [ADR](templates/adr-template.md),
[session handoff](templates/session-handoff-template.md).

## If everything is lost: recovery checklist

0. **Only what was pushed to GitHub can be recovered.** Push at the end of every session (`git status -sb` shows "ahead").
1. `git clone https://github.com/brindeshwar/askoverlay.git`, check out `v1.1` (the integration branch), and open it with
   your agent. Tell it: "Read `AGENTS.md` and follow the cold-start steps."
2. Read [STATUS](status/STATUS.md). It states the phase and the exact next step.
3. Verify the repository is healthy (commands in `AGENTS.md` section 4): tests, lint, `python tools/check_docs.py`.
4. Recreate what is **deliberately not in the repository**:

| Not in the repo | Why | How to get it back |
|---|---|---|
| `backend/.env` (the demo Gemini key and settings) | Secret | Create a new key in Google AI Studio; variable names are in `backend/.env.example` |
| Private evaluation data (`evals/pointing/data/`: screenshots, labels, judgments) | Private screen content | Aggregate results are in ADR-0008; to regenerate, follow `evals/pointing/README.md`. Keep a private encrypted backup if you want the raw data |
| The Azure VM and its SSH key (`askoverlay-key.pem`) | Infrastructure and a secret | `DEPLOYMENT.md`; store the key **outside** the repository folder |
| Claude Code's local memory | Machine-local, not authoritative | Not needed: everything important is in these documents |

## Related project

The test-agent idea that grew out of this project is **SapienZero**, a separate repository
(`github.com/brindeshwar/sapienzero`). See [ADR-0009](decisions/0009-finish-askoverlay-small-and-split-out-sapienzero.md).
