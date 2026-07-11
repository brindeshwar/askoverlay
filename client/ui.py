from auth import LoginWorker
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTextEdit, QSystemTrayIcon, QMenu, QDialog, QLabel
)

def build_window(icon_path):
    window = QWidget()
    window.setWindowTitle("AskOverlay")
    window.resize(400, 300)
    window.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    window.setWindowIcon(QIcon(icon_path))

    layout = QVBoxLayout()

    login_button = QPushButton("Login")
    login_button.setFixedSize(90, 24)

    close_button = QPushButton("✕")
    close_button.setFixedSize(24, 24)
    close_button.clicked.connect(window.hide)

    top_bar = QHBoxLayout()
    top_bar.addStretch()
    top_bar.addWidget(login_button)
    top_bar.addWidget(close_button)

    usage_label = QLabel("")
    usage_label.setStyleSheet("color: gray; font-size: 10px;")

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
    layout.addWidget(usage_label)
    layout.addWidget(response_area)
    layout.addLayout(input_layout)
    window.setLayout(layout)

    return window, response_area, input_field, send_button, login_button, usage_label


def build_tray_icon(app, window, icon_path):
    icon = QIcon(icon_path)
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

    tray_icon._menu = tray_menu
    tray_icon._open_action = open_action
    tray_icon._quit_action = quit_action

    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            window.show()
            window.activateWindow()

    tray_icon.activated.connect(on_tray_activated)
    tray_icon.show()

    return tray_icon

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