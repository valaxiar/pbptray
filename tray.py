#!/usr/bin/env python3
import sys
import os
import socket
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSystemTrayIcon, QMenu, QAction, QCheckBox
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QCoreApplication, QTimer, QSize

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setFixedSize(250, 150)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Window)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        self.checks = []

        self.add_checkbox(
            layout,
            "In ear detection",
            get_state_fn=lambda: get_setting_state("ohd"),
            on_cmd=lambda: set_setting("ohd", "true"),
            off_cmd=lambda: set_setting("ohd", "false")
        )
        self.add_checkbox(
            layout,
            "mono",
            get_state_fn=lambda: get_setting_state("mono"),
            on_cmd=lambda: set_setting("mono", "true"),
            off_cmd=lambda: set_setting("mono", "false")
        )

        self.setLayout(layout)

    def add_checkbox(self, layout, label, get_state_fn, on_cmd, off_cmd):
        box = CommandCheckbox(label, get_state_fn, on_cmd, off_cmd)
        layout.addWidget(box)
        self.checks.append(box)

class CommandCheckbox(QCheckBox):
    def __init__(self, label, get_state_fn, on_cmd, off_cmd):
        super().__init__(label)
        self.get_state_fn = get_state_fn
        self.on_cmd = on_cmd
        self.off_cmd = off_cmd

        # Set initial checked state from the function output (True/False)
        self.blockSignals(True)
        self.setChecked(self.is_on())
        self.blockSignals(False)

        # React to user changes
        self.stateChanged.connect(self._handle_toggle)

    def _handle_toggle(self, state):
        cmd = self.on_cmd if state else self.off_cmd
        print(f"[DEBUG] Running toggle command: {cmd}")
        if callable(cmd):
            cmd()
        else:
            subprocess.run(cmd, shell=True)

    def is_on(self):
        try:
            # get_state_fn must return boolean
            state = bool(self.get_state_fn())
            print(f"[DEBUG] Checkbox '{self.text()}' initial state: {state}")
            return state
        except Exception as e:
            print(f"[Checkbox] Failed to get state: {e}")
            return False

bt_addr = "5C:33:7B:6A:8A:2B"

# === Singleton Lock ===
sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
try:
    sock.bind('\0noise_control_tray_singleton')
except OSError:
    print("Tray already running.")
    sys.exit(0)

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

def get_setting_state(setting):
    """Returns True if setting is enabled, False otherwise."""
    cmd = ["pbpctrl", "-d", bt_addr, "get", setting]
    print(f"[DEBUG] Running get_setting_state command: {' '.join(cmd)}")
    try:
        result = subprocess.check_output(
            cmd,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip().lower()
        print(f"[DEBUG] get_setting_state output: {result}")
        return result in ("true", "1", "enabled", "on")
    except subprocess.CalledProcessError as e:
        print(f"[DEBUG] get_setting_state error: {e}")
        return False

def set_noise_control(mode):
    print(f"[pbptray] Switching noise control to: {mode}")
    subprocess.run(["pbpctrl", "-d", bt_addr, "set", "anc", mode])
    if main_window:
        main_window.update_state_label()

def set_setting(setting, val):
    print(f"[pbptray] Switching {setting} to: {val}")
    subprocess.run(["pbpctrl", "-d", bt_addr, "set", setting, val])
    if main_window:
        main_window.update_state_label()

# Dummy battery function
def get_battery_percent(which):
    return "85%" if which == "left" else "88%"

def safe_pixmap(path, size):
    if os.path.exists(path):
        return QPixmap(path).scaled(size, size, Qt.KeepAspectRatio)
    else:
        return QPixmap(size, size)  # Empty placeholder

# === Main Widget ===
class ControlWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Noise Control")
        self.setFixedSize(300, 300)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        # === Earbud Images and Battery ===
        buds_layout = QHBoxLayout()
        self.left_img = QLabel()
        self.left_img.setPixmap(safe_pixmap("left.png", 64))
        self.left_label = QLabel(get_battery_percent("left"))
        self.left_label.setAlignment(Qt.AlignCenter)

        self.right_img = QLabel()
        self.right_img.setPixmap(safe_pixmap("right.png", 64))
        self.right_label = QLabel(get_battery_percent("right"))
        self.right_label.setAlignment(Qt.AlignCenter)

        left_col = QVBoxLayout()
        left_col.addWidget(self.left_img)
        left_col.addWidget(self.left_label)

        right_col = QVBoxLayout()
        right_col.addWidget(self.right_img)
        right_col.addWidget(self.right_label)

        buds_layout.addLayout(left_col)
        buds_layout.addLayout(right_col)
        layout.addLayout(buds_layout)

        # === Mode Buttons ===
        button_layout = QHBoxLayout()

        self.btn_anc = QPushButton()
        self.btn_anc.setIcon(QIcon("anc.png"))
        self.btn_anc.setIconSize(QSize(48, 48))
        self.btn_anc.clicked.connect(lambda: set_noise_control("active"))

        self.btn_trans = QPushButton()
        self.btn_trans.setIcon(QIcon("transparency.png"))
        self.btn_trans.setIconSize(QSize(48, 48))
        self.btn_trans.clicked.connect(lambda: set_noise_control("aware"))

        self.btn_off = QPushButton()
        self.btn_off.setIcon(QIcon("off.png"))
        self.btn_off.setIconSize(QSize(48, 48))
        self.btn_off.clicked.connect(lambda: set_noise_control("off"))

        button_layout.addWidget(self.btn_anc)
        button_layout.addWidget(self.btn_trans)
        button_layout.addWidget(self.btn_off)
        layout.addLayout(button_layout)

        # === ANC State Label ===
        self.state_label = QLabel()
        self.state_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.state_label)

        # === Settings Button ===
        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(QIcon("settings.png"))
        self.settings_btn.setIconSize(QSize(24, 24))
        self.settings_btn.setFixedSize(32, 32)
        self.settings_btn.setFlat(True)
        self.settings_btn.setStyleSheet("border: none;")
        self.settings_btn.clicked.connect(self.open_settings)

        settings_layout = QHBoxLayout()
        settings_layout.addStretch()
        settings_layout.addWidget(self.settings_btn)

        layout.addLayout(settings_layout)

        self.setLayout(layout)
        self.update_state_label()

    def update_state_label(self):
        state = get_noise_control_state()
        self.state_label.setText(f"Noise Control: {state.capitalize()}")
        tray.setToolTip(f"Noise Control: {state.capitalize()}")

    def open_settings(self):
        self.settings_window = SettingsWindow()
        self.settings_window.show()

# === Tray Setup ===
def toggle_window():
    if main_window.isVisible():
        main_window.hide()
    else:
        main_window.show()

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

tray = QSystemTrayIcon(QIcon.fromTheme("audio-headphones"))
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

# === Optional Refresh Timer ===
refresh_timer = QTimer()
refresh_timer.timeout.connect(main_window.update_state_label)
refresh_timer.start(5000)

sys.exit(app.exec_())
