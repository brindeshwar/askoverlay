"""Classify LLM failures: which are worth a fallback, and what HTTP status/message the user gets.

Uses LangChain's provider-neutral exception types, so nothing here depends on Gemini SDK internals.
"""
import httpx
from langchain_core.exceptions import (
    ContextOverflowError,
    ModelAPIError,
    ModelAuthenticationError,
    ModelConnectionError,
    ModelInvalidRequestError,
    ModelNotFoundError,
    ModelPermissionDeniedError,
    ModelRateLimitError,
    ModelTimeoutError,
)


class ChatError(Exception):
    """A failure talking to the model, already translated into an HTTP status and a message safe to show users."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


_TIMEOUTS = (ModelTimeoutError, TimeoutError, httpx.TimeoutException)

# Worth trying the fallback model for: the same request may well succeed elsewhere.
# Bad keys / bad requests are deliberately absent - the fallback would fail identically.
_TRANSIENT = (ModelRateLimitError, ModelAPIError, ModelConnectionError, httpx.TransportError, *_TIMEOUTS)


def is_transient(exc: BaseException) -> bool:
    return isinstance(exc, _TRANSIENT)


def translate(exc: BaseException) -> ChatError:
    """Map any exception from the model call to a status and a safe message (never raw exception text)."""
    if isinstance(exc, ContextOverflowError):
        return ChatError(400, "This conversation is too long for the model. Start a new chat.")
    if isinstance(exc, ModelRateLimitError):
        # Reported as 503, never 429: the client reads 429 from this backend as "demo quota used up".
        return ChatError(503, "Gemini is rate-limiting requests right now. Try again in a moment.")
    if isinstance(exc, _TIMEOUTS):
        return ChatError(504, "Gemini took too long to respond. Try again.")
    if isinstance(exc, ModelNotFoundError):
        return ChatError(502, "The AI model is unavailable right now. Try again later.")
    if isinstance(exc, (ModelAuthenticationError, ModelPermissionDeniedError, ModelInvalidRequestError)):
        return ChatError(400, "Gemini rejected the request. Check your API key.")
    if isinstance(exc, ModelAPIError):
        return ChatError(502, "Gemini is temporarily unavailable. Try again shortly.")
    return ChatError(502, "Could not get an answer from Gemini. Try again shortly.")
