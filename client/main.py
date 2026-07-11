import sys
import os
import ctypes
import logging
import webbrowser
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QTextCursor
from auth import (
    determine_auth_mode,
    get_or_create_device_id,
    get_or_prompt_api_key,
    LoginWorker,
    CheckoutWorker,
    SERVICE_NAME,
    SESSION_TOKEN_KEY_NAME,
)
from ui import build_window, build_tray_icon, show_first_run_dialog, show_quota_dialog
from worker import StreamWorker
import keyring

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

# ── Determine how this session authenticates ────────────────────────────────
auth_mode, credential = determine_auth_mode()

if auth_mode is None:
    choice = show_first_run_dialog()
    if choice == "try":
        credential = get_or_create_device_id()
        auth_mode = "device"
    elif choice == "login":
        session_token = keyring.get_password("AskOverlay", "session_token")
        auth_mode = "session"
        credential = session_token
    else:
        sys.exit(0)

window, response_area, input_field, send_button, login_button = build_window(ICON_PATH)
if auth_mode == "session":
    login_button.setText("✓ Signed in")
    login_button.setEnabled(False)
tray_icon = build_tray_icon(app, window, ICON_PATH)

thread_pool = QThreadPool()
log.debug(f"QThreadPool max threads: {thread_pool.maxThreadCount()}")
log.info(f"Starting in auth mode: {auth_mode}")

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

    worker = StreamWorker(user_message, auth_mode, credential)
    worker.signals.quota_exceeded.connect(on_quota_exceeded)
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

def on_quota_exceeded(detail_message):
    log.info(f"Quota exceeded: {detail_message}")
    send_button.setEnabled(True)
    choice = show_quota_dialog(auth_mode, detail_message)

    if choice == "login":
        on_login()
    elif choice == "upgrade":
        start_upgrade()
    elif choice == "byok":
        start_byok_setup()

def on_finished():
    log.info("Stream finished, re-enabling send button")
    response_area.append("\n")
    send_button.setEnabled(True)

def on_login():
    login_button.setEnabled(False)
    login_button.setText("Logging in...")
    worker = LoginWorker()
    worker.signals.success.connect(on_login_success)
    worker.signals.error.connect(on_login_error)
    thread_pool.start(worker)

def on_login_success(email, name):
    global auth_mode, credential
    log.info(f"Login successful: {email}")
    session_token = keyring.get_password("AskOverlay", "session_token")
    auth_mode = "session"
    credential = session_token
    login_button.setText(f"✓ {name.split()[0]}")
    login_button.setEnabled(False)

def on_login_error(error_msg):
    log.error(f"Login failed: {error_msg}")
    login_button.setText("Login")
    login_button.setEnabled(True)
    response_area.append(f"\n[Login error: {error_msg}]\n")

def start_upgrade():
    if auth_mode != "session":
        response_area.append("\n[Upgrade requires signing in first.]\n")
        return
    worker = CheckoutWorker(credential)
    worker.signals.success.connect(on_checkout_ready)
    worker.signals.error.connect(on_checkout_error)
    thread_pool.start(worker)

def on_checkout_ready(approve_url):
    webbrowser.open(approve_url)
    response_area.append("\n[Complete payment in your browser. Once done, you'll be Premium — just send another message.]\n")

def on_checkout_error(error_msg):
    log.error(f"Checkout failed: {error_msg}")
    response_area.append(f"\n[Upgrade error: {error_msg}]\n")

def start_byok_setup():
    global auth_mode, credential
    api_key = get_or_prompt_api_key()
    auth_mode = "byok"
    credential = api_key
    response_area.append("\n[Switched to your own Gemini API key. You now have unlimited usage.]\n")

login_button.clicked.connect(on_login)
send_button.clicked.connect(on_send)
input_field.returnPressed.connect(on_send)

window.show()
log.info("AskOverlay client started")
sys.exit(app.exec())