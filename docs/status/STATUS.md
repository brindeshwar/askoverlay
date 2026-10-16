# Project status

Last updated: 2026-10-16

This file is the **single place that says where the project is right now**. It is updated at the end of every session
(see `AGENTS.md` section 6). If it disagrees with the code, one of them is wrong: find out which and fix it.

## Current phase

**Finishing small.** Decided in [ADR-0009](../decisions/0009-finish-askoverlay-small-and-split-out-sapienzero.md): AskOverlay is
completed as a small, smooth, working project, and the test-agent idea lives in its own repository (SapienZero). The order is:
1. **Screen reading** (the owner calls it "OCR"): the feature ADR-0003 designed and never built, implemented with a vision model,
   not Tesseract. A short plan is written and approved **before** any code.
2. A **frontend polish** pass (to be discussed with the owner).
3. **Docker, VM and HTTPS deployment**, last.

## What exists in the repository today

| Part | State | Checks (last run 2026-10-16) |
|---|---|---|
| `backend/` FastAPI service: BYOK plus a lifetime demo with per-IP and global caps, LangGraph chat agent (`gemini-3.5-flash-lite`, fallback `gemini-3.1-flash-lite`), stateless | Working; deployed earlier on an Azure VM over plain HTTP | 64 tests pass, lint clean |
| `client/` PySide6 desktop chat client with client-held history | Working, not packaged since the refactors. **Has no screen capture yet** | 6 tests pass |
| `evals/pointing/` evaluation harness (labeler, runner, blind review page, scoring) | Complete; one full experiment run (ADR-0008) | 55 tests pass |
| CI: `ci.yml` (ruff, pytest, client checks, `ci-ok` aggregate) and `docs.yml` (documentation checks) | Defined and YAML-validated; **not yet run on GitHub for this repository** | Commands run locally |
| Documentation system: `docs/`, `AGENTS.md`, `tools/check_docs.py` | Added on branch `docs/askoverlay-docs-system` | Docs check and its tests run locally (see "Last session") |
| Docker and VM deployment | Postponed to the end. `backend/Dockerfile` and `.dockerignore` hold **untested** edits (commit `0bbfef0`) | Not built |

## Decisions in force

Accepted: ADR-0003 (screen context via vision), 0004, 0005 (BYOK plus lifetime demo), 0006, 0007 (LangGraph, client-held
history), 0008 (pointing evidence), 0009 (finish small, split out SapienZero). Superseded: ADR-0001, 0002.
See the [decision log](../decisions/README.md).

## Evidence we have

One experiment (pointing accuracy, ADR-0008): both lite models pointed at the right control about 85% of the time on 20 real
screens (60 questions; 95% range 74-93%), about 80% for button-sized controls, judged by one person on AI-suggested questions.
It is a human-judged result, not independent ground truth.

## Exact next step

1. Merge the documentation branch `docs/askoverlay-docs-system` into `v1.1` (pull request; CI must be green).
2. Write the **screen-reading plan** and get the owner's approval before coding. Starting point (to confirm with the owner):
   the client captures one screenshot per send (the "Middle" strategy of ADR-0003); the backend declares a `read_screen` tool on
   the LangGraph agent; the model decides when to use it and answers grounded in the image; tests use fakes and one real run is
   recorded. Open sub-questions: image downscaling, privacy notice in the UI, how a user turns it off, cost on the demo tier.
3. Then the frontend polish pass, then deployment work.

## Open questions

- What exactly the owner wants from "OCR". Reading of the evidence: ADR-0003 says the feature was "originally framed as OCR" and
  reframed as vision screen context. Confirm this is what is wanted (as opposed to text extraction with Tesseract, or the
  pointing overlay).
- Does `v1.1` become `main` now or after the screen-reading feature? Today `main` and `v1.2` are still at the old V1 commit.

## Housekeeping and risks (known, not yet fixed)

- The working folder contains `askoverlay-key.pem` (the VM's SSH key) and a Google OAuth client-secret JSON. Both are
  git-ignored (nothing leaked into the repository) but should not live in the project folder. The OAuth client is obsolete
  (login was removed); revoke it in the Google Cloud console. `DEPLOYMENT.md` still names the key path and the VM's public IP.
- The deployed VM still holds old PayPal and Google variables in its `.env`, and serves over plain HTTP, so BYOK keys travel
  unencrypted until HTTPS is added.
- Whether prompts sent through a **free-tier** Gemini key may be used by Google to improve its products is unverified; this
  matters before claiming that screenshots are never stored, and it matters more once screen reading sends screenshots.
- `v1.2` is stale (identical to `main`); decide whether to delete it.
- No branch protection or secret scanning is applied on this repository yet (SapienZero has them; the checklist is in its
  `docs/runbooks/settings-2026-10-12.md`).

## Last session

2026-10-16: split the test-agent work out into the new repository SapienZero (ADR-0009) and gave this repository its own small
documentation system: one decision record per file, a status file, `AGENTS.md`, a docs checker in CI, security and contributing
notes. The old combined plan stays archived on the branch `docs/plan-v0.1` (tag `archive/sapienzero-plan-v0.1`).
Verified: backend 64, evals 55, client 6 tests pass; lint clean. **Not verified:** CI on GitHub for this repository; the
Docker edits; anything about the screen-reading feature (not started).
