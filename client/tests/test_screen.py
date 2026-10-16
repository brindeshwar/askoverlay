import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

import screen  # noqa: E402


@pytest.mark.parametrize(
    "size, expected",
    [
        ((1920, 1080), (1280, 720)),
        ((2560, 1440), (1280, 720)),
        ((3840, 2160), (1280, 720)),
        ((1080, 1920), (720, 1280)),  # portrait monitor: the long side is the height
        ((1280, 720), (1280, 720)),  # already small enough: unchanged
        ((800, 600), (800, 600)),  # never enlarged
        ((1281, 1), (1280, 1)),  # extreme shape: never collapses to zero
        ((10000, 3), (1280, 1)),
    ],
)
def test_fit_within_keeps_the_aspect_ratio_and_never_enlarges(size, expected):
    assert screen.fit_within(*size) == expected


def test_fit_within_respects_a_custom_limit():
    assert screen.fit_within(1000, 500, max_side=100) == (100, 50)


def test_the_payload_has_no_screenshot_key_when_there_is_none():
    assert screen.chat_payload("hi", []) == {"message": "hi", "history": []}
    assert screen.chat_payload("hi", [], None) == {"message": "hi", "history": []}
    assert screen.chat_payload("hi", [], "") == {"message": "hi", "history": []}


def test_the_payload_carries_the_screenshot_for_this_message_only():
    history = [{"role": "user", "content": "earlier"}]
    payload = screen.chat_payload("what is this?", history, "QUJD")
    assert payload == {"message": "what is this?", "history": history, "screenshot": "QUJD"}
    assert "screenshot" not in history[0]  # history stays text


def test_the_size_budget_is_below_the_servers_limit():
    server_limit = 1_500_000  # backend/agent/screenshot.py MAX_SCREENSHOT_BYTES
    assert screen.MAX_ENCODED_BYTES < server_limit


def test_window_exclusion_is_only_attempted_on_a_new_enough_windows(monkeypatch):
    monkeypatch.setattr(screen.sys, "platform", "linux")
    assert screen.can_exclude_from_capture() is False

    monkeypatch.setattr(screen.sys, "platform", "win32")
    monkeypatch.setattr(screen.sys, "getwindowsversion", lambda: type("V", (), {"build": 18363})(), raising=False)
    assert screen.can_exclude_from_capture() is False  # Windows 10 1909: would show a black box

    monkeypatch.setattr(screen.sys, "getwindowsversion", lambda: type("V", (), {"build": 19045})(), raising=False)
    assert screen.can_exclude_from_capture() is True
