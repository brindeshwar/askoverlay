import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from history import MAX_HISTORY_CHARS, MAX_TURNS, remember_exchange, trim_history  # noqa: E402


def turn(role, text="x"):
    return {"role": role, "content": text}


def test_short_history_is_unchanged_and_not_mutated():
    history = [turn("user", "hi"), turn("assistant", "hello")]
    assert trim_history(history) == history
    assert trim_history(history) is not history


def test_oldest_turns_are_dropped_first_when_over_the_turn_limit():
    history = [turn("user" if i % 2 == 0 else "assistant", str(i)) for i in range(MAX_TURNS + 10)]
    trimmed = trim_history(history)
    assert len(trimmed) <= MAX_TURNS
    assert trimmed[-1] == history[-1]  # the newest turn always survives


def test_character_budget_is_respected():
    history = [turn("user", "a" * 20_000), turn("assistant", "b" * 20_000), turn("user", "c" * 20_000), turn("assistant", "d" * 20_000)]
    trimmed = trim_history(history)
    assert sum(len(t["content"]) for t in trimmed) <= MAX_HISTORY_CHARS
    assert trimmed[-1]["content"].startswith("d")


def test_result_never_starts_with_an_assistant_turn():
    history = [turn("user", "a" * 30_000), turn("assistant", "b" * 30_000), turn("user", "q"), turn("assistant", "r")]
    trimmed = trim_history(history)
    assert trimmed and trimmed[0]["role"] == "user"


def test_a_single_oversized_turn_is_dropped_rather_than_breaking_the_request():
    assert trim_history([turn("user", "z" * (MAX_HISTORY_CHARS + 1))]) == []


def test_remember_exchange_appends_user_then_assistant():
    history = []
    remember_exchange(history, "question", "answer")
    assert history == [turn("user", "question"), turn("assistant", "answer")]
