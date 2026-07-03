import sys
import logging
import keyring
from PySide6.QtWidgets import QInputDialog, QMessageBox, QLineEdit

log = logging.getLogger("askoverlay.client.auth")

SERVICE_NAME = "AskOverlay"
GEMINI_KEY_NAME = "gemini_api_key"

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

# Day 13: get_or_create_device_id() will be added here
# Day 11: Google login trigger will be added here