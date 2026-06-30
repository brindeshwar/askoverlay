from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QInputDialog, QMessageBox
import sys, requests
import keyring

SERVICE_NAME = "AskOverlay"
KEY_NAME = "gemini_api_key"

def get_or_prompt_api_key():
    api_key = keyring.get_password(SERVICE_NAME, KEY_NAME)
    if api_key is None:
        api_key, ok = QInputDialog.getText(None, "Enter Gemini API Key", "Paste your Gemini API key (It will be saved on your system and encrypted):")
        if ok and api_key:
            keyring.set_password(SERVICE_NAME, KEY_NAME, api_key)
            QMessageBox.information(None, "Success", "API key saved successfully.")
        else:
            QMessageBox.critical(None, "API Key Required", "AskOverlay needs a Gemini API key to function. The app will now close.")
            sys.exit(1)
    return api_key

app = QApplication(sys.argv)

api_key = get_or_prompt_api_key()

window = QWidget()
window.setWindowTitle("AskOverlay")
window.resize(400, 200)

layout = QVBoxLayout()

input_field = QLineEdit()
input_field.setPlaceholderText("Ask something...")

send_button = QPushButton("Send")
response_label = QLabel("Response will appear here.")

layout.addWidget(input_field)
layout.addWidget(send_button)
layout.addWidget(response_label)

window.setLayout(layout)

def on_send():
    user_message = input_field.text()
    response = requests.post("http://localhost:8000/chat", json={"message": user_message})
    reply = response.json()["reply"]
    response_label.setText(reply)

send_button.clicked.connect(on_send)    

window.show()

sys.exit(app.exec())