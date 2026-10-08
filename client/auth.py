import sys
import logging
import keyring
import uuid
from PySide6.QtWidgets import QInputDialog, QMessageBox, QLineEdit


log = logging.getLogger("askoverlay.client.auth")

SERVICE_NAME = "AskOverlay"
GEMINI_KEY_NAME = "gemini_api_key"
BACKEND_URL = "http://135.235.216.131:8000"
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

def determine_auth_mode():
    """
    Returns a tuple: (mode, credential)
    mode is one of: "byok", "device"
    credential is the corresponding key/id string
    """
    gemini_key = keyring.get_password(SERVICE_NAME, GEMINI_KEY_NAME)
    if gemini_key:
        log.info("Startup mode: BYOK")
        return "byok", gemini_key

    device_id = keyring.get_password(SERVICE_NAME, DEVICE_ID_KEY_NAME)
    if device_id:
        log.info("Startup mode: demo (device)")
        return "device", device_id

    return None, None
