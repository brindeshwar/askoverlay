import sys
import os
import ctypes
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool
from auth import (
    determine_auth_mode,
    get_or_create_device_id,
    get_or_prompt_api_key,
)
from ui import build_window, build_icon, build_tray_icon, WINDOW_SIZE, ICON_SIZE
from dialogs import show_first_run_dialog, show_quota_dialog
from worker import StreamWorker, QuotaCheckWorker

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
app.setQuitOnLastWindowClosed(False)

auth_mode, credential = determine_auth_mode()
current_interaction_id = None
current_assistant_bubble = None

if auth_mode is None:
    choice = show_first_run_dialog()
    if choice == "try":
        credential = get_or_create_device_id()
        auth_mode = "device"
    elif choice == "byok":
        credential = get_or_prompt_api_key()
        auth_mode = "byok"
    else:
        sys.exit(0)

window, add_user_message, add_assistant_message, add_system_message, input_field, send_button, usage_label, minimize_button = build_window(ICON_PATH)

def show_chat_window():
    icon_pos = icon_widget.pos()
    window.move(icon_pos.x() + ICON_SIZE.width(), icon_pos.y())
    window.show()
    window.activateWindow()

def hide_chat_window():
    window.hide()

def toggle_chat_window():
    if window.isVisible():
        hide_chat_window()
    else:
        show_chat_window()

def on_icon_drag(delta):
    if window.isVisible():
        window.move(window.pos() + delta)

icon_widget = build_icon(ICON_PATH, on_click=toggle_chat_window, on_drag=on_icon_drag)
minimize_button.clicked.connect(hide_chat_window)

tray_icon = build_tray_icon(app, window, ICON_PATH)

thread_pool = QThreadPool()
log.debug(f"QThreadPool max threads: {thread_pool.maxThreadCount()}")
log.info(f"Starting in auth mode: {auth_mode}")

# ── Worker reference tracking (prevents premature garbage collection) ───────
_active_workers = []

def _track(worker):
    _active_workers.append(worker)

def _untrack(worker):
    if worker in _active_workers:
        _active_workers.remove(worker)

# ── Slots ──────────────────────────────────────────────────────────────────
def on_send():
    global current_assistant_bubble
    user_message = input_field.text()
    if not user_message.strip():
        return

    log.info(f"Sending message: {user_message[:50]}")
    add_user_message(user_message)
    input_field.clear()
    send_button.setEnabled(False)

    current_assistant_bubble = add_assistant_message()

    worker = StreamWorker(user_message, auth_mode, credential, current_interaction_id)
    _track(worker)
    worker.signals.quota_exceeded.connect(on_quota_exceeded)
    worker.signals.chunk_received.connect(append_chunk)
    worker.signals.error.connect(on_error)
    worker.signals.finished.connect(on_finished)
    worker.signals.finished.connect(lambda: _untrack(worker))
    worker.signals.interaction_id_received.connect(on_interaction_id_received)

    thread_pool.start(worker)

def append_chunk(chunk):
    current_assistant_bubble.append(chunk)

def on_error(error_msg):
    log.error(f"UI received error signal: {error_msg}")
    add_system_message(f"Error: {error_msg}")

def on_quota_exceeded(detail_message):
    log.info(f"Quota exceeded: {detail_message}")
    send_button.setEnabled(True)
    choice = show_quota_dialog(detail_message)

    if choice == "byok":
        start_byok_setup()

def on_finished():
    log.info("Stream finished, re-enabling send button")
    current_assistant_bubble.finalize()
    send_button.setEnabled(True)
    refresh_usage_indicator()

def start_byok_setup():
    global auth_mode, credential, current_interaction_id
    api_key = get_or_prompt_api_key()
    auth_mode = "byok"
    credential = api_key
    current_interaction_id = None  # conversation ids belong to the key that created them
    add_system_message("Switched to your own Gemini API key. You now have unlimited usage.")
    refresh_usage_indicator()

def refresh_usage_indicator():
    if auth_mode == "byok":
        usage_label.setText("")
        return
    worker = QuotaCheckWorker(auth_mode, credential)
    _track(worker)
    worker.signals.result.connect(on_quota_status)
    worker.signals.result.connect(lambda *_: _untrack(worker))
    worker.signals.error.connect(lambda e: log.debug(f"Quota status check failed: {e}"))
    worker.signals.error.connect(lambda *_: _untrack(worker))
    thread_pool.start(worker)

def on_quota_status(mode, used, limit):
    if used is None or limit is None:
        usage_label.setText("")
    else:
        usage_label.setText(f"Demo: {used}/{limit} requests used")

def on_interaction_id_received(new_id):
    global current_interaction_id
    current_interaction_id = new_id
    log.debug(f"Session interaction ID updated: {new_id}")

send_button.clicked.connect(on_send)
input_field.returnPressed.connect(on_send)

icon_widget.show()
refresh_usage_indicator()
log.info("AskOverlay client started")
sys.exit(app.exec())