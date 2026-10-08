import json
import logging
from collections.abc import AsyncIterator
import httpx
from google import genai
from google.genai import types

log = logging.getLogger("askoverlay.gemini")

SYSTEM_INSTRUCTION = "You are a helpful assistant. Use markdown formatting naturally where it helps clarity (headers, bold, bullet points, code blocks)."


class GeminiError(Exception):
    """A failure talking to Gemini, already translated into an HTTP status and a safe message."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _translate(exc: Exception) -> GeminiError:
    """Map a Gemini/transport exception to a status code and a message safe to show users.

    Gemini's own 429 is reported as 503: the client treats 429 from this backend as
    "demo quota used up", which is a different condition.
    """
    if isinstance(exc, (TimeoutError, httpx.TimeoutException)) or type(exc).__name__ == "APITimeoutError":
        return GeminiError(504, "Gemini took too long to respond. Try again.")

    status = _status_of(exc)
    if status == 429:
        return GeminiError(503, "Gemini is rate-limiting requests right now. Try again in a moment.")
    if status in (400, 401, 403, 404):
        return GeminiError(400, "Gemini rejected the request. Check your API key, or start a new conversation.")
    if status is not None:
        return GeminiError(502, "Gemini is temporarily unavailable. Try again shortly.")
    return GeminiError(502, "Could not reach Gemini. Try again shortly.")


def _status_of(exc: Exception) -> int | None:
    """HTTP status carried by a Gemini SDK exception, or None.

    The SDK has two exception families: classic calls raise errors.APIError (`.code`),
    the Interactions API raises its own APIStatusError subclasses (`.status_code`, in a
    private module). Duck-typing on the attribute avoids importing the private classes.
    """
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None


def _frame(text: str) -> str:
    # JSON-encoded so embedded newlines can't break SSE's line-based framing.
    return f"data: {json.dumps(text)}\n\n"


async def _close(client: genai.Client) -> None:
    try:
        await client.aio.aclose()
    except Exception:
        log.debug("Ignoring error while closing Gemini client", exc_info=True)


async def start_stream(
    api_key: str,
    model: str,
    message: str,
    previous_interaction_id: str | None,
    timeout_seconds: float,
) -> AsyncIterator[str]:
    """Open a streaming Gemini interaction and return an async iterator of SSE lines.

    The request is sent *before* returning, so failures that happen up front (bad
    key, rate limit, unreachable) raise GeminiError and the route can answer with a
    real HTTP status instead of a 200 whose body is an error.
    """
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),  # milliseconds
    )

    kwargs = {
        "model": model,
        "input": message,
        "system_instruction": SYSTEM_INSTRUCTION,
        "stream": True,
    }
    if previous_interaction_id:
        kwargs["previous_interaction_id"] = previous_interaction_id

    log.info(f"Calling Gemini: model={model}, has_previous_id={bool(previous_interaction_id)}")

    try:
        events = await client.aio.interactions.create(**kwargs)
    except Exception as e:
        await _close(client)
        log.error(f"Gemini request failed before streaming: {e}", exc_info=True)
        raise _translate(e) from e

    return _sse_lines(client, events)


async def _sse_lines(client: genai.Client, events) -> AsyncIterator[str]:
    new_interaction_id = None
    event_count = 0
    try:
        try:
            async for event in events:
                event_count += 1
                log.debug(f"Event #{event_count}: type={event.event_type}")
                if event.event_type == "step.delta" and event.delta.type == "text":
                    yield _frame(event.delta.text)
                elif event.event_type == "interaction.completed":
                    new_interaction_id = event.interaction.id
                    log.info(f"Completed: id={new_interaction_id}, usage={event.interaction.usage}")
                elif event.event_type == "error":
                    log.error(f"Gemini stream error event: {event.error.message} (code={event.error.code})")
                    yield _frame("[ERROR: Gemini reported an error while answering. Try again.]")
        except Exception as e:
            # Mid-stream failure: the 200 status is already sent, so report in-band.
            log.error(f"Exception during stream: {e}", exc_info=True)
            yield _frame(f"[ERROR: {_translate(e).detail}]")

        if new_interaction_id:
            yield f"data: [INTERACTION_ID:{new_interaction_id}]\n\n"
        yield "data: [DONE]\n\n"
    finally:
        # No yields here: if the client disconnects, the generator is closed and a
        # yield in this block would raise. Cleanup only.
        await _close(client)
        log.info(f"Stream closed after {event_count} events")
