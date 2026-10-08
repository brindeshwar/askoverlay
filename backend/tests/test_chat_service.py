import asyncio
import json

import httpx
import pytest
from langchain_core.exceptions import (
    ContextOverflowError,
    ModelAPIError,
    ModelAuthenticationError,
    ModelInvalidRequestError,
    ModelNotFoundError,
    ModelPermissionDeniedError,
    ModelRateLimitError,
    ModelTimeoutError,
)

from agent.errors import ChatError, is_transient, translate
from services import chat_service as svc
from tests.conftest import make_settings
from tests.fakes import ScriptedChat


def decode(line):
    return json.loads(line[len("data: "):])


async def collect(gen):
    return [line async for line in gen]


@pytest.fixture
def models(monkeypatch):
    """Control the primary/fallback models: models["primary"] = ScriptedChat(...)."""
    registry = {"primary": ScriptedChat(model="primary", script=["ok"]), "fallback": ScriptedChat(model="fallback", script=["ok"])}
    created = []

    def fake_make_model(name, api_key, settings, max_retries):
        created.append(dict(name=name, api_key=api_key, max_retries=max_retries, timeout=settings.gemini_timeout_seconds))
        return registry["primary"] if name == settings.gemini_model else registry["fallback"]

    monkeypatch.setattr(svc, "make_model", fake_make_model)
    registry["created"] = created
    return registry


def start(history=None, message="hi", **settings):
    async def go():
        return await svc.start_chat_stream("key", history or [], message, make_settings(**settings))

    return asyncio.run(go())


def start_and_collect(**kw):
    async def go():
        lines = await svc.start_chat_stream("key", kw.pop("history", []), "hi", make_settings(**kw))
        return await collect(lines)

    return asyncio.run(go())


# --- streaming and framing ----------------------------------------------------------------------

def test_text_is_streamed_as_json_frames_then_done(models):
    models["primary"].script = ["Hel", "lo\nworld"]
    lines = start_and_collect()
    assert [decode(line) for line in lines[:-1]] == ["Hel", "lo\nworld"]  # newline survives SSE framing
    assert lines[-1] == "data: [DONE]\n\n"
    assert not any("INTERACTION_ID" in line for line in lines)  # the server keeps no conversation id any more


def test_models_are_built_with_the_configured_names_key_and_retry_policy(models):
    start_and_collect(gemini_model="primary", gemini_fallback_model="fallback", gemini_timeout_seconds=12)
    primary, fallback = models["created"]
    assert (primary["name"], primary["max_retries"]) == ("primary", 0)  # the fallback is the retry
    assert (fallback["name"], fallback["max_retries"]) == ("fallback", 1)
    assert primary["api_key"] == fallback["api_key"] == "key"
    assert primary["timeout"] == 12


def test_empty_fallback_name_disables_the_fallback(models):
    start_and_collect(gemini_model="primary", gemini_fallback_model="")
    assert [m["name"] for m in models["created"]] == ["primary"]


def test_fallback_answers_transparently_when_the_primary_is_rate_limited(models):
    models["primary"].script = [ModelRateLimitError("429")]
    models["fallback"].script = ["from fallback"]
    lines = start_and_collect(gemini_model="primary", gemini_fallback_model="fallback")
    assert decode(lines[0]) == "from fallback"
    assert lines[-1] == "data: [DONE]\n\n"


def test_history_reaches_the_model_in_order(models):
    seen = []
    original = models["primary"]._astream

    async def spy(messages, *a, **kw):
        seen.append([(type(m).__name__, m.content) for m in messages])
        async for chunk in original(messages, *a, **kw):
            yield chunk

    object.__setattr__(models["primary"], "_astream", spy)
    start_and_collect(history=[("user", "my name is Asha"), ("assistant", "hi Asha")])
    kinds = [kind for kind, _ in seen[0]]
    assert kinds == ["SystemMessage", "HumanMessage", "AIMessage", "HumanMessage"]
    assert seen[0][1][1] == "my name is Asha"


