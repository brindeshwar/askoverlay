from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTextEdit, QSystemTrayIcon, QMenu
)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt

def build_window(icon_path):
    window = QWidget()
    window.setWindowTitle("AskOverlay")
    window.resize(400, 300)
    window.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    window.setWindowIcon(QIcon(icon_path))

    layout = QVBoxLayout()

    close_button = QPushButton("✕")
    close_button.setFixedSize(24, 24)
    close_button.clicked.connect(window.hide)

    top_bar = QHBoxLayout()
    top_bar.addStretch()
    top_bar.addWidget(close_button)

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
    layout.addWidget(response_area)
    layout.addLayout(input_layout)
    window.setLayout(layout)

    login_button = QPushButton("Login")
    login_button.setFixedSize(50, 24)
    top_bar.addWidget(login_button)

    return window, response_area, input_field, send_button, login_button


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