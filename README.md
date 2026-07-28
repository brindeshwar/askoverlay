# AskOverlay

A Windows always-on-top desktop AI assistant. Click a small draggable icon, ask a question about anything you're looking at, get a streamed, formatted answer — no window switching required.

Built as a portfolio project demonstrating full-stack AI application development: a PySide6 desktop client, a Dockerized FastAPI backend, and a live cloud deployment — with production-style concerns (authentication, billing, tiered quotas, session memory) implemented deliberately, not assumed away.

## Features

- **Three access tiers through one endpoint:**
  - **BYOK** — paste your own Gemini API key, unlimited use, zero cost or liability to the developer
  - **Anonymous free tier** — 10 requests/day, no signup required
  - **Google-authenticated free/premium** — 10 or 100 requests/day, upgradeable via a real PayPal payment flow
- Real-time streaming responses (SSE) with live markdown rendering (headers, bold, lists)
- Multi-turn session memory via Gemini's server-side Interactions API
- Frameless, draggable, always-on-top overlay window with a persistent tray-managed lifecycle (no taskbar presence)
- Dockerized backend, deployed and tested on a live Azure VM
- Packaged, distributable standalone Windows executable (PyInstaller)

## System Design

### High-Level Design (HLD)

```
┌─────────────────┐        HTTPS / SSE        ┌──────────────────┐
│  PySide6 Client  │ ────────────────────────► │  FastAPI Backend │
│  (Windows .exe)  │ ◄──────────────────────── │   (Dockerized)   │
└─────────────────┘                            └──────────────────┘
                                                        │
                        ┌───────────────────────────────┼───────────────────────────────┐
                        │                                │                               │
                        ▼                                ▼                               ▼
              ┌───────────────────┐           ┌────────────────────┐          ┌────────────────────┐
              │ Gemini Interactions│           │   SQLite (Users,   │          │  Google OAuth /     │
              │       API          │           │     Devices)       │          │     PayPal          │
              └───────────────────┘           └────────────────────┘          └────────────────────┘
```

**Major subsystems:**
- **Client** — PySide6 desktop app. Owns UI state, local secret storage (Windows Credential Manager via `keyring`), and background networking (via `QThreadPool` workers so the UI never blocks).
- **Backend** — FastAPI, stateless per-request except for SQLite-backed quota/user data. Single entry point (`/chat`) routes to one of three auth paths based on which header is present.
- **LLM layer** — Google Gemini, accessed through the **Interactions API** rather than manual message-history resending — the server keeps conversation state, the client just passes a `previous_interaction_id` forward.
- **Deployment** — Docker Compose on an Azure VM (Azure for Students, Ubuntu 24.04), with a named volume for SQLite persistence across container restarts.

### Low-Level Design (LLD)

