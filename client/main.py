import sys
import os
import ctypes
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QTextCursor

from auth import get_or_prompt_api_key
from worker import StreamWorker
from ui import build_window, build_tray_icon

if sys.platform == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("askoverlay.client.v1")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "assets", "icon.png")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("askoverlay.log"),
    ]
)
log = logging.getLogger("askoverlay.client")

app = QApplication(sys.argv)
api_key = get_or_prompt_api_key()

window, response_area, input_field, send_button = build_window(ICON_PATH)
tray_icon = build_tray_icon(app, window, ICON_PATH)

thread_pool = QThreadPool()
log.debug(f"QThreadPool max threads: {thread_pool.maxThreadCount()}")

def on_send():
    user_message = input_field.text()
    if not user_message.strip():
        return

    log.info(f"Sending message: {user_message[:50]}")
    response_area.append(f"You: {user_message}\n")
    response_area.append("Assistant: ")
    input_field.clear()
    send_button.setEnabled(False)

    worker = StreamWorker(user_message, api_key)
    worker.signals.chunk_received.connect(append_chunk)
    worker.signals.error.connect(on_error)
    worker.signals.finished.connect(on_finished)

    thread_pool.start(worker)

def append_chunk(chunk):
    response_area.moveCursor(QTextCursor.End)
    response_area.insertPlainText(chunk)

def on_error(error_msg):
    log.error(f"UI received error signal: {error_msg}")
    response_area.moveCursor(QTextCursor.End)
    response_area.insertPlainText(f"\n[Error: {error_msg}]")

def on_finished():
    log.info("Stream finished, re-enabling send button")
    response_area.append("\n")
    send_button.setEnabled(True)

send_button.clicked.connect(on_send)
input_field.returnPressed.connect(on_send)

window.show()
log.info("AskOverlay client started")
sys.exit(app.exec())