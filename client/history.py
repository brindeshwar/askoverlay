"""Conversation history, held by the client.

The server keeps no conversation state: every request carries the turns so far. This module keeps that
history within the limits the server enforces, so a long chat never starts failing with a 422.
"""

# Server limits (backend/routes/chat.py): at most 40 turns, and message + history <= 60,000 characters.
MAX_TURNS = 40
# Leaves room for the new message, which may be up to 8,000 characters.
MAX_HISTORY_CHARS = 50_000


def trim_history(history, max_turns=MAX_TURNS, max_chars=MAX_HISTORY_CHARS):
    """Return the newest turns that fit the limits, as a new list (the input is not modified).

    Turns are dropped oldest-first. The result never starts with an assistant turn, because a
    conversation should open with the user's message.
    """
    kept = []
    total = 0
    for turn in reversed(history):
        size = len(turn["content"])
        if len(kept) >= max_turns or total + size > max_chars:
            break
        kept.append(turn)
        total += size
    kept.reverse()
    while kept and kept[0]["role"] != "user":
        kept.pop(0)
    return kept


def remember_exchange(history, user_text, assistant_text):
    """Record a finished question/answer pair."""
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": assistant_text})
