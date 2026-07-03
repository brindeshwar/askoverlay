import logging
import requests
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

log = logging.getLogger("askoverlay.client.worker")

class WorkerSignals(QObject):
    chunk_received = Signal(str)
    finished = Signal()
    error = Signal(str)

class StreamWorker(QRunnable):
    def __init__(self, message, api_key):
        super().__init__()
        self.message = message
        self.api_key = api_key
        self.signals = WorkerSignals()
        log.debug(f"StreamWorker created for message: {message[:50]}")

    @Slot()
    def run(self):
        log.info("StreamWorker started")
        try:
            with requests.post(
                "http://localhost:8000/chat",
                json={"message": self.message},
                headers={"X-Gemini-Key": self.api_key},
                stream=True,
                timeout=(10, None)
            ) as response:
                log.debug(f"HTTP response status: {response.status_code}")
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