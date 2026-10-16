# AskOverlay

[![CI](https://github.com/brindeshwar/askoverlay/actions/workflows/ci.yml/badge.svg)](https://github.com/brindeshwar/askoverlay/actions/workflows/ci.yml)

A Windows always-on-top desktop AI assistant. Click a small draggable icon, ask a question about anything you're looking at, get a streamed, formatted answer — no window switching required.

Built as a portfolio project demonstrating full-stack AI application development: a PySide6 desktop client, a Dockerized FastAPI backend, and a live cloud deployment — with production-style concerns (secret handling, usage quotas, session memory) implemented deliberately, not assumed away.

## Features

- **Two access modes through one endpoint:**
  - **BYOK** — paste your own Gemini API key, unlimited use, zero cost or liability to the developer
  - **Demo mode** — 10 free requests per device in total (not per day), no signup required
- **Look at my screen** (off by default): turn it on and each question is sent with a screenshot of your screen, so the model can answer about what you see. The chat window is left out of the capture, the image is downsized, used for that one message only, and never stored or logged. It uses a vision model directly, not OCR (see ADR-0003 and ADR-0010). Images cost more tokens, so they use the shared demo budget faster.
- Real-time streaming responses (SSE) with live markdown rendering (headers, bold, lists)
- Multi-turn memory held by the client: the server is stateless and never stores a conversation
- Frameless, draggable, always-on-top overlay window with a persistent tray-managed lifecycle (no taskbar presence)
- Dockerized backend, deployed and tested on a live Azure VM
- Packaged, distributable standalone Windows executable (PyInstaller)

## System Design

### High-Level Design (HLD)

```
┌─────────────────┐        HTTP / SSE         ┌──────────────────┐
│  PySide6 Client  │ ────────────────────────► │  FastAPI Backend │
│  (Windows .exe)  │ ◄──────────────────────── │   (Dockerized)   │
└─────────────────┘                            └──────────────────┘
                                                        │
                                  ┌─────────────────────┴─────────────────────┐
                                  ▼                                           ▼
                        ┌───────────────────┐                      ┌────────────────────┐
                        │ Gemini (LangGraph) │                      │  SQLite (demo      │
                        │       API          │                      │  usage per device) │
                        └───────────────────┘                      └────────────────────┘
```

**Major subsystems:**
- **Client** — PySide6 desktop app. Owns UI state, local secret storage (Windows Credential Manager via `keyring`), and background networking (via `QThreadPool` workers so the UI never blocks).
- **Backend** — FastAPI, stateless per-request except for a SQLite-backed demo-usage counter. Single entry point (`/chat`) routes to the BYOK or demo path based on which header is present.
- **LLM layer** — a small **LangGraph** graph (`backend/agent/`) around Google Gemini via `langchain-google-genai`: a primary model (`gemini-3.5-flash-lite`) and a fallback (`gemini-3.1-flash-lite`) that takes over on rate limits, 5xx errors or timeouts, but only if the primary failed before the user saw any text. All LLM access goes through one module, `services/chat_service.py`.
- **Deployment** — Docker Compose on an Azure VM (Azure for Students, Ubuntu 24.04), with a named volume for SQLite persistence across container restarts.

### Low-Level Design (LLD)

**API surface:**

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/chat` | POST | `X-Gemini-Key` \| `X-Device-Id` | Streams a Gemini response via SSE |
| `/quota/status` | GET | `X-Device-Id` | Returns demo usage + limit |
| `/health` | GET | — | Liveness plus a database round-trip |

**Database schema (SQLite):**

```
devices(device_id PK, request_count)
```

**Request routing logic in `/chat`** (checked in order, first match wins):
1. `X-Gemini-Key` present → BYOK path, no quota. The key is forwarded to Gemini for that request only; it is not stored or logged.
2. `X-Device-Id` present → demo path on the backend's own key, subject to three caps checked together in one transaction (see *Demo abuse model*). A request that fails before Gemini answers is refunded.
3. None present → `400`

**SSE protocol:** each event is `data: <JSON-encoded text chunk>\n\n`. Chunks are JSON-encoded so embedded newlines can't break SSE's line-based framing (see *Bugs Found and Fixed*), and so model text can never be mistaken for a control frame: a JSON string always starts with a quote. Control frames are raw: `data: [ERROR: <message>]` for a failure after the stream began, and `data: [DONE]` to close. Failures *before* the first token return a real HTTP status (400 bad key/request, 503 rate limit, 504 timeout, 502 otherwise) with a safe message.

**Client threading model:** every network call (`StreamWorker`, `QuotaCheckWorker`) is a `QRunnable` submitted to a shared `QThreadPool`, communicating results back via Qt signals. Two lifetime-management details were necessary and non-obvious (see *Bugs Found and Fixed*): explicit Python-side reference tracking (`_track`/`_untrack`), and disabling Qt's own `autoDelete`.

## Design Decisions

**BYOK plus a small lifetime demo, no accounts.** BYOK gives unlimited use with zero cost or liability to the developer. The demo gives anyone a taste (10 requests per device, ever) on the backend's own key. There are deliberately no user accounts: without identity the demo cap is a fairness limit, not a security boundary, so the backend's key is meant to live on a project with no billing attached.

**Demo abuse model.** Device ids are generated by the client, so anyone can mint a fresh one with `curl`; the per-device cap (10 requests, lifetime) is a fairness limit, not security. Spend is bounded by two server-side counters instead: a **per-IP daily cap** (default 30) and a **global daily cap** (default 300), all in UTC. The three counters are bumped together in a single transaction, each with one atomic `INSERT ... ON CONFLICT DO UPDATE ... WHERE count < limit`, so concurrent requests cannot overshoot and a rejected request consumes nothing. A request that fails upstream before Gemini answers is refunded. Server-issued device tokens were considered and rejected: with IP and global caps they add a signing secret and client changes for almost no extra protection. Residual risk: a botnet with many IPs is bounded only by the global cap, and users behind one shared IP (campus, office) share the IP cap. Behind a reverse proxy, set `TRUST_FORWARDED_FOR=true` so the proxy-appended client IP is used (only the last `X-Forwarded-For` entry is trusted).

**SQLite, not MongoDB or Redis.** The data is small, fixed-shape, and single-instance — one row per device. MongoDB's flexible-schema strength isn't needed; Redis was not needed at this scale. SQLite needs zero extra infrastructure and fits comfortably on a free-tier VM.

**One model pair for every path.** BYOK and demo traffic use the same primary (`gemini-3.5-flash-lite`) and fallback (`gemini-3.1-flash-lite`), both configurable. A live benchmark (see `docs/decisions/README.md`) showed `3.1-flash-lite` is several times faster to first token than `3.5-flash-lite` with equal accuracy on reading screenshots; the fallback therefore also improves latency when the primary is slow or rate-limited.

**LangGraph, with the conversation held by the client.** The graph is deliberately small (`primary → fallback`), and failures are classified with LangChain's provider-neutral exception types rather than SDK internals. There is no checkpointer: each request carries the turns so far, so the server stores no conversations (a privacy and operations win), and a stale conversation id can no longer break a chat. The client trims history to the server's limits (40 turns, 60,000 characters). The honest trade-off: with one model call per request the framework's benefit is modest today; it earns more once a second tool (screen reading) joins the graph. Models are built per request inside the graph's closures, never passed through graph config, because config can end up in tracing metadata and the models hold the caller's API key.

**Azure, not AWS.** AWS EC2 was the original plan, but the available account had no active Free Tier at deployment time. Rather than accept unbounded on-demand cost, Azure for Students was used instead — genuinely free compute, no card required, functionally equivalent for this project's needs.

## Bugs Found and Fixed

Three genuine, non-obvious bugs surfaced during development. Each is stated here as a finding, not a narrated debugging log:

- **SSE payload corruption on embedded newlines.** Streamed text chunks occasionally contained literal newline characters, which silently broke SSE's line-based framing and truncated content mid-response. Found by comparing Gemini's own reported `total_output_tokens` against the actual length of received text — a measurable, confirmed discrepancy, not a rendering guess. Fixed by JSON-encoding each chunk before transport and decoding on receipt.
- **`QRunnable`'s default `autoDelete` causing a use-after-free crash.** Qt auto-deletes a `QRunnable` the instant `run()` returns — a mechanism entirely independent of Python's own reference counting. A slow, multi-second background network call exposed a race between this auto-deletion and an in-flight signal emission. Fixed with `setAutoDelete(False)` on every worker, combined with explicit Python-side lifetime tracking.
- **Silent application quit via `quitOnLastWindowClosed`.** Qt's default behavior fully quits the application once it believes the "last window" has closed. A frameless, `Qt.Tool`-flagged persistent tray icon isn't counted as a "real" window under this logic — so closing any modal dialog silently terminated the entire app, with no error or traceback. Fixed with an explicit `app.setQuitOnLastWindowClosed(False)`.

## Future Work

- **HTTPS on the deployed backend.** The backend is currently served over plain HTTP, so BYOK API keys travel unencrypted. A production version would add Caddy or nginx with automatic TLS in front of the FastAPI service.
- **Retry/backoff for transient Gemini errors.** The app surfaces `503`/high-demand errors cleanly but doesn't yet auto-retry.

## Setup

### Running locally

```bash
# Backend (Docker)
cd backend
cp .env.example .env     # optional: set BACKEND_GEMINI_KEY to enable the demo
docker compose up --build

# Backend (without Docker) + tests
cd backend
pip install -r requirements-dev.txt
uvicorn main:app --reload
pytest

# Client
cd client
pip install -r requirements.txt
python main.py
```

Configuration is read from environment variables (or `backend/.env`) and validated at startup; see `backend/.env.example` for every setting and its default.

### Tests and CI

`pytest` (backend, 64 tests) covers quota caps including concurrency and rollback, request routing, input validation, the graph's failover rules, error classification, SSE framing and client-disconnect safety; the client's history logic has its own small suite. GitHub Actions runs `ruff` and `pytest` on every push and pull request.

### Distribution

The client is packaged into a standalone Windows executable via PyInstaller:

```bash
pyinstaller --name=AskOverlay --windowed --onefile ^
  --icon=assets/askoverlay.ico --add-data "assets;assets" ^
  --hidden-import=keyring.backends.Windows main.py
```

See `DEPLOYMENT.md` for Azure deployment and restart/shutdown procedures.

**Note:** a packaged `.exe` build exists but isn't distributed as a public download here, since it points at a live, shared backend with a bounded, free-tier quota rather than a self-hosted instance — happy to share it directly on request.