**API surface:**

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/chat` | POST | `X-Gemini-Key` \| `X-Session-Token` \| `X-Device-Id` | Streams a Gemini response via SSE |
| `/quota/status` | GET | `X-Session-Token` \| `X-Device-Id` | Returns current tier + usage |
| `/auth/google/login` | GET | — | Returns a Google consent URL |
| `/auth/google/callback` | POST | — | Exchanges auth code for tokens, issues session JWT |
| `/billing/checkout` | POST | `X-Session-Token` | Creates a PayPal order, returns approval URL |
| `/billing/webhook` | POST | PayPal signature | Verifies + captures payment, upgrades tier |

**Database schema (SQLite):**

```
devices(device_id PK, request_count, last_reset_date)
users(id PK, google_id UNIQUE, email, name, refresh_token, tier, request_count, last_reset_date)
```

**Request routing logic in `/chat`** (checked in order, first match wins):
1. `X-Gemini-Key` present → BYOK path, no quota, backend never sees or stores this key
2. `X-Session-Token` present → decode JWT, look up user, enforce free (10/day) or premium (100/day) limit
3. `X-Device-Id` present → anonymous path, 10/day, tracked by device UUID
4. None present → `400`

**SSE protocol:** each event is `data: <JSON-encoded chunk>\n\n`. Chunks are JSON-encoded specifically to survive embedded newlines safely inside SSE's line-based framing (see *Bugs Found and Fixed*). Two sentinels close the stream: `data: [INTERACTION_ID:<id>]\n\n` (carries the new conversation-thread ID forward) and `data: [DONE]\n\n`.

**Session JWT:** `{"sub": "<user_id>", "exp": <30-day expiry>}`, signed `HS256` with a server-held secret. Never contains the Google refresh token — that stays server-side in SQLite.

**Client threading model:** every network call (`StreamWorker`, `QuotaCheckWorker`, `LoginWorker`, `CheckoutWorker`) is a `QRunnable` submitted to a shared `QThreadPool`, communicating results back via Qt signals. Two lifetime-management details were necessary and non-obvious (see *Bugs Found and Fixed*): explicit Python-side reference tracking (`_track`/`_untrack`), and disabling Qt's own `autoDelete`.

## Design Decisions

**BYOK and OAuth/payments coexist, deliberately.** Rather than picking a single cost model, both are supported: BYOK for zero-liability unlimited use, and a backend-funded tiered system with a real payment flow for users who'd rather not manage their own API key. The header-based routing (`X-Gemini-Key` vs `X-Session-Token` vs `X-Device-Id`) keeps these fully independent at the API layer.

**SQLite, not MongoDB or Redis.** The data is small, fixed-shape, and single-instance — one row per user or device. MongoDB's flexible-schema strength isn't needed; Redis was considered for session-token caching, but there's no functional need at this scale. SQLite needs zero extra infrastructure and fits comfortably on a free-tier VM.

**Model split by cost-liability, not preference.** `gemini-3.5-flash` for BYOK (the user's own quota), `gemini-2.5-flash-lite` for anything running on the backend's own key (anonymous/free/premium tiers) — the cheaper model bounds real exposure on the only traffic the developer actually pays for.

**Gemini's Interactions API over LangChain, for session memory.** LangChain's memory classes (`ConversationBufferMemory` and siblings) are deprecated as of v0.3.1 and slated for removal, with the ecosystem moving toward LangGraph — a full agent-orchestration framework, disproportionate for a single linear chat history. The Interactions API provides equivalent server-side state with implicit caching, natively, with no added dependency risk.

**Backend-mediated OAuth, not client-embedded.** The desktop client never holds `client_secret` — it only captures the authorization code from a local loopback redirect and forwards it to the backend, which performs the actual token exchange. This mirrors Google's own documented "one-time-code flow" for exactly this split, rather than the more common (and less secure) pattern of embedding the secret directly in a distributed desktop app.

**Azure, not AWS.** AWS EC2 was the original plan, but the available account had no active Free Tier at deployment time. Rather than accept unbounded on-demand cost, Azure for Students was used instead — genuinely free compute, no card required, functionally equivalent for this project's needs.

**PayPal, not Stripe or Razorpay.** Stripe requires an invitation to onboard new accounts in India. Razorpay's test mode required a personal PAN just to reach the dashboard — a reasonable requirement for a real business, not one worth trading for a portfolio demo. PayPal's developer sandbox is a fully synthetic environment requiring neither.

## Bugs Found and Fixed

Three genuine, non-obvious bugs surfaced during development. Each is stated here as a finding, not a narrated debugging log:

- **SSE payload corruption on embedded newlines.** Streamed text chunks occasionally contained literal newline characters, which silently broke SSE's line-based framing and truncated content mid-response. Found by comparing Gemini's own reported `total_output_tokens` against the actual length of received text — a measurable, confirmed discrepancy, not a rendering guess. Fixed by JSON-encoding each chunk before transport and decoding on receipt.
- **`QRunnable`'s default `autoDelete` causing a use-after-free crash.** Qt auto-deletes a `QRunnable` the instant `run()` returns — a mechanism entirely independent of Python's own reference counting. A slow, multi-second background task (a two-step PayPal API call) exposed a race between this auto-deletion and an in-flight signal emission. Fixed with `setAutoDelete(False)` on every worker, combined with explicit Python-side lifetime tracking.
- **Silent application quit via `quitOnLastWindowClosed`.** Qt's default behavior fully quits the application once it believes the "last window" has closed. A frameless, `Qt.Tool`-flagged persistent tray icon isn't counted as a "real" window under this logic — so closing any modal dialog silently terminated the entire app, with no error or traceback. Fixed with an explicit `app.setQuitOnLastWindowClosed(False)`.

## Future Work

- **HTTPS on the deployed backend.** PayPal's webhook requires HTTPS; currently verified via an `ngrok` tunnel rather than a permanent solution. A production version would add Caddy or nginx with automatic TLS in front of the FastAPI service.
- **Retry/backoff for transient Gemini errors.** The app surfaces `503`/high-demand errors cleanly but doesn't yet auto-retry.
- **Merge anonymous and authenticated quotas.** Currently independent — a user could exhaust an anonymous 10/day, then sign in for a fresh 10/day. Low-stakes here, but a real gap in a production system.
- **Move the backend's own Gemini key off the free tier.** Currently bounded by Google's own rate limits, beneath the app's own quota system. Enabling Cloud Billing would remove this ceiling.
- **Redis as a session-token cache**, once running more than a single backend instance.

## Setup

### Running locally

```bash
# Backend
cd backend
docker compose up --build

# Client
cd client
pip install -r requirements.txt
python main.py
```

### Distribution

The client is packaged into a standalone Windows executable via PyInstaller:

```bash
pyinstaller --name=AskOverlay --windowed --onefile ^
  --icon=assets/askoverlay.ico --add-data "assets;assets" ^
  --hidden-import=keyring.backends.Windows main.py
```

See `DEPLOYMENT.md` for Azure deployment and restart/shutdown procedures.

**Note:** a packaged `.exe` build exists but isn't distributed as a public download here, since it points at a live, shared backend with a bounded, free-tier quota rather than a self-hosted instance — happy to share it directly on request.