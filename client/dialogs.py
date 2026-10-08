from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton


def show_first_run_dialog():
    """Returns "try" (demo mode), "byok" (own key), or None if the dialog is closed."""
    dialog = QDialog()
    dialog.setWindowTitle("Welcome to AskOverlay")
    dialog.setFixedSize(320, 160)

    layout = QVBoxLayout()
    layout.addWidget(QLabel("Get started:"))

    try_button = QPushButton("Try the demo (10 free requests)")
    byok_button = QPushButton("Use my own Gemini API key")
    layout.addWidget(try_button)
    layout.addWidget(byok_button)
    dialog.setLayout(layout)

    result = {"choice": None}

    def pick(value):
        result["choice"] = value
        dialog.accept()

    try_button.clicked.connect(lambda: pick("try"))
    byok_button.clicked.connect(lambda: pick("byok"))

    dialog.exec()
    return result["choice"]


def show_quota_dialog(detail_message):
    """Returns "byok" if the user wants to add their own key, else None."""
    dialog = QDialog()
    dialog.setWindowTitle("Demo Limit Reached")
    dialog.setFixedSize(320, 160)

    layout = QVBoxLayout()
    label = QLabel(detail_message)
    label.setWordWrap(True)
    layout.addWidget(label)

    result = {"choice": None}

    def pick(value):
        result["choice"] = value
        dialog.accept()

    byok_btn = QPushButton("Use your own Gemini API key")
    byok_btn.clicked.connect(lambda: pick("byok"))
    layout.addWidget(byok_btn)

    dismiss_btn = QPushButton("Maybe later")
    dismiss_btn.clicked.connect(lambda: pick(None))
    layout.addWidget(dismiss_btn)

    dialog.setLayout(layout)
    dialog.exec()
    return result["choice"]
