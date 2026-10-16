import base64
import logging

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

import redaction
from agent.graph import SCREEN_PROMPT, SYSTEM_PROMPT, build_graph, to_messages, visible_text
from agent.screenshot import MAX_SCREENSHOT_BYTES, parse_screenshot
from tests.fakes import ScriptedChat

JPEG = b"\xff\xd8\xff\xe0" + b"fake-jpeg-body"
PNG = b"\x89PNG\r\n\x1a\n" + b"fake-png-body"


def b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


# ── validation ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw, mime", [(JPEG, "image/jpeg"), (PNG, "image/png")])
def test_accepts_jpeg_and_png(raw, mime):
    shot = parse_screenshot(b64(raw))
    assert shot.mime == mime
    assert shot.data_url == f"data:{mime};base64,{b64(raw)}"


@pytest.mark.parametrize(
    "encoded, reason",
    [
        ("", "empty"),
        ("not base64 at all!!", "not valid base64"),
        (b64(b"GIF89a-not-allowed"), "JPEG or PNG"),
        (b64(b"plain text"), "JPEG or PNG"),
        (b64(JPEG + b"x" * MAX_SCREENSHOT_BYTES), "too large"),
    ],
    ids=["empty", "not-base64", "gif", "text", "too-large"],  # the default ids would embed the 2 MB value
)
def test_rejects_anything_else_without_echoing_it(encoded, reason):
    with pytest.raises(ValueError, match=reason) as error:
        parse_screenshot(encoded)
    if encoded:
        assert encoded[:40] not in str(error.value)


def test_the_size_limit_is_exact():
    parse_screenshot(b64(JPEG + b"x" * (MAX_SCREENSHOT_BYTES - len(JPEG))))
    with pytest.raises(ValueError, match="too large"):
        parse_screenshot(b64(JPEG + b"x" * (MAX_SCREENSHOT_BYTES - len(JPEG) + 1)))


# ── what the model receives ───────────────────────────────────────────────────

def test_without_a_screenshot_the_messages_are_unchanged():
    messages = to_messages([("user", "a"), ("assistant", "b")], "hello")
    assert messages[0] == SystemMessage(SYSTEM_PROMPT)
    assert messages[-1] == HumanMessage("hello")


def test_a_screenshot_is_attached_to_the_newest_message_only():
    shot = parse_screenshot(b64(PNG))
    messages = to_messages([("user", "earlier"), ("assistant", "reply")], "what is this?", shot)
    assert messages[0].content == SYSTEM_PROMPT + SCREEN_PROMPT
    assert messages[1].content == "earlier"  # history stays plain text
    assert messages[-1].content == [
        {"type": "text", "text": "what is this?"},
        {"type": "image_url", "image_url": {"url": shot.data_url}},
    ]


def test_the_fallback_model_receives_the_same_screenshot():
    from langchain_core.exceptions import ModelRateLimitError
    import asyncio

    shot = parse_screenshot(b64(JPEG))
    primary = ScriptedChat(model="p", script=[ModelRateLimitError("429")], seen=[])
    fallback = ScriptedChat(model="f", script=["ok"], seen=[])
    graph = build_graph(primary, fallback)

    async def go():
        out = ""
        async for chunk, _ in graph.astream(
            {"messages": to_messages([], "q", shot), "failed_over": False}, stream_mode="messages"
        ):
            out += visible_text(chunk)
        return out

    assert asyncio.run(go()) == "ok"
    for model in (primary, fallback):
        assert model.seen[0][-1].content[1]["image_url"]["url"] == shot.data_url


# ── screenshots never reach the logs ──────────────────────────────────────────

def test_redact_removes_data_urls_and_long_base64():
    secret = b64(PNG * 200)
    text = f"request failed: data:image/png;base64,{secret} and raw {secret}"
    cleaned = redaction.redact(text)
    assert secret[:50] not in cleaned
    assert "request failed" in cleaned


def test_redact_leaves_ordinary_text_alone():
    assert redaction.redact("model=gemini history_turns=3 screenshot=yes") == "model=gemini history_turns=3 screenshot=yes"


def test_the_log_filter_covers_messages_arguments_and_tracebacks():
    secret = b64(JPEG * 300)
    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(self.format(record))

    handler = Capture()
    handler.addFilter(redaction.RedactImagesFilter())
    logger = logging.getLogger("askoverlay.test-redaction")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        logger.info("with argument %s", f"data:image/jpeg;base64,{secret}")
        try:
            raise RuntimeError(f"provider echoed the request: {secret}")
        except RuntimeError:
            logger.error("failed", exc_info=True)
    finally:
        logger.removeHandler(handler)
    assert len(records) == 2
    assert all(secret[:50] not in line for line in records)
    assert "provider echoed the request" in records[1]  # the rest of the traceback is still there
