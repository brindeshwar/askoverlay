import sys
import logging
import keyring
import http.server
import threading
import webbrowser
import uuid
import requests as req
from PySide6.QtWidgets import QInputDialog, QMessageBox, QLineEdit
from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from urllib.parse import urlparse, parse_qs


log = logging.getLogger("askoverlay.client.auth")

SERVICE_NAME = "AskOverlay"
GEMINI_KEY_NAME = "gemini_api_key"
SESSION_TOKEN_KEY_NAME = "session_token"
BACKEND_URL = "http://localhost:8000"
DEVICE_ID_KEY_NAME = "device_id"

def get_or_prompt_api_key():
    log.debug("Checking keyring for stored API key")
    api_key = keyring.get_password(SERVICE_NAME, GEMINI_KEY_NAME)
    if api_key is None:
        log.info("No API key found, prompting user")
        api_key, ok = QInputDialog.getText(
            None,
            "Enter Gemini API Key",
            "Paste your Gemini API key (it will be saved and encrypted on your system):",
            QLineEdit.Password
        )
        if ok and api_key:
            keyring.set_password(SERVICE_NAME, GEMINI_KEY_NAME, api_key)
            log.info("API key saved to keyring")
            QMessageBox.information(None, "Success", "API key saved successfully.")
        else:
            log.warning("User cancelled API key entry, exiting")
            QMessageBox.critical(None, "API Key Required", "AskOverlay needs a Gemini API key to function. The app will now close.")
            sys.exit(1)
    else:
        log.debug("API key loaded from keyring")
    return api_key

def get_or_create_device_id():
    device_id = keyring.get_password(SERVICE_NAME, DEVICE_ID_KEY_NAME)
    if device_id is None:
        device_id = str(uuid.uuid4())
        keyring.set_password(SERVICE_NAME, DEVICE_ID_KEY_NAME, device_id)
        log.info("Generated new device ID")
    else:
        log.debug("Loaded existing device ID from keyring")
    return device_id

class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        self.server.auth_code = query.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h2>Login complete. You can close this window.</h2></body></html>")

    def log_message(self, format, *args):
        pass  # suppress default request logging clutter


class LoginSignals(QObject):
    success = Signal(str, str)   # email, name
    error = Signal(str)


class LoginWorker(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = LoginSignals()

    @Slot()
    def run(self):
        try:
            server = http.server.HTTPServer(("127.0.0.1", 0), _CallbackHandler)
            port = server.server_port
            redirect_uri = f"http://127.0.0.1:{port}/callback"

            resp = req.get(f"{BACKEND_URL}/auth/google/login", params={"redirect_uri": redirect_uri})
            resp.raise_for_status()
            login_url = resp.json()["login_url"]

            webbrowser.open(login_url)

            server.timeout = 120
            server.handle_request()  # blocks until one request arrives, or times out

            code = getattr(server, "auth_code", None)
            if not code:
                self.signals.error.emit("Login timed out or was cancelled.")
                return

            exchange_resp = req.post(f"{BACKEND_URL}/auth/google/callback", json={
                "code": code,
                "redirect_uri": redirect_uri,
            })
            exchange_resp.raise_for_status()
            data = exchange_resp.json()

            keyring.set_password(SERVICE_NAME, SESSION_TOKEN_KEY_NAME, data["session_token"])
            self.signals.success.emit(data.get("email", ""), data.get("name", ""))

        except Exception as e:
            self.signals.error.emit(str(e))

class CheckoutSignals(QObject):
    success = Signal(str)  # approve_url
    error = Signal(str)


class CheckoutWorker(QRunnable):
    def __init__(self, session_token):
        super().__init__()
        self.session_token = session_token
        self.signals = CheckoutSignals()

    @Slot()
    def run(self):
        try:
            resp = req.post(f"{BACKEND_URL}/billing/checkout", headers={"X-Session-Token": self.session_token})
            resp.raise_for_status()
            approve_url = resp.json()["approve_url"]
            self.signals.success.emit(approve_url)
        except Exception as e:
            self.signals.error.emit(str(e))

def determine_auth_mode():
    """
    Returns a tuple: (mode, credential)
    mode is one of: "byok", "session", "device"
    credential is the corresponding key/token/id string
    """
    gemini_key = keyring.get_password(SERVICE_NAME, GEMINI_KEY_NAME)
    if gemini_key:
        log.info("Startup mode: BYOK")
        return "byok", gemini_key

    session_token = keyring.get_password(SERVICE_NAME, SESSION_TOKEN_KEY_NAME)
    if session_token:
        log.info("Startup mode: logged-in session")
        return "session", session_token

    device_id = keyring.get_password(SERVICE_NAME, DEVICE_ID_KEY_NAME)
    if device_id:
        log.info("Startup mode: anonymous device")
        return "device", device_id

    return None, None