"""Runs the chat graph and turns its token stream into Server-Sent Events.

This is the single LLM seam: routes call start_chat_stream(), never a model directly.
SSE frames: `data: <JSON-encoded text chunk>` ..., optionally `data: [ERROR: <message>]`, then `data: [DONE]`.
"""
import json
import logging
from collections.abc import AsyncIterator

from langchain_google_genai import ChatGoogleGenerativeAI

from agent.errors import ChatError, translate
from agent.graph import build_graph, to_messages, visible_text
from agent.screenshot import Screenshot
from config import Settings

log = logging.getLogger("askoverlay.chat_service")


def make_model(name: str, api_key: str, settings: Settings, max_retries: int) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=name,
        api_key=api_key,
        timeout=settings.gemini_timeout_seconds,
        # Library-level retries wait with backoff (tens of seconds on a 429); the fallback model is the retry.
        max_retries=max_retries,
    )


def _frame(text: str) -> str:
    # JSON-encoded so embedded newlines can't break SSE's line-based framing. A JSON string always
    # starts with a quote, so it can never be mistaken for the raw control frames below.
    return f"data: {json.dumps(text)}\n\n"


def _error_frame(message: str) -> str:
    # Raw (not JSON): distinguishable from model text, so a client never stores an error as an answer.
    return f"data: [ERROR: {message}]\n\n"


async def _close(models: list) -> None:
    for model in models:
        try:
            await model.aclose()
        except Exception:
            log.debug("Ignoring error while closing a model client", exc_info=True)


async def _first_text(events) -> str | None:
    async for chunk, _meta in events:
        text = visible_text(chunk)
        if text:
            return text
    return None


async def start_chat_stream(
    api_key: str,
    history: list[tuple[str, str]],
    message: str,
    settings: Settings,
    screenshot: Screenshot | None = None,
) -> AsyncIterator[str]:
    """Start answering and return an async iterator of SSE lines.

    The graph is run until the first visible text arrives *before* returning, so failures that
    happen up front (bad key, rate limit on every model, unreachable) raise ChatError and the
    route can answer with a real HTTP status instead of a 200 whose body is an error.
    """
    primary = make_model(settings.gemini_model, api_key, settings, max_retries=0)
    fallback = (
        make_model(settings.gemini_fallback_model, api_key, settings, max_retries=1)
        if settings.gemini_fallback_model
        else None
    )
    models = [m for m in (primary, fallback) if m is not None]

    log.info(
        f"Starting chat: model={settings.gemini_model}, "
        f"fallback={settings.gemini_fallback_model or 'none'}, history_turns={len(history)}, "
        f"screenshot={'yes' if screenshot else 'no'}"
    )
    graph = build_graph(primary, fallback)
    events = graph.astream(
        {"messages": to_messages(history, message, screenshot), "failed_over": False}, stream_mode="messages"
    )

    try:
        first = await _first_text(events)
    except Exception as exc:
        await _aclose(events)
        await _close(models)
        log.error(f"Chat failed before streaming: {type(exc).__name__}: {exc}", exc_info=True)
        raise translate(exc) from exc

    return _sse_lines(first, events, models)


async def _aclose(events) -> None:
    aclose = getattr(events, "aclose", None)
    if aclose is not None:
        try:
            await aclose()
        except Exception:
            log.debug("Ignoring error while closing the graph stream", exc_info=True)


async def _sse_lines(first: str | None, events, models: list) -> AsyncIterator[str]:
    sent = 0
    try:
        if first is None:
            log.warning("Model finished without any visible text")
            yield _error_frame("The model returned no answer. Try rephrasing your question.")
        else:
            yield _frame(first)
            sent = 1
            try:
                async for chunk, _meta in events:
                    text = visible_text(chunk)
                    if text:
                        sent += 1
                        yield _frame(text)
            except Exception as exc:
                # Mid-stream failure: the 200 status is already sent, so report in-band.
                log.error(f"Exception during stream: {type(exc).__name__}: {exc}", exc_info=True)
                yield _error_frame(translate(exc).detail)
        yield "data: [DONE]\n\n"
    finally:
        # No yields here: if the client disconnects the generator is closed, and a yield
        # in this block would raise. Cleanup only.
        await _aclose(events)
        await _close(models)
        log.info(f"Stream closed after {sent} text chunks")


__all__ = ["ChatError", "start_chat_stream"]
