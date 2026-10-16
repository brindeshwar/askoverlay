# ADR-0005: BYOK plus a lifetime demo; no accounts, no payments

- Status: Accepted
- Date: 2026-10-09

**Context.** V1 shipped Google OAuth, JWT sessions, a users table, and PayPal billing. The OAuth flow
lacked `state`/PKCE, stored an unused refresh token, and the deployed billing webhook could not work
over plain HTTP. The surface area was large relative to the value for a portfolio project.

**Decision.** Two access modes only: bring-your-own Gemini key (unlimited, zero cost to the developer)
or a demo of 10 requests per device, lifetime, on the backend's key. All accounts, JWTs, OAuth and
billing were deleted.

**Consequences.** Without identity, the demo cannot be protected per user (see ADR-0006). The backend's
key must live on a project with no billing attached. Conversation history is to be held by the client
(ADR-0007).
