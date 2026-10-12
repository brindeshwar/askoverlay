# Start here

Status: Draft v0.1 (awaiting external review). Last reviewed: 2026-10-12.

This is the entry point to the project's documentation. If you have lost your chat history, your laptop, or your
memory of how things work, **this page plus the repository is enough to continue**.

## What this project is, in plain words

An **AI test agent**. You describe a test in plain English ("log in, add the first product to the cart, check the total").
The agent runs it in an isolated, headless browser in the background, so nothing on your screen is disturbed, and
returns a verdict with evidence (screenshots, a trace, a step log). You can use it:

- **on its own**, from the command line or CI;
- **driven and supervised by another agent** (for example a coding agent) over MCP, which can read live progress,
  pause, stop, and approve or deny risky steps;
- with **you** supervising instead. Who supervises is a setting, not a different product.

The working title is "AskOverlay" (inherited from an earlier overlay product; the name is an open question,
see [open questions](07-open-questions.md)). Full definition: [vision and scope](01-vision-and-scope.md).

## Documentation map

Read in this order the first time. Every document is linked from here; a check in CI fails if one is not.

| # | Document | Read it to learn | When |
|---|---|---|---|
| 1 | [Vision and scope](01-vision-and-scope.md) | Why this exists, for whom, what it is not, how success is measured | First |
| 2 | [Requirements](02-requirements.md) | Numbered functional and non-functional requirements with acceptance criteria | Before designing or testing anything |
| 3 | [Features and roadmap](03-features-and-roadmap.md) | Releases R0 to R6, their scope, exit gates and kill criteria | Before planning work |
| 4 | [High-level design](04-architecture/hld.md) | Context, containers, components, deployment modes, technology choices | Before touching architecture |
| 5 | [Low-level design](04-architecture/lld.md) | Modules, data model, state machine, events, agent loop, algorithms | Before writing code |
| 6 | [Interfaces](04-architecture/interfaces.md) | CLI, MCP tools, REST API, event stream, reports | Before integrating or testing from outside |
| 7 | [Security and threat model](04-architecture/security-threat-model.md) | What can go wrong and what stops it | Before any feature that touches the network, secrets, or untrusted content |
| 8 | [Scaling and operations](04-architecture/scaling-and-operations.md) | Load balancing, queues, workers, capacity, SLOs, observability, recovery | Before building service mode |
| 9 | [Evaluation strategy](05-evaluation/evaluation-strategy.md) | How we measure the agent, the test bed, pass bars | Before running or changing any measurement |
| 10 | [Engineering handbook](06-process/engineering-handbook.md) | Git, pull requests, reviews, versioning, releases, repository settings | Before your first pull request |
| 11 | [CI/CD](06-process/ci-cd.md) | Pipelines, gates, environments, adoption tiers | Before changing automation |
| 12 | [Documentation and memory policy](06-process/documentation-and-memory-policy.md) | How the docs stay true; the cold-start drill | Before ending any session |
| 13 | [Lessons learned](06-process/lessons-learned.md) | Mistakes already paid for | When something behaves strangely |
| 14 | [Decision log](decisions/README.md) | Every significant decision and why | Before changing anything that was decided |
| 15 | [Open questions](07-open-questions.md) | What is still undecided and who decides | Before assuming |
| 16 | [Current status](status/STATUS.md) | **Where we are right now and the exact next step** | Every session, first |
| 17 | [Review brief](REVIEW-BRIEF.md) | One page for an outside reviewer | When asking for feedback |
| 18 | [Cold-start drill log](status/drills.md) | Results of proving the docs are enough to resume from | Before a release |
| 19 | [Runbooks and operational records](runbooks/README.md) | What to do when things break; settings kept outside git | When operating or recovering |
| 20 | [Overview diagram](diagrams/overview.svg) | The whole system on one picture | Any time |

Templates (for new ADRs, handoffs, experiments, runbooks) live in `docs/templates/`. Rules for AI agents are in
[`AGENTS.md`](../AGENTS.md) at the repository root.

Template files: [ADR](templates/adr-template.md), [session handoff](templates/session-handoff-template.md),
[experiment pre-registration](templates/experiment-preregistration-template.md), [runbook](templates/runbook-template.md).

## If everything is lost: recovery checklist

0. **Only what was pushed to GitHub can be recovered.** Pushing at the end of every session is part of the routine (see
   `AGENTS.md` section 6); check `git status -sb` for "ahead".
1. `git clone` the repository and open it with your agent. Tell it: "Read `AGENTS.md` and follow the cold-start steps."
2. Read [STATUS](status/STATUS.md) yourself. It states the phase and the exact next step.
3. Verify the repository is healthy (commands in `AGENTS.md` section 4): tests, lint, `python tools/check_docs.py`.
4. Recreate what is **deliberately not in the repository**:

| Not in the repo | Why | How to get it back |
|---|---|---|
| API keys and `.env` files | Secrets | Create new keys in the provider's console; names are listed in `backend/.env.example` |
| Private evaluation data (`evals/pointing/data/`: screenshots, labels, judgments) | Contains private screen content | Aggregate results are kept in ADR-0008; to regenerate, follow `evals/pointing/README.md`. Keep a private encrypted backup if you want the raw data |
| The Azure VM and its SSH key | Infrastructure and a secret | `DEPLOYMENT.md`; the key must be stored **outside** the repository folder |
| GitHub repository settings (branch protection, secrets, environments) | Not versioned by git | The checklist in the engineering handbook; re-apply it |
| Claude Code's local memory | Machine-local and not authoritative | Not needed: everything important is in these documents |

## How this documentation stays true

Documents are changed in the **same pull request** as the code they describe, and CI checks the mechanical parts.
Details and the periodic "cold-start drill" are in the [documentation and memory policy](06-process/documentation-and-memory-policy.md).
