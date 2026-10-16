"""Screen capture for the "Look at my screen" switch.

The pure helpers (sizing, request payload) have no Qt dependency so they can be tested in CI, where no desktop exists.
The capture itself needs Qt and a real screen; Qt is imported inside the functions that use it.

The screenshot is captured only when the user has the switch on, is sent with that one message, and is never written
to disk or to the log by the client.
"""
import base64
import logging
import sys

log = logging.getLogger("askoverlay.client.screen")

MAX_SIDE = 1280  # longest side after downsizing, in pixels
JPEG_QUALITIES = (80, 65, 50)  # tried in order until the image fits
MAX_ENCODED_BYTES = 1_200_000  # the server rejects more than 1,500,000; this leaves a margin
WDA_EXCLUDEFROMCAPTURE = 0x11  # Windows: hide a window from screen capture without hiding it from the user
MIN_BUILD_FOR_EXCLUDE = 19041  # Windows 10 version 2004; older builds would show a black rectangle instead


def fit_within(width: int, height: int, max_side: int = MAX_SIDE) -> tuple[int, int]:
    """The size to scale (width, height) to so the longest side is at most max_side. Never enlarges."""
    longest = max(width, height)
    if longest <= max_side:
        return width, height
    scale = max_side / longest
    return max(1, round(width * scale)), max(1, round(height * scale))


def chat_payload(message: str, history: list, screenshot_b64: str | None = None) -> dict:
    """The JSON body for POST /chat. The screenshot key is present only when there is a screenshot."""
    payload = {"message": message, "history": history}
    if screenshot_b64:
        payload["screenshot"] = screenshot_b64
    return payload


def can_exclude_from_capture() -> bool:
    """Whether this Windows version can hide our own window from a screen capture."""
    if sys.platform != "win32":
        return False
    return sys.getwindowsversion().build >= MIN_BUILD_FOR_EXCLUDE


def exclude_from_capture(window) -> bool:
    """Ask Windows to leave `window` out of screen captures. Returns True if it worked."""
    if not can_exclude_from_capture():
        return False
    import ctypes

    try:
        return bool(ctypes.windll.user32.SetWindowDisplayAffinity(int(window.winId()), WDA_EXCLUDEFROMCAPTURE))
    except Exception:
        log.warning("Could not exclude the chat window from screen capture", exc_info=True)
        return False


def _grab_jpeg(screen) -> bytes | None:
    """Grab `screen`, downsize it, and encode it as a JPEG that fits the size budget."""
    from PySide6.QtCore import QBuffer, QIODevice, Qt

    image = screen.grabWindow(0).toImage()
    if image.isNull():
        return None
    width, height = fit_within(image.width(), image.height())
    if (width, height) != (image.width(), image.height()):
        image = image.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    for quality in JPEG_QUALITIES:
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        if not image.save(buffer, "JPEG", quality):
            return None
        data = bytes(buffer.data())
        if len(data) <= MAX_ENCODED_BYTES:
            return data
    return None


def capture_screen_b64(window) -> str | None:
    """A base64 JPEG of the screen that holds `window`, without the window in it. None if capture failed.

    Preferred: Windows leaves the chat window out of the capture, so nothing flickers. Fallback: hide the window for a
    moment, grab, and show it again.
    """
    from PySide6.QtCore import QThread
    from PySide6.QtWidgets import QApplication

    screen = window.screen() or QApplication.primaryScreen()
    if screen is None:
        return None

    was_visible = window.isVisible()
    hidden = False
    try:
        if not (was_visible and exclude_from_capture(window)):
            if was_visible:
                window.hide()
                hidden = True
                QApplication.processEvents()
                QThread.msleep(150)  # let the desktop repaint where the window was
        data = _grab_jpeg(screen)
    except Exception:
        log.error("Screen capture failed", exc_info=True)
        return None
    finally:
        if hidden:
            window.show()
    return base64.b64encode(data).decode("ascii") if data else None
