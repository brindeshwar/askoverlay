import logging
import requests
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

log = logging.getLogger("askoverlay.client.worker")

class WorkerSignals(QObject):
    chunk_received = Signal(str)
    finished = Signal()
    error = Signal(str)
    quota_exceeded = Signal(str)

class StreamWorker(QRunnable):
    def __init__(self, message, auth_mode, credential):
        super().__init__()
        self.message = message
        self.auth_mode = auth_mode
        self.credential = credential
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        headers = {}
        if self.auth_mode == "byok":
            headers["X-Gemini-Key"] = self.credential
        elif self.auth_mode == "session":
            headers["X-Session-Token"] = self.credential
        elif self.auth_mode == "device":
            headers["X-Device-Id"] = self.credential

        try:
            with requests.post(
                "http://localhost:8000/chat",
                json={"message": self.message},
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

                for line in response.iter_lines():
                    if line:
                        decoded = line.decode("utf-8")
                        if decoded.startswith("data: "):
                            chunk = decoded[len("data: "):]
                            if chunk == "[DONE]":
                                log.debug("Received [DONE] sentinel")
                                break
                            self.signals.chunk_received.emit(chunk)
        except Exception as e:
            log.error(f"StreamWorker error: {e}", exc_info=True)
            self.signals.error.emit(str(e))
        finally:
            log.info("StreamWorker finished")
            self.signals.finished.emit()