#!/usr/bin/env python3
import sys
import os
import socket
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QCoreApplication, QTimer, QSize

INSTALL_DIR = os.path.expanduser("~/.local/share/pbptray")
bt_addr_path = os.path.join(INSTALL_DIR, "bt_addr")
try:
    with open(bt_addr_path, "r") as f:
        bt_addr = f.read().strip()
except FileNotFoundError:
    print(f"Bluetooth address file not found: {bt_addr_path}")
    bt_addr = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
try:
    sock.bind('\0noise_control_tray_singleton')
except OSError:
    print("Tray already running.")
    sys.exit(0)

def is_connected():
    if not bt_addr:
        return False
    try:
        output = subprocess.check_output(
            ["bluetoothctl", "info", bt_addr],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return "Connected: yes" in output
    except subprocess.CalledProcessError:
        return False

def get_noise_control_state():
    try:
        result = subprocess.check_output(
            ["pbpctrl", "-d", bt_addr, "get", "anc"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        return result if result else "unknown"
    except subprocess.CalledProcessError:
        return "error"

def set_noise_control(mode):
    print(f"[Tray] Switching noise control to: {mode}")
    subprocess.run(["pbpctrl", "-d", bt_addr, "set", "anc", mode])
    if main_window:
        main_window.update_state_label()

def get_battery_percent(which):
    try:
        output = subprocess.check_output(
            ["pbpctrl", "-d", bt_addr, "show", "battery"],
            stderr=subprocess.DEVNULL,
            text=True
        )
        for line in output.splitlines():
            if which in line.lower():
                percent = line.split(":")[1].split("%")[0].strip()
                return f"{percent}%"
    except Exception as e:
        print(f"Battery error: {e}")
    return "?"

def safe_pixmap(path, size):
    full_path = os.path.join(SCRIPT_DIR, path)
    if os.path.exists(full_path):
        return QPixmap(full_path).scaled(size, size, Qt.KeepAspectRatio)
    else:
        return QPixmap(size, size)

class ControlWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Noise Control")
        self.setFixedSize(300, 310)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        layout.addSpacing(5)

        buds_layout = QHBoxLayout()
        buds_layout.setContentsMargins(20, 0, 20, 0)
        buds_layout.setSpacing(40)

        self.left_img = QLabel()
        self.left_img.setPixmap(safe_pixmap("images/left.png", 64))
        self.left_label = QLabel("?")
        self.left_label.setAlignment(Qt.AlignCenter)

        self.right_img = QLabel()
        self.right_img.setPixmap(safe_pixmap("images/right.png", 64))
        self.right_label = QLabel("?")
        self.right_label.setAlignment(Qt.AlignCenter)

        left_col = QVBoxLayout()
        left_col.setAlignment(Qt.AlignHCenter)
        left_col.addWidget(self.left_img)
        left_col.addWidget(self.left_label)

        right_col = QVBoxLayout()
        right_col.setAlignment(Qt.AlignHCenter)
        right_col.addWidget(self.right_img)
        right_col.addWidget(self.right_label)

        buds_layout.addLayout(left_col)
        buds_layout.addLayout(right_col)
        layout.addLayout(buds_layout)

        layout.addSpacing(5)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.buttons = {
            "active": QPushButton(),
            "aware": QPushButton(),
            "off": QPushButton(),
        }

        self.buttons["active"].setIcon(QIcon(os.path.join(SCRIPT_DIR, "images/anc.png")))
        self.buttons["aware"].setIcon(QIcon(os.path.join(SCRIPT_DIR, "images/transparency.png")))
        self.buttons["off"].setIcon(QIcon(os.path.join(SCRIPT_DIR, "images/off.png")))

        for mode, btn in self.buttons.items():
            btn.setIconSize(QSize(48, 48))
            btn.setFixedSize(60, 60)
            btn.clicked.connect(lambda _, m=mode: set_noise_control(m))
            button_layout.addWidget(btn)

        layout.addLayout(button_layout)

        self.state_label = QLabel("Device not connected")
        self.state_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.state_label)

        self.setLayout(layout)
        self.update_state_label()

    def update_state_label(self):
        if not is_connected():
            self.state_label.setText("Device not connected")
            tray.setToolTip("Device not connected")
            for btn in self.buttons.values():
                btn.setEnabled(False)
            self.left_label.setText("?")
            self.right_label.setText("?")
            return

        for btn in self.buttons.values():
            btn.setEnabled(True)

        state = get_noise_control_state()
        self.state_label.setText(f"Noise Control: {state.capitalize()}")
        tray.setToolTip(f"Noise Control: {state.capitalize()}")

        for btn in self.buttons.values():
            btn.setStyleSheet("")
        if state in self.buttons:
            self.buttons[state].setStyleSheet(
                "border: 2px solid #4CAF50; border-radius: 6px;"
            )

        self.left_label.setText(get_battery_percent("left"))
        self.right_label.setText(get_battery_percent("right"))

def toggle_window():
    if main_window.isVisible():
        main_window.hide()
    else:
        main_window.show()

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

icon = QIcon.fromTheme("audio-headphones")
if icon.isNull():
    icon_path = os.path.join(SCRIPT_DIR, "images", "headphones.png")
    icon = QIcon(icon_path)

tray = QSystemTrayIcon(icon)
tray_menu = QMenu()
toggle_action = QAction("Toggle Window")
toggle_action.triggered.connect(toggle_window)
quit_action = QAction("Quit")
quit_action.triggered.connect(QCoreApplication.quit)
tray_menu.addAction(toggle_action)
tray_menu.addSeparator()
tray_menu.addAction(quit_action)
tray.setContextMenu(tray_menu)
tray.activated.connect(lambda reason: reason == QSystemTrayIcon.Trigger and toggle_window())
tray.show()

main_window = ControlWindow()

refresh_timer = QTimer()
refresh_timer.timeout.connect(main_window.update_state_label)
refresh_timer.start(5000)

sys.exit(app.exec_())
