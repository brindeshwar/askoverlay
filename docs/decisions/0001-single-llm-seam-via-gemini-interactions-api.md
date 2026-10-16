# ADR-0001: Single LLM seam via the Gemini Interactions API

- Status: Superseded
- Date: 2026-10-05
- Related: Superseded in part by ADR-0007.
- Status detail: Superseded in part by ADR-0007 (the single seam stays, now `services/chat_service.py`; the Interactions API and server-side memory are replaced)

All LLM access goes through one module (`services/gemini_service.py`), using the Interactions API with
streaming and `previous_interaction_id` for server-side memory. Good for V1: memory for free, one place
to change LLM behaviour. Problems found later: interaction ids expire and likely belong to the API key
that created them, so a stale id or a switch from the demo key to a user's own key breaks the next turn,
and server-side memory means conversations live on Google's side, outside our control.
