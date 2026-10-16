# Project status

Last updated: 2026-10-16

This file is the **single place that says where the project is right now**. It is updated at the end of every session
(see `AGENTS.md` section 6). If it disagrees with the code, one of them is wrong: find out which and fix it.

## Current phase

**Finishing small.** Decided in [ADR-0009](../decisions/0009-finish-askoverlay-small-and-split-out-sapienzero.md): AskOverlay is
completed as a small, smooth, working project, and the test-agent idea lives in its own repository (SapienZero). The order is:
1. **Screen reading** (the owner calls it "OCR"): **built and merged into `v1.1` (pull request 3); the owner's trial is pending.** A
   "Look at my screen" switch sends a screenshot with each question to the vision model, as decided in
   [ADR-0010](../decisions/0010-attach-the-screenshot-directly.md). Not Tesseract.
2. A **frontend polish** pass (to be discussed with the owner).
3. **Docker, VM and HTTPS deployment**, last.

## What exists in the repository today

| Part | State | Checks (last run 2026-10-16) |
|---|---|---|
| `backend/` FastAPI service: BYOK plus a lifetime demo with per-IP and global caps, LangGraph chat agent (`gemini-3.5-flash-lite`, fallback `gemini-3.1-flash-lite`), stateless; **now accepts an optional screenshot** (validated, 1.5 MB limit, never stored, redacted from logs) | Working; deployed earlier on an Azure VM over plain HTTP. **The deployed VM does not have the screenshot support yet** | 84 tests pass, lint clean |
| `client/` PySide6 desktop chat client with client-held history; **"Look at my screen" switch** (off by default, remembered, one-time privacy notice, chat window left out of the capture, image downsized to 1280 px JPEG) | Working in scripted checks; not packaged since the refactors | 19 tests pass (13 new, for the pure helpers) |
| `evals/pointing/` evaluation harness (labeler, runner, blind review page, scoring) | Complete; one full experiment run (ADR-0008) | 55 tests pass |
| CI: `ci.yml` (ruff, pytest, client checks, `ci-ok` aggregate) and `docs.yml` (documentation checks) | Green on GitHub for the documentation pull requests | Green on `v1.1`, including the screen-reading pull request |
| Documentation system: `docs/`, `AGENTS.md`, `tools/check_docs.py` | Merged into `v1.1` | Docs check passes; 31 tests pass |
| Docker and VM deployment | Postponed to the end. `backend/Dockerfile` and `.dockerignore` hold **untested** edits (commit `0bbfef0`) | Not built |

## Decisions in force

Accepted: ADR-0003 (screen context via vision; its Decision 2 is superseded by ADR-0010), 0004, 0005 (BYOK plus lifetime demo), 0006,
0007 (LangGraph, client-held history), 0008 (pointing evidence), 0009 (finish small, split out SapienZero), 0010 (attach the
screenshot directly). Superseded: ADR-0001, 0002. See the [decision log](../decisions/README.md).

## Evidence we have

- Pointing accuracy (ADR-0008): both lite models pointed at the right control about 85% of the time on 20 real screens (60
  questions; 95% range 74-93%), about 80% for button-sized controls, judged by one person on AI-suggested questions. Human-judged,
  not independent ground truth.
- Screen reading (2026-10-16, a handful of checks, not a measurement): with a synthetic error dialog the real model read the code
  correctly through the backend, and through a real local server using the client's own capture on the real desktop (a full-screen
  window of our own, so no private content was captured). Without an image the model says it cannot see the screen. On that
  desktop (Windows build 26300) the chat window was left out of the capture both with the Windows exclusion setting and with the
  hide-and-show fallback, and a control capture proved the check can see the window when it is not excluded.

## Exact next step

1. **Owner trial:** run the client, turn on "Look at my screen", and ask about something on screen. Report anything that feels
   slow, wrong or confusing. This is the part scripted checks cannot judge.
2. Then discuss the **frontend polish** pass, and after that deployment work (the VM needs the new backend, and HTTPS).

## Open questions

- Does `v1.1` become `main` now or after the frontend polish? Today `main` and `v1.2` are still at the old V1 commit.
- Screenshot size: the client sends at most 1280 px on the long side. If small text is misread in the owner's trial, raise it.

## Housekeeping and risks (known, not yet fixed)

- **Not verified:** the new wiring in `client/main.py` inside the running app (click the switch, notice, send) was not run
  end to end; only its parts were (capture, payload, switch, notice, setting). The packaged executable was not rebuilt. The
  Windows fallback was checked on a new Windows build only (older builds use it automatically).
- The working folder contains `askoverlay-key.pem` (the VM's SSH key) and a Google OAuth client-secret JSON. Both are
  git-ignored (nothing leaked into the repository) but should not live in the project folder. The OAuth client is obsolete
  (login was removed); revoke it in the Google Cloud console. `DEPLOYMENT.md` still names the key path and the VM's public IP.
- The deployed VM still holds old PayPal and Google variables in its `.env`, and serves over plain HTTP, so BYOK keys **and now
  screenshots** would travel unencrypted until HTTPS is added. Do not point a client that sends screenshots at the plain-HTTP
  VM for anything private.
- Whether prompts sent through a **free-tier** Gemini key may be used by Google to improve its products is unverified. The
  one-time notice in the client says "some free tiers allow it" and does not claim more.
- Screenshot requests are larger; there is no request-size limit at the web server yet (add one in the reverse proxy at
  deployment time).
- `v1.2` is stale (identical to `main`); decide whether to delete it.
- No branch protection or secret scanning is applied on this repository yet (SapienZero has them; the checklist is in its
  `docs/runbooks/settings-2026-10-12.md`).

## Last session

2026-10-16: built the screen-reading feature (ADR-0010; merged via pull request 3): backend (schema, validation, image to the
model on both models, redaction filter, 422 that does not echo images), client (capture, switch, privacy notice, payload), 33
new tests. Verified: backend 84, client 19, evals 55, tools 31 tests; lint clean; real-model checks described above. Also
recorded two lessons (L-27, L-28). **Not verified:** see the first housekeeping item.
