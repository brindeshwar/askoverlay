from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel
import sys, requests
app = QApplication(sys.argv)
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