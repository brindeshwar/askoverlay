"""A logging filter that removes embedded images from log output.

Screenshots must never reach the logs. The code does not log them on purpose; this filter is the second line of defence
for the case where a library puts a request into an error message or a traceback.
"""
import logging
import re

# A data URL, or any long unbroken base64 run (a raw screenshot is hundreds of thousands of characters).
_DATA_URL = re.compile(r"data:image/[a-zA-Z.+-]+;base64,[A-Za-z0-9+/=]+")
_LONG_BASE64 = re.compile(r"[A-Za-z0-9+/=]{400,}")

REDACTED = "[image removed from log]"


def redact(text: str) -> str:
    return _LONG_BASE64.sub(REDACTED, _DATA_URL.sub(REDACTED, text))


class RedactImagesFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = None
        if record.exc_info:
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
            record.exc_info = None
        elif record.exc_text:
            record.exc_text = redact(record.exc_text)
        return True


def install(handler_target: logging.Logger | None = None) -> None:
    """Attach the filter to every handler of the root logger (filters on a logger do not cover child loggers)."""
    logger = handler_target or logging.getLogger()
    for handler in logger.handlers:
        if not any(isinstance(f, RedactImagesFilter) for f in handler.filters):
            handler.addFilter(RedactImagesFilter())
