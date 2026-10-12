# Project status

Last updated: 2026-10-12

This file is the **single place that says where the project is right now**. It is updated at the end of every session
(see `AGENTS.md` section 6). If it disagrees with the code, one of them is wrong: find out which and fix it.

## Current phase

**R0: Planning and review.** A complete plan (vision, requirements, design, process) exists as Draft v0.1 on the branch
`docs/plan-v0.1`. It is waiting for outside review. **No new product code has been written yet.** The product direction
(an AI test agent) is *Proposed* in [ADR-0009](../decisions/0009-pivot-to-an-ai-test-agent.md), not yet *Accepted*.

## What exists in the repository today

All of this is the earlier "AskOverlay" overlay product, kept and working until ADR-0009 is decided.

| Part | State | Checks (last run 2026-10-12) |
|---|---|---|
| `backend/` FastAPI service: BYOK plus a lifetime demo with per-IP and global caps, LangGraph chat agent with a fallback model, stateless | Working, deployed earlier on an Azure VM (over plain HTTP) | 64 tests pass, lint clean |
| `client/` PySide6 desktop chat client with client-held history | Working, not packaged since the refactors | 6 tests pass |
| `evals/pointing/` evaluation harness (labeler, runner, blind review page, scoring) | Complete; one full experiment run | 55 tests pass |
| CI: `ci.yml` (ruff, pytest, client checks, `ci-ok` aggregate) and `docs.yml` (documentation checks) | Defined and YAML-validated, **has never run on GitHub** (nothing pushed yet) | Every command simulated locally |
| Documentation system: `docs/`, `AGENTS.md`, `tools/check_docs.py` (31 tests, including dangling-reference detection) | Built on branch `docs/plan-v0.1`; checker proven to fail on deliberate breakage; all 11 Mermaid diagrams parse with the real library | Docs check passes |
| GitHub scaffolding: issue forms, PR template, CODEOWNERS, Dependabot, `SECURITY.md`, `CONTRIBUTING.md` | Built; YAML and issue-form structure validated | n/a |
| Docker and VM deployment | Deliberately postponed to the end | Dockerfile edits uncommitted |

## Decisions in force

Accepted: ADR-0003, 0004, 0005, 0006, 0007, 0008. Superseded: ADR-0001, 0002.
Proposed (under review): **ADR-0009** product pivot to an AI test agent, ADR-0010 documentation as memory,
ADR-0011 verdict computed from assertions, ADR-0012 MCP surface as plain tools, ADR-0013 local-first with optional
service mode. See the [decision log](../decisions/README.md).

## Evidence we have

The only experiment so far (pointing accuracy, ADR-0008): both lite models pointed at the right control about 85% of the
time on 20 real screens (60 questions; 95% range 74-93%), about 80% for button-sized controls, judged by one person on
AI-suggested questions. It is a human-judged result, not independent ground truth. It matters now mainly as the method
and as the future "vision fallback" tool of the test agent.

## Exact next step

0. **Back up the work: push it to GitHub (needs the owner's approval).** Nothing from the last weeks is on GitHub yet; see the
   first housekeeping item. Push `v1.1` and `docs/plan-v0.1`.
1. The owner shares [REVIEW-BRIEF](../REVIEW-BRIEF.md) (and the diagram) with a reviewer and collects feedback. Meanwhile,
   run the cold-start drill with an independent fresh agent ([drill log](drills.md)); the author's own cold read is logged
   there but does not count.
2. Apply the feedback to the documents on `docs/plan-v0.1`, then merge to the main line and tag `plan-v0.1`.
3. Accept or reject ADR-0009. If accepted, start **R1.0** of the [roadmap](../03-features-and-roadmap.md): the seeded-bug
   test bed, the 30-test suite and the **frozen pass bar**, with **no agent code before the bar is frozen** (see
   [evaluation strategy](../05-evaluation/evaluation-strategy.md)).

## Open questions

See [open questions](../07-open-questions.md). The blocking ones: product name, licence, whether to keep or archive the
legacy overlay code, the owner's weekly time budget, and which LLM provider(s) the first measurements use.

## Housekeeping and risks (known, not yet fixed)

- **The work is not backed up.** On GitHub, `main` and `v1.2` are at the old V1 commit and `v1.1` is at an early refactor; the
  local `v1.1` is **18 commits ahead** (LangGraph port, demo caps, evaluation harness, decision records, ...) and
  `docs/plan-v0.1` is local only. Until pushed, the repository on GitHub cannot restore this project. `v1.2` looks stale
  (identical to `main`); decide whether to delete it.
- The working folder contains `askoverlay-key.pem` (the VM's SSH key) and a Google OAuth client-secret JSON. Both are
  git-ignored (nothing leaked into history) but should not live in the project folder. The OAuth client is obsolete
  (login was removed); revoke it in the Google Cloud console.
- The deployed VM still holds old PayPal and Google variables in its `.env`, and serves over plain HTTP.
- `backend/Dockerfile` and `backend/.dockerignore` have uncommitted, unbuilt edits (healthcheck, ignore rules).
- Whether prompts sent through a **free-tier** Gemini key may be used by Google to improve its products is unverified;
  this matters before claiming that screenshots are never stored.
- GitHub Actions has not run yet; the first push may reveal Linux-only failures or GitHub-specific rejections.
- Repository settings (branch protection, secret scanning, environments) are **not applied**: they are manual and listed in the engineering handbook, section 9.
- CodeQL and dependency review are pending the public-versus-private decision (OQ-12); action SHA pinning is pending a tool.

## Last session

2026-10-12: completed the pointing experiment and recorded it (ADR-0008); the owner redirected the product toward an AI
test agent and asked for a complete, professional plan whose documentation makes the repository the only memory. Wrote:
vision, requirements, features and roadmap, high- and low-level design, interfaces, security model, scaling and
operations design, evaluation strategy, engineering handbook, CI/CD, documentation policy, lessons learned, ADR-0009 to
ADR-0013 (all Proposed), open questions, a one-page review brief and an overview diagram; split the single ADR file into
one file per decision (and corrected ADR-0008's date); built `tools/check_docs.py` with negative tests; added GitHub
templates, CODEOWNERS, Dependabot, `docs.yml` and the `ci-ok` aggregate; re-encoded two UTF-16 requirements files.
Verified: docs checker and its tests; YAML parsing of every workflow and issue form; Mermaid parsing of all diagrams;
the diagram rendered in a browser. **Not verified:** anything on GitHub itself, any Docker build, the cold-start drill
(still to be run before the plan merges), and nothing of the new product exists yet.
