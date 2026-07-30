from auth import LoginWorker
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton


def show_first_run_dialog():
    dialog = QDialog()
    dialog.setWindowTitle("Welcome to AskOverlay")
    dialog.setFixedSize(320, 160)

    layout = QVBoxLayout()
    status_label = QLabel("Get started:")
    layout.addWidget(status_label)

    try_button = QPushButton("Try for free (no signup)")
    login_button = QPushButton("Sign in with Google")
    layout.addWidget(try_button)
    layout.addWidget(login_button)
    dialog.setLayout(layout)

    result = {"choice": None}
    thread_pool = QThreadPool()

    def choose_try():
        result["choice"] = "try"
        dialog.accept()

    def start_login():
        try_button.setEnabled(False)
        login_button.setEnabled(False)
        status_label.setText("Opening browser — complete sign-in there...")

        worker = LoginWorker()
        worker.signals.success.connect(on_success)
        worker.signals.error.connect(on_error)
        thread_pool.start(worker)

    def on_success(email, name):
        result["choice"] = "login"
        status_label.setText(f"Signed in as {name}.")
        dialog.accept()

    def on_error(error_msg):
        status_label.setText(f"Sign-in failed: {error_msg}")
        try_button.setEnabled(True)
        login_button.setEnabled(True)

    try_button.clicked.connect(choose_try)
    login_button.clicked.connect(start_login)

    dialog.exec()
    return result["choice"]


def show_quota_dialog(auth_mode, detail_message):
    dialog = QDialog()
    dialog.setWindowTitle("Limit Reached")
    dialog.setFixedSize(320, 160)

    layout = QVBoxLayout()
    layout.addWidget(QLabel(detail_message))

    result = {"choice": None}

    def pick(value):
        result["choice"] = value
        dialog.accept()

    if auth_mode == "device":
        login_btn = QPushButton("Sign in with Google")
        login_btn.clicked.connect(lambda: pick("login"))
        layout.addWidget(login_btn)
    elif auth_mode == "session":
        upgrade_btn = QPushButton("Upgrade to Premium")
        upgrade_btn.clicked.connect(lambda: pick("upgrade"))
        layout.addWidget(upgrade_btn)

    byok_btn = QPushButton("Use your own Gemini API key")
    byok_btn.clicked.connect(lambda: pick("byok"))
    layout.addWidget(byok_btn)

    dismiss_btn = QPushButton("Maybe later")
    dismiss_btn.clicked.connect(lambda: pick(None))
    layout.addWidget(dismiss_btn)

    dialog.setLayout(layout)
    dialog.exec()
    return result["choice"]