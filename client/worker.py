import json
import logging
import requests
from auth import BACKEND_URL
from screen import chat_payload
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

log = logging.getLogger("askoverlay.client.worker")

def _error_detail(response):
    """The backend's human-readable message for a non-200 reply (FastAPI puts it under "detail")."""
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = None
    if isinstance(detail, str):
        return detail
    return f"The server could not process the request (HTTP {response.status_code})."


class WorkerSignals(QObject):
    chunk_received = Signal(str)
    finished = Signal()
    error = Signal(str)
    quota_exceeded = Signal(str)

class StreamWorker(QRunnable):
    def __init__(self, message, history, auth_mode, credential, screenshot_b64=None):
        super().__init__()
        self.setAutoDelete(False)
        self.message = message
        self.screenshot_b64 = screenshot_b64  # for this message only; never logged
        self.auth_mode = auth_mode
        self.credential = credential
        self.history = history
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        headers = {}
        if self.auth_mode == "byok":
            headers["X-Gemini-Key"] = self.credential
        elif self.auth_mode == "device":
            headers["X-Device-Id"] = self.credential

        try:
            with requests.post(
                f"{BACKEND_URL}/chat",
                json=chat_payload(self.message, self.history, self.screenshot_b64),
                headers=headers,
                stream=True,
                timeout=(10, None)
            ) as response:
                log.debug(f"HTTP response status: {response.status_code}")

                if response.status_code == 429:
                    detail = response.json().get("detail", "Daily limit reached.")
                    log.info(f"Quota exceeded: {detail}")
                    self.signals.quota_exceeded.emit(detail)
                    return

                if response.status_code >= 400:
                    detail = _error_detail(response)
                    log.error(f"Backend error {response.status_code}: {detail}")
                    self.signals.error.emit(detail)
                    return

                for line in response.iter_lines():
                    if line:
                        decoded = line.decode("utf-8")
                        if decoded.startswith("data: "):
                            payload = decoded[len("data: "):]
                            if payload == "[DONE]":
                                log.debug("Received [DONE] sentinel")
                                break
                            elif payload.startswith("[ERROR: "):
                                # A raw control frame; model text is always JSON-quoted, so no collision.
                                message = payload[len("[ERROR: "):].rstrip("]")
                                log.error(f"Stream error frame: {message}")
                                self.signals.error.emit(message)
                                break
                            else:
                                chunk = json.loads(payload)
                                self.signals.chunk_received.emit(chunk)
        except Exception as e:
            log.error(f"StreamWorker error: {e}", exc_info=True)
            self.signals.error.emit(str(e))
        finally:
            log.info("StreamWorker finished")
            self.signals.finished.emit()


class QuotaSignals(QObject):
    result = Signal(str, object, object)  # mode, used, limit
    error = Signal(str)

class QuotaCheckWorker(QRunnable):
    def __init__(self, auth_mode, credential):
        super().__init__()
        self.setAutoDelete(False)
        self.auth_mode = auth_mode
        self.credential = credential
        self.signals = QuotaSignals()

    @Slot()
    def run(self):
        headers = {}
        if self.auth_mode == "device":
            headers["X-Device-Id"] = self.credential

        try:
            resp = requests.get(f"{BACKEND_URL}/quota/status", headers=headers, timeout=(10, 10))
            resp.raise_for_status()
            data = resp.json()
            self.signals.result.emit(data["mode"], data["used"], data["limit"])
        except Exception as e:
            log.debug(f"Quota status check failed: {e}")
            self.signals.error.emit(str(e))