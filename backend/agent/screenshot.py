"""A screenshot sent with a chat request: validation and the data-URL form the model needs.

The client sends the image base64-encoded in the JSON body. Nothing here stores it, and it is never logged
(see redaction.py for the log filter that backs that rule up).
"""
import base64
import binascii
from dataclasses import dataclass

MAX_SCREENSHOT_BYTES = 1_500_000  # decoded size; the client downsizes to about 200 to 500 KB
MAX_SCREENSHOT_B64_CHARS = MAX_SCREENSHOT_BYTES * 4 // 3 + 8  # the longest base64 text that can decode to the limit

_MAGIC = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
}


@dataclass(frozen=True)
class Screenshot:
    mime: str
    data: str  # base64 text, as received

    @property
    def data_url(self) -> str:
        return f"data:{self.mime};base64,{self.data}"


def parse_screenshot(encoded: str) -> Screenshot:
    """Check that `encoded` is base64 for a JPEG or PNG within the size limit. Raises ValueError otherwise.

    The error messages never contain the value: a validation error is returned to the caller and may be logged.
    """
    if not encoded:
        raise ValueError("screenshot is empty")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("screenshot is not valid base64") from None
    if len(raw) > MAX_SCREENSHOT_BYTES:
        raise ValueError(f"screenshot is too large ({len(raw)} bytes, limit {MAX_SCREENSHOT_BYTES})")
    for mime, magic in _MAGIC.items():
        if raw.startswith(magic):
            return Screenshot(mime=mime, data=encoded)
    raise ValueError("screenshot must be a JPEG or PNG image")
