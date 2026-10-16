from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath, QTextDocument
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QSystemTrayIcon, QMenu, QLabel, QFrame, QScrollArea, QCheckBox
)

ICON_SIZE = QSize(64, 64)
WINDOW_SIZE = QSize(400, 320)


def paint_rounded_shape(widget, radius, border_color="#FDD835", border_width=2, fill_color=None):
    def paintEvent(event):
        painter = QPainter(widget)
        painter.setRenderHint(QPainter.Antialiasing)

        inset = border_width / 2
        rect_w = widget.width() - border_width
        rect_h = widget.height() - border_width

        painter.setBrush(QBrush(fill_color) if fill_color else Qt.NoBrush)
        pen = QPen(QColor(border_color))
        pen.setWidth(border_width)
        painter.setPen(pen)

        painter.drawRoundedRect(inset, inset, rect_w, rect_h, radius, radius)
        painter.end()
    widget.paintEvent = paintEvent


def markdown_to_html(markdown_text):
    doc = QTextDocument()
    doc.setMarkdown(markdown_text)
    return doc.toHtml()


def build_icon(icon_path, on_click, on_drag):
    icon_widget = QWidget()
    icon_widget.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
    icon_widget.setFixedSize(ICON_SIZE)
    icon_widget.setAttribute(Qt.WA_TranslucentBackground)

    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel()
    label.setPixmap(QPixmap(icon_path).scaled(ICON_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    label.setAlignment(Qt.AlignCenter)
    layout.addWidget(label)
    icon_widget.setLayout(layout)

    def mousePressEvent(event):
        if event.button() == Qt.LeftButton:
            icon_widget._drag_pos = event.globalPosition().toPoint() - icon_widget.pos()
            icon_widget._dragged = False
            event.accept()

    def mouseMoveEvent(event):
        if event.buttons() == Qt.LeftButton and hasattr(icon_widget, '_drag_pos'):
            icon_widget._dragged = True
            old_pos = icon_widget.pos()
            new_pos = event.globalPosition().toPoint() - icon_widget._drag_pos
            icon_widget.move(new_pos)
            delta = new_pos - old_pos
            on_drag(delta)
            event.accept()

    def mouseReleaseEvent(event):
        if not getattr(icon_widget, '_dragged', False):
            on_click()

    icon_widget.mousePressEvent = mousePressEvent
    icon_widget.mouseMoveEvent = mouseMoveEvent
    icon_widget.mouseReleaseEvent = mouseReleaseEvent

    return icon_widget


def build_window(icon_path):
    window = QWidget()
    window.setWindowTitle("AskOverlay")
    window.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
    window.setWindowIcon(QIcon(icon_path))
    window.setAttribute(Qt.WA_TranslucentBackground)
    window.resize(WINDOW_SIZE)

    layout = QVBoxLayout()

    minimize_button = QPushButton("—")
    minimize_button.setFixedSize(24, 24)

    top_bar = QHBoxLayout()
    top_bar.addStretch()
    top_bar.addWidget(minimize_button)

    usage_label = QLabel("")
    usage_label.setStyleSheet("color: gray; font-size: 10px;")

    # ── Message list (replaces the old single QTextEdit) ────────────────────
    messages_container = QWidget()
    messages_container.setStyleSheet("background: transparent;")
    messages_layout = QVBoxLayout()
    messages_layout.addStretch()
    messages_container.setLayout(messages_layout)

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setWidget(messages_container)
    scroll_area.setFrameStyle(QFrame.NoFrame)
    scroll_area.setStyleSheet(
        "QScrollArea { background-color: rgba(30, 30, 30, 180); "
        "border: 1px solid #555; border-radius: 6px; }"
    )
    scroll_area.viewport().setStyleSheet("background: transparent;")

    def scroll_to_bottom():
        QTimer.singleShot(0, lambda: scroll_area.verticalScrollBar().setValue(
            scroll_area.verticalScrollBar().maximum()
        ))

    def _new_label(color):
        label = QLabel()
        label.setWordWrap(True)
        label.setTextFormat(Qt.PlainText)
        label.setStyleSheet(f"color: {color}; background: transparent; padding: 2px 6px;")
        messages_layout.insertWidget(messages_layout.count() - 1, label)
        return label

    def add_user_message(text):
        label = _new_label("#DDDDDD")
        label.setText(f"You: {text}")
        scroll_to_bottom()

    def add_system_message(text):
        label = _new_label("#999999")
        label.setText(f"[{text}]")
        scroll_to_bottom()

    class _AssistantBubble:
        def __init__(self):
            self.label = _new_label("#FFFFFF")
            self.buffer = ""
            self.label.setText("Assistant: ")
            scroll_to_bottom()

        def append(self, chunk):
            self.buffer += chunk
            self.label.setText("Assistant: " + self.buffer)
            scroll_to_bottom()

        def finalize(self):
            if self.buffer.strip():
                html = markdown_to_html(self.buffer)
                self.label.setTextFormat(Qt.RichText)
                self.label.setText("<b>Assistant:</b> " + html)
            scroll_to_bottom()

    def add_assistant_message():
        return _AssistantBubble()

    # ── Input row ─────────────────────────────────────────────────────────
    input_layout = QHBoxLayout()
    input_field = QLineEdit()
    input_field.setPlaceholderText("Ask something...")
    input_field.setStyleSheet(
        "QLineEdit { background: transparent; border: 1px solid gray; border-radius: 4px; padding: 4px; }"
    )
    send_button = QPushButton("Send")
    input_layout.addWidget(input_field)
    input_layout.addWidget(send_button)

    screen_checkbox = QCheckBox("Look at my screen")
    screen_checkbox.setToolTip("When on, a screenshot of your screen is sent with each question, so I can see what you see.")
    screen_checkbox.setStyleSheet("QCheckBox { color: gray; font-size: 11px; }")

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
    layout.addWidget(scroll_area)
    layout.addWidget(screen_checkbox)
    layout.addLayout(input_layout)
    window.setLayout(layout)

    paint_rounded_shape(window, radius=15, fill_color=QColor(30, 30, 30, 140))

    return (
        window, add_user_message, add_assistant_message, add_system_message,
        input_field, send_button, usage_label, minimize_button, screen_checkbox
    )


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