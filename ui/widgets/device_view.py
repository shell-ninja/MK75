"""
Device & Profiles Management View for Lingbao MK75.
Shows hardware connection status, live udev permission diagnostics, polling rate,
and JSON profile import / export.
"""

import os
import shutil
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QFrame, QFileDialog, QMessageBox,
    QProgressBar, QListView
)

from core.device_detector import MK75Detector, DeviceInfo
from core.hid_controller import MK75HardwareController, POLLING_RATES
from ui.icons import get_icon
from ui.theme import (
    BG_CARD, BORDER_COLOR, ACCENT_PRIMARY, ACCENT_SKY,
    ACCENT_EMERALD, ACCENT_ROSE, ACCENT_AMBER, TEXT_PRIMARY, TEXT_MUTED
)

class DeviceView(QWidget):
    """View to inspect hardware status, check udev permissions, and handle profiles."""

    def __init__(self, profile_manager, hid_controller: MK75HardwareController, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.hid = hid_controller
        self.device_info = DeviceInfo()

        self._build_ui()
        self.refresh_status()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Title
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Device Settings")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Hardware status, kernel permissions, USB polling rate, and profile management.")
        subtitle.setObjectName("SubtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        main_layout.addLayout(title_box)

        # 1. Device Info Card
        dev_card = QFrame()
        dev_card.setObjectName("Card")
        dev_layout = QVBoxLayout(dev_card)
        dev_layout.setContentsMargins(20, 18, 20, 18)
        dev_layout.setSpacing(12)

        dev_header = QHBoxLayout()
        dev_title = QLabel("Hardware Connection")
        dev_title.setStyleSheet("font-size: 14px; font-weight: 600;")
        dev_header.addWidget(dev_title)

        self.conn_badge = QLabel("Checking...")
        self.conn_badge.setObjectName("Badge")
        dev_header.addWidget(self.conn_badge)
        dev_header.addStretch()

        self.refresh_btn = QPushButton("Rescan Hardware")
        self.refresh_btn.setIcon(get_icon("refresh", size=14))
        self.refresh_btn.clicked.connect(self.refresh_status)
        dev_header.addWidget(self.refresh_btn)

        dev_layout.addLayout(dev_header)

        # Grid of device details
        self.grid = QGridLayout()
        self.grid.setSpacing(10)

        self.lbl_device_name = QLabel("Detecting...")
        self.lbl_vid_pid = QLabel("N/A")
        self.lbl_mode = QLabel("N/A")
        self.lbl_battery = QLabel("Querying...")
        self.lbl_hidraw = QLabel("N/A")
        self.lbl_events = QLabel("N/A")

        self.grid.addWidget(QLabel("Device:"), 0, 0)
        self.grid.addWidget(self.lbl_device_name, 0, 1)
        self.grid.addWidget(QLabel("USB VID:PID:"), 0, 2)
        self.grid.addWidget(self.lbl_vid_pid, 0, 3)

        self.grid.addWidget(QLabel("Connection Mode:"), 1, 0)
        self.grid.addWidget(self.lbl_mode, 1, 1)
        self.grid.addWidget(QLabel("Battery Level:"), 1, 2)
        self.grid.addWidget(self.lbl_battery, 1, 3)

        self.grid.addWidget(QLabel("Primary HID:"), 2, 0)
        self.grid.addWidget(self.lbl_hidraw, 2, 1)
        self.grid.addWidget(QLabel("Event Nodes:"), 2, 2)
        self.grid.addWidget(self.lbl_events, 2, 3)

        dev_layout.addLayout(self.grid)
        main_layout.addWidget(dev_card)

        # 2. Battery & Wireless Power Telemetry Card
        batt_card = QFrame()
        batt_card.setObjectName("Card")
        batt_layout = QVBoxLayout(batt_card)
        batt_layout.setContentsMargins(20, 18, 20, 18)
        batt_layout.setSpacing(12)

        batt_header = QHBoxLayout()
        batt_title = QLabel("Battery & Wireless Power Telemetry")
        batt_title.setStyleSheet("font-size: 14px; font-weight: 600;")
        batt_header.addWidget(batt_title)

        self.batt_badge = QLabel("Querying...")
        self.batt_badge.setObjectName("Badge")
        batt_header.addWidget(self.batt_badge)
        batt_header.addStretch()

        self.batt_query_btn = QPushButton("Query Battery Now")
        self.batt_query_btn.setIcon(get_icon("battery", size=14))
        self.batt_query_btn.clicked.connect(self._query_live_battery)
        batt_header.addWidget(self.batt_query_btn)
        batt_layout.addLayout(batt_header)

        # Gauge & Bar
        bar_box = QVBoxLayout()
        bar_box.setSpacing(6)

        pct_row = QHBoxLayout()
        self.lbl_batt_pct = QLabel("--%")
        self.lbl_batt_pct.setStyleSheet("font-size: 26px; font-weight: 700; color: #10B981;")
        pct_row.addWidget(self.lbl_batt_pct)

        self.lbl_batt_state = QLabel("Detecting power status...")
        self.lbl_batt_state.setStyleSheet("color: #9CA3AF; font-size: 12px; padding-left: 8px;")
        pct_row.addWidget(self.lbl_batt_state)
        pct_row.addStretch()
        bar_box.addLayout(pct_row)

        self.batt_progress = QProgressBar()
        self.batt_progress.setRange(0, 100)
        self.batt_progress.setValue(0)
        self.batt_progress.setTextVisible(False)
        self.batt_progress.setFixedHeight(8)
        self.batt_progress.setStyleSheet("""
            QProgressBar {
                background-color: #171A24;
                border: 1px solid #1E2330;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #10B981;
                border-radius: 3px;
            }
        """)
        bar_box.addWidget(self.batt_progress)
        batt_layout.addLayout(bar_box)

        # Telemetry detail
        self.lbl_raw_telemetry = QLabel("Protocol: Compx Report ID 0x13 • Command 0x4A telemetry channel")
        self.lbl_raw_telemetry.setStyleSheet("color: #6B7280; font-size: 11px; font-family: monospace;")
        batt_layout.addWidget(self.lbl_raw_telemetry)

        main_layout.addWidget(batt_card)

        # 3. Linux udev & Kernel Permissions Card
        perm_card = QFrame()
        perm_card.setObjectName("Card")
        perm_layout = QVBoxLayout(perm_card)
        perm_layout.setContentsMargins(20, 18, 20, 18)
        perm_layout.setSpacing(12)

        perm_header = QLabel("Linux Kernel & udev Subsystem Permissions")
        perm_header.setStyleSheet("font-size: 14px; font-weight: 600;")
        perm_layout.addWidget(perm_header)

        self.uinput_status = QLabel("• /dev/uinput (Virtual Kernel Injection): Checking...")
        self.events_status = QLabel("• /dev/input/event* (Evdev Interception): Checking...")
        self.hidraw_status = QLabel("• /dev/hidraw* (Hardware RGB Control): Checking...")

        perm_layout.addWidget(self.uinput_status)
        perm_layout.addWidget(self.events_status)
        perm_layout.addWidget(self.hidraw_status)

        perm_actions = QHBoxLayout()
        self.perm_summary = QLabel("")
        self.perm_summary.setStyleSheet("font-weight: 500;")
        perm_actions.addWidget(self.perm_summary)
        perm_actions.addStretch()

        self.install_rules_btn = QPushButton("udev Setup Guide")
        self.install_rules_btn.clicked.connect(self._show_udev_guide)
        perm_actions.addWidget(self.install_rules_btn)

        perm_layout.addLayout(perm_actions)
        main_layout.addWidget(perm_card)

        # 3. Hardware Settings & Profile Sync Card
        sync_card = QFrame()
        sync_card.setObjectName("Card")
        sync_layout = QVBoxLayout(sync_card)
        sync_layout.setContentsMargins(20, 18, 20, 18)
        sync_layout.setSpacing(14)

        sync_title = QLabel("Hardware Tuning & Profiles")
        sync_title.setStyleSheet("font-size: 14px; font-weight: 600;")
        sync_layout.addWidget(sync_title)

        tuning_row = QHBoxLayout()
        tuning_row.addWidget(QLabel("USB Polling Rate:"))
        self.poll_combo = QComboBox()
        self.poll_combo.setView(QListView())
        for rate in POLLING_RATES.keys():
            self.poll_combo.addItem(rate)
        self.poll_combo.setCurrentText("1000Hz")
        tuning_row.addWidget(self.poll_combo)

        self.set_poll_btn = QPushButton("Set Polling Rate")
        self.set_poll_btn.setIcon(get_icon("check", size=14))
        self.set_poll_btn.clicked.connect(self._set_polling_rate)
        tuning_row.addWidget(self.set_poll_btn)
        tuning_row.addStretch()
        sync_layout.addLayout(tuning_row)

        profile_row = QHBoxLayout()
        self.export_btn = QPushButton("Export Profile (.json)")
        self.export_btn.setIcon(get_icon("device", size=14))
        self.export_btn.clicked.connect(self._export_profile)
        profile_row.addWidget(self.export_btn)

        self.import_btn = QPushButton("Import Profile (.json)")
        self.import_btn.setIcon(get_icon("plus", size=14))
        self.import_btn.clicked.connect(self._import_profile)
        profile_row.addWidget(self.import_btn)

        profile_row.addStretch()

        self.factory_reset_btn = QPushButton("Reset to Defaults")
        self.factory_reset_btn.setIcon(get_icon("trash", normal_color="#F87171", size=14))
        self.factory_reset_btn.setObjectName("DangerButton")
        self.factory_reset_btn.clicked.connect(self._factory_reset)
        profile_row.addWidget(self.factory_reset_btn)

        sync_layout.addLayout(profile_row)
        main_layout.addWidget(sync_card)

        main_layout.addStretch()

    def _query_live_battery(self):
        status = self.hid.query_device_status()
        if status and status.get("battery") is not None:
            pct = status["battery"]
            self.lbl_batt_pct.setText(f"{pct}%")
            self.batt_progress.setValue(pct)
            
            bar_color = "#10B981" if pct > 20 else "#EF4444"
            self.lbl_batt_pct.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {bar_color};")
            self.batt_progress.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #171A24;
                    border: 1px solid #1E2330;
                    border-radius: 4px;
                }}
                QProgressBar::chunk {{
                    background-color: {bar_color};
                    border-radius: 3px;
                }}
            """)
            self.batt_badge.setText("Active")
            self.batt_badge.setStyleSheet("color: #10B981; background: #132B22; border: 1px solid #1A4D38;")
            self.lbl_batt_state.setText(f"Operating on battery • Wireless 2.4G (Profile {status.get('profile_slot', 1)})")
            self.lbl_raw_telemetry.setText(f"Telemetry: Report ID 0x13 [0x4A] • Battery: {pct}% • MCU Radio Awake: {status.get('online', True)}")
            self.lbl_battery.setText(f"{pct}% (Wireless)")
            self.lbl_battery.setStyleSheet(f"color: {bar_color}; font-weight: 600;")
        else:
            self.batt_badge.setText("Unavailable")
            self.batt_badge.setStyleSheet("color: #8A94A6; background: #1A1F2C; border: 1px solid #242A3B;")
            self.lbl_batt_state.setText("Wired USB-C mode or keyboard in low-power sleep")
            self.lbl_raw_telemetry.setText("Battery telemetry only broadcast over 2.4GHz wireless channel")

    def refresh_status(self):
        self.device_info = MK75Detector.scan()
        summary = MK75Detector.get_udev_check_summary(self.device_info)

        if self.device_info.detected:
            self.conn_badge.setText(f"Connected: {self.device_info.connection_type}")
            self.conn_badge.setStyleSheet("color: #10B981; background: #132B22; border: 1px solid #1A4D38;")
            self.lbl_device_name.setText(self.device_info.name)
            self.lbl_vid_pid.setText(f"{self.device_info.vid:04X}:{self.device_info.pid:04X}")
            self.lbl_mode.setText(self.device_info.connection_type)
            self.lbl_hidraw.setText(self.device_info.primary_hidraw or "None")
            self.lbl_events.setText(", ".join(self.device_info.event_paths) if self.device_info.event_paths else "None")

            # Hardware battery query
            self._query_live_battery()
        else:
            self.conn_badge.setText("Disconnected")
            self.conn_badge.setStyleSheet("color: #EF4444; background: #2E151A; border: 1px solid #4D1A23;")
            self.lbl_device_name.setText("MK75 not detected on USB bus")
            self.lbl_vid_pid.setText("N/A")
            self.lbl_mode.setText("N/A")
            self.lbl_battery.setText("N/A")
            self.lbl_hidraw.setText("N/A")
            self.lbl_events.setText("N/A")

        # Subsystem Permission status
        if self.device_info.uinput_accessible:
            self.uinput_status.setText("/dev/uinput — Read and write access verified (Ready)")
            self.uinput_status.setStyleSheet("color: #10B981; font-weight: 500;")
        else:
            self.uinput_status.setText("/dev/uinput — Permission denied (Install udev rule)")
            self.uinput_status.setStyleSheet("color: #EF4444; font-weight: 500;")

        if self.device_info.event_accessible:
            self.events_status.setText("/dev/input/event* — Input device nodes accessible")
            self.events_status.setStyleSheet("color: #10B981; font-weight: 500;")
        else:
            self.events_status.setText("/dev/input/event* — Permission denied")
            self.events_status.setStyleSheet("color: #EF4444; font-weight: 500;")

        if self.device_info.hidraw_accessible:
            self.hidraw_status.setText("/dev/hidraw* — Hardware HID configuration channel open")
            self.hidraw_status.setStyleSheet("color: #10B981; font-weight: 500;")
        else:
            self.hidraw_status.setText("/dev/hidraw* — Permission denied")
            self.hidraw_status.setStyleSheet("color: #EF4444; font-weight: 500;")

        if summary["all_permissions_ok"]:
            self.perm_summary.setText("All kernel input and hidraw permissions verified.")
            self.perm_summary.setStyleSheet("color: #10B981;")
        else:
            self.perm_summary.setText("Some permissions restricted. Use setup script to install udev rules.")
            self.perm_summary.setStyleSheet("color: #F59E0B;")

    def _set_polling_rate(self):
        rate = self.poll_combo.currentText()
        ok = self.hid.set_polling_rate(rate)
        if ok:
            QMessageBox.information(self, "Success", f"Polling rate configured to {rate}")
        else:
            QMessageBox.warning(self, "Notice", f"Applied setting {rate} to profile. Connect hardware to commit.")

    def _show_udev_guide(self):
        rule_path = os.path.abspath("99-lingbao-mk75.rules")
        msg = (
            "To grant unprivileged non-root access to /dev/uinput, /dev/hidraw*, and /dev/input/event*:\n\n"
            f"1. Run setup.sh:\n"
            f"   sudo ./setup.sh\n\n"
            f"Or manually copy the rule file:\n"
            f"   sudo cp {rule_path} /etc/udev/rules.d/99-lingbao-mk75.rules\n"
            f"   sudo udevadm control --reload-rules && sudo udevadm trigger\n\n"
            f"Then unplug and replug the MK75 keyboard."
        )
        QMessageBox.information(self, "udev Rules Installation", msg)

    def _export_profile(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export MK75 Profile", "mk75_profile.json", "JSON Files (*.json)")
        if path:
            if self.profile_manager.export_to_file(path):
                QMessageBox.information(self, "Success", f"Profile exported to {path}")
            else:
                QMessageBox.critical(self, "Error", "Failed to export profile.")

    def _import_profile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import MK75 Profile", "", "JSON Files (*.json)")
        if path:
            if self.profile_manager.import_from_file(path):
                QMessageBox.information(self, "Success", f"Profile imported successfully from {path}")
            else:
                QMessageBox.critical(self, "Error", "Failed to import profile.")

    def _factory_reset(self):
        ans = QMessageBox.question(self, "Confirm Reset", "Reset all key remaps, macros, and lighting to factory default?")
        if ans == QMessageBox.Yes:
            from core.profile_manager import DEFAULT_PROFILE
            self.profile_manager.profile = dict(DEFAULT_PROFILE)
            self.profile_manager.save()
            QMessageBox.information(self, "Reset", "Profile reset to default settings.")
