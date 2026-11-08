"""
Main Window for Lingbao MK75 Linux Controller.
Clean, modern desktop layout with vector SVG navigation,
hero 75% interactive visualizer, and background daemon support.
"""

import os
from typing import Optional
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QStackedWidget,
    QFrame, QSystemTrayIcon, QMenu, QMessageBox, QScrollArea
)

from core.profile_manager import ProfileManager
from core.macro_engine import MacroEngine
from core.evdev_remapper import EvdevRemapper
from core.hid_controller import MK75HardwareController
from core.device_detector import MK75Detector, DeviceInfo

from ui.theme import GLOBAL_STYLESHEET
from ui.icons import get_icon
from ui.widgets.keyboard_visualizer import KeyboardVisualizer
from ui.widgets.key_config_panel import KeyConfigPanel
from ui.widgets.lighting_view import LightingView
from ui.widgets.macros_view import MacrosView
from ui.widgets.device_view import DeviceView
from ui.widgets.inspector_view import InspectorView

class MainWindow(QMainWindow):
    """Main desktop application window for Lingbao MK75."""

    def __init__(self, profile_manager: ProfileManager,
                 remapper: EvdevRemapper,
                 hid_controller: MK75HardwareController,
                 macro_engine: MacroEngine):
        super().__init__()
        self.profile_manager = profile_manager
        self.remapper = remapper
        self.hid = hid_controller
        self.macro_engine = macro_engine

        self.setWindowTitle("MK75")
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "mk75.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(get_icon("keyboard", normal_color="#6366F1", size=32))
        self.resize(1120, 740)
        self.setMinimumSize(960, 640)
        self.setStyleSheet(GLOBAL_STYLESHEET)

        self._build_ui()
        self._setup_system_tray()
        self._connect_signals()
        self._check_device_status()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._check_device_status)
        self.status_timer.start(10000)

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Header Bar
        header = QFrame()
        header.setObjectName("HeaderBar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 10, 18, 10)

        brand_box = QHBoxLayout()
        brand_box.setSpacing(10)
        title_label = QLabel("MK75")
        title_label.setStyleSheet("font-size: 15px; font-weight: 700; letter-spacing: 0.5px; color: #FFFFFF;")
        brand_box.addWidget(title_label)

        sub_label = QLabel("Tri-Mode 75%")
        sub_label.setStyleSheet("color: #6B7280; font-size: 11px; padding-top: 2px;")
        brand_box.addWidget(sub_label)
        header_layout.addLayout(brand_box)

        header_layout.addStretch()

        # Connection Status
        self.conn_pill = QLabel("Checking connection...")
        self.conn_pill.setObjectName("Badge")
        header_layout.addWidget(self.conn_pill)

        # Battery Status Pill
        self.battery_pill = QLabel("Battery --")
        self.battery_pill.setObjectName("Badge")
        self.battery_pill.hide()
        header_layout.addWidget(self.battery_pill)

        # Daemon Remapper Toggle Button
        self.daemon_btn = QPushButton("Remapper Active")
        self.daemon_btn.setIcon(get_icon("check", normal_color="#10B981", size=14))
        self.daemon_btn.setStyleSheet(
            "background-color: #162620; color: #10B981; border: 1px solid #1E4D38; font-size: 11px; padding: 4px 10px;"
        )
        self.daemon_btn.clicked.connect(self._toggle_remapper_daemon)
        header_layout.addWidget(self.daemon_btn)

        root_layout.addWidget(header)

        # 2. Main Body: Sidebar + Stacked Content
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left Sidebar with SVG Icons
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 12, 8, 12)
        sidebar_layout.setSpacing(4)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("SidebarList")
        self.nav_list.setIconSize(QSize(18, 18))

        nav_items = [
            ("Keymap & Knob", "keyboard", 0),
            ("Lighting", "lighting", 1),
            ("Macros", "macro", 2),
            ("Device Settings", "device", 3),
            ("Packet Inspector", "terminal", 4),
        ]

        for label, icon_name, idx in nav_items:
            item = QListWidgetItem(label)
            item.setIcon(get_icon(icon_name, size=18))
            item.setData(Qt.UserRole, idx)
            self.nav_list.addItem(item)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        sidebar_layout.addWidget(self.nav_list)
        sidebar_layout.addStretch()

        version_label = QLabel("v1.0.0 • Linux Native")
        version_label.setStyleSheet("color: #4B5563; font-size: 11px; padding: 6px 10px;")
        sidebar_layout.addWidget(version_label)

        body_layout.addWidget(sidebar)

        # Stacked Views Container
        self.stack = QStackedWidget()

        # Page 0: Keymap & Knob
        self.page_keymap = self._build_keymap_page()
        self.stack.addWidget(self.page_keymap)

        # Page 1: Lighting
        self.page_lighting = LightingView(self.profile_manager, self.hid)
        self.stack.addWidget(self.page_lighting)

        # Page 2: Macros (New human-friendly builder)
        self.page_macros = MacrosView(self.profile_manager, self.macro_engine)
        self.stack.addWidget(self.page_macros)

        # Page 3: Device & Profiles
        self.page_device = DeviceView(self.profile_manager, self.hid)
        self.stack.addWidget(self.page_device)

        # Page 4: Packet Inspector
        self.page_inspector = InspectorView(self.hid)
        self.stack.addWidget(self.page_inspector)

        body_layout.addWidget(self.stack, 1)
        root_layout.addWidget(body, 1)

        self.nav_list.setCurrentRow(0)

    def _build_keymap_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        self.visualizer = KeyboardVisualizer(self.profile_manager)
        layout.addWidget(self.visualizer)

        self.config_panel = KeyConfigPanel(self.profile_manager)
        layout.addWidget(self.config_panel)

        scroll.setWidget(container)
        return scroll

    def _connect_signals(self):
        self.visualizer.key_selected.connect(self.config_panel.set_key)
        self.config_panel.remap_changed.connect(self.visualizer.update)
        self.config_panel.remap_changed.connect(self.page_macros.visualizer.update)
        self.page_macros.macro_changed.connect(self.visualizer.update)
        self.page_macros.macro_changed.connect(lambda: self.config_panel.set_key(self.visualizer.selected_key_id if hasattr(self.visualizer, "selected_key_id") else None))
        self.remapper.add_key_listener(self._on_hardware_keypress)
        self.page_lighting.lighting_applied.connect(lambda _: self.visualizer.update())
        self.page_lighting.lighting_applied.connect(lambda _: self.page_macros.visualizer.update())

    def _on_nav_changed(self, row: int):
        if row >= 0:
            self.stack.setCurrentIndex(row)
            if row == 2 and hasattr(self, "page_macros"):
                self.page_macros.visualizer.update()

    def _on_hardware_keypress(self, key_id: str, value: int):
        self.visualizer.set_key_pressed(key_id, value > 0)
        if hasattr(self, "page_macros") and hasattr(self.page_macros, "visualizer"):
            self.page_macros.visualizer.set_key_pressed(key_id, value > 0)

    def _check_device_status(self):
        info = MK75Detector.scan()
        if info.detected:
            self.conn_pill.setText(f"{info.connection_type} • {info.vid:04X}:{info.pid:04X}")
            self.conn_pill.setStyleSheet("color: #10B981; background: #13261C; border: 1px solid #1E4D38;")

            # Query battery level over 2.4GHz wireless channel
            status = self.hid.query_device_status()
            if status and status.get("battery") is not None:
                pct = status["battery"]
                self.battery_pill.setText(f"{pct}% Battery")
                if pct > 20:
                    self.battery_pill.setStyleSheet("color: #10B981; background: #13261C; border: 1px solid #1E4D38;")
                else:
                    self.battery_pill.setStyleSheet("color: #EF4444; background: #2E151A; border: 1px solid #4D1A23;")
                self.battery_pill.show()
            else:
                self.battery_pill.hide()
        else:
            self.conn_pill.setText("Disconnected")
            self.conn_pill.setStyleSheet("color: #8A94A6; background: #1A1F2C; border: 1px solid #242A3B;")
            self.battery_pill.hide()

    def _toggle_remapper_daemon(self):
        if self.remapper.running:
            self.remapper.stop_remapper()
            self.daemon_btn.setText("Remapper Paused")
            self.daemon_btn.setIcon(get_icon("cross", normal_color="#F59E0B", size=14))
            self.daemon_btn.setStyleSheet("background-color: #2D2316; color: #F59E0B; border: 1px solid #573A1B; font-size: 11px;")
        else:
            started = self.remapper.start_remapper()
            if started:
                self.daemon_btn.setText("Remapper Active")
                self.daemon_btn.setIcon(get_icon("check", normal_color="#10B981", size=14))
                self.daemon_btn.setStyleSheet("background-color: #162620; color: #10B981; border: 1px solid #1E4D38; font-size: 11px;")
            else:
                QMessageBox.warning(
                    self, "Remapper Daemon Notice",
                    "Could not start the OS-level key remapper.\nCheck that your user has access to /dev/uinput and /dev/input/event*."
                )

    def _setup_system_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return

        self.tray = QSystemTrayIcon(self)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "mk75.png")
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))
        else:
            self.tray.setIcon(get_icon("keyboard", normal_color="#6366F1", size=24))
        self.tray.setToolTip("MK75")

        tray_menu = QMenu()
        show_action = QAction("Open MK75", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)

        hide_action = QAction("Hide Window", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit Application", self)
        quit_action.triggered.connect(self._force_quit)
        tray_menu.addAction(quit_action)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def closeEvent(self, event):
        if self.tray and self.tray.isVisible():
            self.hide()
            event.ignore()
        else:
            self._force_quit()

    def _force_quit(self):
        self.remapper.stop_remapper()
        self.hid.disconnect()
        if self.tray:
            self.tray.hide()
        self.close()
        import sys
        sys.exit(0)