# --- failures ---------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "error, status",
    [
        (ModelInvalidRequestError("API key not valid"), 400),
        (ModelAuthenticationError("401"), 400),
        (ModelPermissionDeniedError("403"), 400),
        (ContextOverflowError("too long"), 400),
        (ModelNotFoundError("no such model"), 502),
        (ModelAPIError("500"), 502),
        (ModelTimeoutError("slow"), 504),
        (RuntimeError("something unexpected"), 502),
    ],
)
def test_upfront_failure_becomes_a_chat_error_with_a_real_status(models, error, status):
    models["primary"].script = [error]
    models["fallback"].script = [error]
    with pytest.raises(ChatError) as info:
        start(gemini_model="primary", gemini_fallback_model="fallback")
    assert info.value.status_code == status


def test_rate_limit_on_every_model_is_503_never_429(models):
    models["primary"].script = [ModelRateLimitError("429")]
    models["fallback"].script = [ModelRateLimitError("429")]
    with pytest.raises(ChatError) as info:
        start(gemini_model="primary", gemini_fallback_model="fallback")
    assert info.value.status_code == 503


def test_models_are_closed_after_an_upfront_failure(models):
    models["primary"].script = [ModelInvalidRequestError("bad key")]
    with pytest.raises(ChatError):
        start(gemini_model="primary", gemini_fallback_model="fallback")
    assert models["primary"].closed and models["fallback"].closed


def test_mid_stream_failure_is_reported_in_band_and_still_terminates(models):
    secret = "internal path /srv/app key=AIza123"
    models["primary"].script = ["partial", ModelAPIError(secret)]
    lines = start_and_collect(gemini_model="primary", gemini_fallback_model="fallback")
    assert decode(lines[0]) == "partial"
    assert lines[1].startswith("data: [ERROR: ")  # a raw control frame, never JSON text a client could store as an answer
    assert secret not in "".join(lines)  # raw exception text never reaches the client
    assert lines[-1] == "data: [DONE]\n\n"
    assert models["fallback"].calls == 0  # nothing to fail over to once text was shown


def test_a_model_that_returns_only_empty_text_gets_an_error_frame(models):
    models["primary"].script = [""]  # e.g. an answer blocked by a safety filter
    lines = start_and_collect(gemini_model="primary", gemini_fallback_model="")
    assert lines[0].startswith("data: [ERROR: ")
    assert lines[-1] == "data: [DONE]\n\n"


def test_model_text_that_looks_like_a_control_frame_stays_text(models):
    models["primary"].script = ["[ERROR: not really]"]
    lines = start_and_collect(gemini_model="primary", gemini_fallback_model="")
    assert decode(lines[0]) == "[ERROR: not really]"  # JSON-quoted, so a client cannot confuse it with an error


def test_a_model_that_returns_no_chunks_at_all_is_a_502(models):
    models["primary"].script = []  # LangChain itself raises "No generation chunks were returned"
    with pytest.raises(ChatError) as info:
        start(gemini_model="primary", gemini_fallback_model="")
    assert info.value.status_code == 502


def test_client_disconnect_closes_cleanly_without_yielding_in_finally(models):
    models["primary"].script = ["a", "b", "c"]

    async def scenario():
        gen = await svc.start_chat_stream("key", [], "hi", make_settings(gemini_model="primary", gemini_fallback_model=""))
        first = await gen.__anext__()
        await gen.aclose()  # what Starlette does when the client goes away
        return first

    assert decode(asyncio.run(scenario())) == "a"  # no RuntimeError from the generator
    assert models["primary"].closed


def test_models_are_closed_after_a_normal_stream(models):
    start_and_collect(gemini_model="primary", gemini_fallback_model="fallback")
    assert models["primary"].closed and models["fallback"].closed


# --- error classification (provider-neutral LangChain types) -----------------------------------------

def test_only_transient_errors_are_worth_a_fallback():
    transient = (ModelRateLimitError("x"), ModelAPIError("x"), ModelTimeoutError("x"), TimeoutError(), httpx.ConnectError("x"))
    permanent = (ModelInvalidRequestError("x"), ModelAuthenticationError("x"), ModelPermissionDeniedError("x"), ValueError("x"))
    assert all(is_transient(e) for e in transient)
    assert not any(is_transient(e) for e in permanent)


def test_translate_never_leaks_raw_exception_text():
    secret = "internal path /srv/x key=AIza123"
    for exc in (RuntimeError(secret), ModelAPIError(secret), ModelRateLimitError(secret), ModelInvalidRequestError(secret)):
        assert secret not in translate(exc).detail
