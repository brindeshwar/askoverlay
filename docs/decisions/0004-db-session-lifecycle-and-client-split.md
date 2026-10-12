# ADR-0004: DB session lifecycle via `get_db`; client UI/dialogs split

- Status: Accepted
- Date: 2026-10-05
- Related: Refined by ADR-0006 (`/chat` does not use `get_db`).
- Status detail: Accepted, committed

`get_db` FastAPI dependency owns session cleanup for ordinary routes; `ui.py` (widgets) and
`dialogs.py` (modal flows) separated so widgets do not depend on auth. Refined by ADR-0006:
`/chat` does not use `get_db`, because a request-scoped session would stay open for the whole stream.
