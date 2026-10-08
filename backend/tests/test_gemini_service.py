import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from services import gemini_service as svc


class FakeClient:
    def __init__(self):
        self.closed = False
        self.aio = SimpleNamespace(aclose=self._aclose)

    async def _aclose(self):
        self.closed = True


def delta(text):
    return SimpleNamespace(event_type="step.delta", delta=SimpleNamespace(type="text", text=text))


def completed(interaction_id):
    return SimpleNamespace(event_type="interaction.completed", interaction=SimpleNamespace(id=interaction_id, usage=None))


async def events_of(*items, then_raise=None):
    for item in items:
        yield item
    if then_raise:
        raise then_raise


async def collect(gen):
    return [line async for line in gen]


def decode(line):
    return json.loads(line[len("data: "):])


def interactions_error(status):
    """A real Interactions-API exception, built with the SDK's own factory."""
    from google.genai._gaos.lib import compat_errors

    request = httpx.Request("POST", "https://generativelanguage.googleapis.com/")
    response = httpx.Response(status, request=request)
    return compat_errors.APIError.generate(status, {"error": {"message": "x"}}, None, response)


def interactions_timeout():
    from google.genai._gaos.lib import compat_errors

    return compat_errors.APITimeoutError(httpx.Request("POST", "https://generativelanguage.googleapis.com/"))


@pytest.mark.parametrize(
    "exc, status",
    [
        # Interactions API family (.status_code) - what /chat actually hits
        (interactions_error(429), 503),  # never 429: that means "demo used up"
        (interactions_error(400), 400),  # e.g. "API key not valid"
        (interactions_error(401), 400),
        (interactions_error(403), 400),
        (interactions_error(404), 400),  # e.g. unknown previous_interaction_id
        (interactions_error(500), 502),
        (interactions_error(503), 502),
        (interactions_timeout(), 504),
        # Classic family (.code)
        (errors.ClientError(429, {"error": {"message": "quota"}}), 503),
        (errors.ClientError(400, {"error": {"message": "API key not valid"}}), 400),
        (errors.ServerError(500, {"error": {"message": "boom"}}), 502),
        # Transport-level
        (TimeoutError("read timed out"), 504),
        (httpx.ConnectError("refused"), 502),
        (RuntimeError("anything else"), 502),
    ],
)
def test_translate_maps_gemini_failures(exc, status):
    assert svc._translate(exc).status_code == status


def test_translate_never_leaks_raw_exception_text():
    secret = "internal path /srv/x key=AIza123"
    assert secret not in svc._translate(RuntimeError(secret)).detail


def test_stream_frames_ids_and_done_in_order():
    client = FakeClient()
    lines = asyncio.run(collect(svc._sse_lines(client, events_of(delta("Hel"), delta("lo\nworld"), completed("id-9")))))
    assert [decode(line) for line in lines[:2]] == ["Hel", "lo\nworld"]  # newline survives SSE framing
    assert lines[2] == "data: [INTERACTION_ID:id-9]\n\n"
    assert lines[3] == "data: [DONE]\n\n"
    assert client.closed


def test_mid_stream_failure_is_reported_in_band_and_still_terminates():
    client = FakeClient()
    exc = interactions_error(500)
    lines = asyncio.run(collect(svc._sse_lines(client, events_of(delta("partial"), then_raise=exc))))
    assert decode(lines[0]) == "partial"
    assert decode(lines[1]).startswith("[ERROR:")
    assert "boom internals" not in lines[1]
    assert lines[-1] == "data: [DONE]\n\n"
    assert client.closed


def test_client_disconnect_closes_cleanly_without_yielding_in_finally():
    client = FakeClient()

    async def scenario():
        gen = svc._sse_lines(client, events_of(delta("a"), delta("b"), completed("x")))
        first = await gen.__anext__()
        await gen.aclose()  # what Starlette does when the client goes away
        return first

    assert decode(asyncio.run(scenario())) == "a"  # no RuntimeError from the generator
    assert client.closed


def test_start_stream_translates_upfront_errors_and_closes_client(monkeypatch):
    client = FakeClient()

    async def failing_create(**kwargs):
        raise interactions_error(429)

    client.aio.interactions = SimpleNamespace(create=failing_create)
    monkeypatch.setattr(svc.genai, "Client", lambda **kw: client)

    with pytest.raises(svc.GeminiError) as info:
        asyncio.run(svc.start_stream("k", "m", "hi", None, 5))
    assert info.value.status_code == 503
    assert client.closed


async def _run_start(coro):
    return await collect(await coro)


def test_start_stream_sends_expected_request(monkeypatch):
    client = FakeClient()
    seen = {}

    async def create(**kwargs):
        seen.update(kwargs)
        return events_of(completed("z"))

    client.aio.interactions = SimpleNamespace(create=create)
    built = {}

    def build_client(**kw):
        built.update(kw)
        return client

    monkeypatch.setattr(svc.genai, "Client", build_client)

    lines = asyncio.run(_run_start(svc.start_stream("k", "gemini-3.5-flash-lite", "hi", "prev", 12)))
    assert seen["model"] == "gemini-3.5-flash-lite"
    assert seen["previous_interaction_id"] == "prev"
    assert seen["stream"] is True
    assert built["http_options"].timeout == 12000  # milliseconds
    assert lines[-1] == "data: [DONE]\n\n"
