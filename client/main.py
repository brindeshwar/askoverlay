from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QInputDialog, QMessageBox, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import QThreadPool, QRunnable, Signal, QObject, Slot, Qt
from PySide6.QtGui import QTextCursor, QIcon, QAction
import sys, requests, keyring, logging, os

import ctypes
if sys.platform == "win32":
    myappid = "askoverlay.client.v1"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "assets", "icon.png")

# ── Logging setup ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),                  # terminal
        logging.FileHandler("askoverlay.log"),    # file
    ]
)
log = logging.getLogger("askoverlay.client")

# ── Constants ──────────────────────────────────────────────────────────────
SERVICE_NAME = "AskOverlay"
KEY_NAME = "gemini_api_key"

# ── Key management ─────────────────────────────────────────────────────────
def get_or_prompt_api_key():
    log.debug("Checking keyring for stored API key")
    api_key = keyring.get_password(SERVICE_NAME, KEY_NAME)
    if api_key is None:
        log.info("No API key found, prompting user")
        api_key, ok = QInputDialog.getText(
            None,
            "Enter Gemini API Key",
            "Paste your Gemini API key (it will be saved and encrypted on your system):",
            QLineEdit.Password
        )
        if ok and api_key:
            keyring.set_password(SERVICE_NAME, KEY_NAME, api_key)
            log.info("API key saved to keyring")
            QMessageBox.information(None, "Success", "API key saved successfully.")
        else:
            log.warning("User cancelled API key entry, exiting")
            QMessageBox.critical(None, "API Key Required", "AskOverlay needs a Gemini API key to function. The app will now close.")
            sys.exit(1)
    else:
        log.debug("API key loaded from keyring")
    return api_key

# ── Worker signals ─────────────────────────────────────────────────────────
class WorkerSignals(QObject):
    chunk_received = Signal(str)
    finished = Signal()
    error = Signal(str)

# ── Stream worker ──────────────────────────────────────────────────────────
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
                timeout=60
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

# ── App setup ──────────────────────────────────────────────────────────────
app = QApplication(sys.argv)
api_key = get_or_prompt_api_key()

window = QWidget()
window.setWindowTitle("AskOverlay")
window.resize(400, 300)
window.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
window.setWindowIcon(QIcon(ICON_PATH))

layout = QVBoxLayout()

close_button = QPushButton("✕")
close_button.setFixedSize(24, 24)
close_button.clicked.connect(window.hide)

top_bar = QHBoxLayout()
top_bar.addStretch()
top_bar.addWidget(close_button)

response_area = QTextEdit()
response_area.setReadOnly(True)
response_area.setPlaceholderText("Responses will appear here...")

input_layout = QHBoxLayout()
input_field = QLineEdit()
input_field.setPlaceholderText("Ask something...")
send_button = QPushButton("Send")
input_layout.addWidget(input_field)
input_layout.addWidget(send_button)

def mousePressEvent(event):
    if event.button() == Qt.LeftButton:
        window._drag_pos = event.globalPosition().toPoint() - window.pos()
        event.accept()

def mouseMoveEvent(event):
    if event.buttons() == Qt.LeftButton and hasattr(window, '_drag_pos'):
        window.move(event.globalPosition().toPoint() - window._drag_pos)
        event.accept()

window.mousePressEvent = mousePressEvent
window.mouseMoveEvent = mouseMoveEvent

layout.addLayout(top_bar)
layout.addWidget(response_area)
layout.addLayout(input_layout)
window.setLayout(layout)

# ── System tray ────────────────────────────────────────────────────────────
icon = QIcon(ICON_PATH)
if icon.isNull():
    log.error(f"Failed to load tray icon from {ICON_PATH}")
else:
    log.debug(f"Tray icon loaded from {ICON_PATH}")

tray_icon = QSystemTrayIcon(icon, app)

tray_icon.setToolTip("AskOverlay")

tray_menu = QMenu()

open_action = QAction("Open")
open_action.triggered.connect(window.show)
open_action.triggered.connect(window.activateWindow)
tray_menu.addAction(open_action)

quit_action = QAction("Quit")
quit_action.triggered.connect(app.quit)
tray_menu.addAction(quit_action)

tray_icon.setContextMenu(tray_menu)

def on_tray_activated(reason):
    if reason == QSystemTrayIcon.ActivationReason.Trigger:
        window.show()
        window.activateWindow()

tray_icon.activated.connect(on_tray_activated)
tray_icon.show()

# ── Slots ──────────────────────────────────────────────────────────────────
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