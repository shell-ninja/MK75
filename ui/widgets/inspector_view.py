"""
HID Packet Inspector and Sniffer / Tester for Lingbao MK75.
Allows crafting custom 64-byte feature reports, testing RGB payloads,
and analyzing inbound/outbound packets in real time.
"""

import time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QComboBox, QMessageBox
)

from core.hid_controller import (
    MK75HardwareController, REPORT_ID_FEATURE, REPORT_ID_WIRELESS,
    CMD_SET_LED, CMD_SET_CUSTOM, CMD_PROFILE, CMD_LIVE
)
from ui.icons import get_icon
from ui.theme import (
    BG_CARD, BORDER_COLOR, ACCENT_PRIMARY, ACCENT_SKY,
    ACCENT_EMERALD, ACCENT_ROSE, TEXT_PRIMARY, TEXT_MUTED
)

# Preset Packet Payloads for Instant Testing (Report 0x13 and Report 0x06)
PAYLOAD_PRESETS = [
    ("Report 0x13: Probe Profile (0x4A)", "13 4A 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 5E"),
    ("Report 0x13: Read LED Block (0x44)", "13 44 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 58"),
    ("Report 0x06: Static Red (8 Bytes)", "06 04 01 64 32 FF 00 00"),
    ("Report 0x06: Rainbow Wave (8 Bytes)", "06 04 06 64 32 00 00 00"),
    ("Report 0x06: Query Status (0x84)", "06 84 00 00 00 00 00 00"),
    ("Report 0x06: Commit Flash (0x0A)", "06 0A 01 00 00 00 00 00"),
]

class InspectorView(QWidget):
    """View to craft, inspect, test, and sniff raw USB HID feature packets."""

    def __init__(self, hid_controller: MK75HardwareController, parent=None):
        super().__init__(parent)
        self.hid = hid_controller

        self._build_ui()

        # Timer to poll incoming packets or refresh traffic
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_traffic)
        self.poll_timer.start(500)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Title
        title_box = QVBoxLayout()
        title = QLabel("HID Packet Inspector & Hardware Tester")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Craft, send, and analyze 64-byte USB HID feature reports over /dev/hidraw for reverse-engineering.")
        subtitle.setObjectName("SubtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        main_layout.addLayout(title_box)

        # Top Card: Packet Builder
        builder_card = QFrame()
        builder_card.setObjectName("Card")
        builder_layout = QVBoxLayout(builder_card)
        builder_layout.setContentsMargins(20, 18, 20, 18)
        builder_layout.setSpacing(12)

        # Config Row: Report ID & Preset selector
        cfg_row = QHBoxLayout()
        cfg_row.addWidget(QLabel("Target Report ID:"))
        self.report_id_combo = QComboBox()
        self.report_id_combo.addItem("Report 0x06 (Primary Vendor Feature)", 0x06)
        self.report_id_combo.addItem("Report 0x13 (Secondary Vendor Channel)", 0x13)
        self.report_id_combo.addItem("Report 0x05 (Consumer / Control)", 0x05)
        self.report_id_combo.addItem("Report 0x00 (Direct Unnumbered)", 0x00)
        cfg_row.addWidget(self.report_id_combo)

        cfg_row.addSpacing(20)
        cfg_row.addWidget(QLabel("Quick Templates:"))
        self.template_combo = QComboBox()
        self.template_combo.addItem("-- Select Preset Packet --")
        for name, payload in PAYLOAD_PRESETS:
            self.template_combo.addItem(name, payload)
        self.template_combo.currentIndexChanged.connect(self._on_preset_selected)
        cfg_row.addWidget(self.template_combo, 1)

        builder_layout.addLayout(cfg_row)

        # Hex Input
        hex_label = QLabel("Hex Payload (Space or Comma separated):")
        builder_layout.addWidget(hex_label)

        self.hex_input = QLineEdit("04 01 03 03 02 00 63 66 F1 01")
        self.hex_input.setStyleSheet("font-family: monospace; font-size: 13px; font-weight: 600; color: #38BDF8;")
        builder_layout.addWidget(self.hex_input)

        # Buttons Row
        btn_row = QHBoxLayout()
        self.send_btn = QPushButton(" Send Feature Report (OUT)")
        self.send_btn.setIcon(get_icon("play", normal_color="#FFFFFF", active_color="#FFFFFF"))
        self.send_btn.setObjectName("PrimaryButton")
        self.send_btn.clicked.connect(self._send_payload)
        btn_row.addWidget(self.send_btn)

        self.read_btn = QPushButton(" Read Response (IN)")
        self.read_btn.setIcon(get_icon("refresh", normal_color="#8A94A6", active_color="#FFFFFF"))
        self.read_btn.clicked.connect(self._read_response)
        btn_row.addWidget(self.read_btn)

        btn_row.addStretch()

        self.status_lbl = QLabel("")
        btn_row.addWidget(self.status_lbl)

        builder_layout.addLayout(btn_row)
        main_layout.addWidget(builder_card)

        # Bottom Card: Live Packet Traffic Log
        log_card = QFrame()
        log_card.setObjectName("Card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(20, 18, 20, 18)
        log_layout.setSpacing(10)

        log_header = QHBoxLayout()
        log_title = QLabel("Live HID Packet Monitor")
        log_title.setStyleSheet("font-size: 14px; font-weight: 600;")
        log_header.addWidget(log_title)
        log_header.addStretch()

        self.clear_btn = QPushButton(" Clear Monitor")
        self.clear_btn.setIcon(get_icon("trash", normal_color="#8A94A6", active_color="#FFFFFF"))
        self.clear_btn.clicked.connect(self._clear_monitor)
        log_header.addWidget(self.clear_btn)

        log_layout.addLayout(log_header)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Time", "Direction", "Len", "Hex Bytes"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setStyleSheet("font-family: monospace; font-size: 11px;")
        log_layout.addWidget(self.table)

        main_layout.addWidget(log_card, 1)

    def _on_preset_selected(self, index: int):
        if index <= 0:
            return
        payload = self.template_combo.currentData()
        if payload:
            self.hex_input.setText(payload)

    def _send_payload(self):
        hex_text = self.hex_input.text().strip()
        report_id = self.report_id_combo.currentData()
        ok = self.hid.send_raw_hex(hex_text, report_id=report_id)

        if ok:
            self.status_lbl.setText("Sent successfully")
            self.status_lbl.setStyleSheet("color: #10B981; font-weight: 500;")
        else:
            self.status_lbl.setText("Failed to send (check permissions/connection)")
            self.status_lbl.setStyleSheet("color: #EF4444; font-weight: 500;")

        self._refresh_table()

    def _read_response(self):
        resp = self.hid.read_response(65, timeout_ms=300)
        if resp:
            self.status_lbl.setText(f"Received {len(resp)} bytes")
            self.status_lbl.setStyleSheet("color: #10B981; font-weight: 500;")
        else:
            self.status_lbl.setText("No data returned")
            self.status_lbl.setStyleSheet("color: #9CA3AF; font-weight: 500;")
        self._refresh_table()

    def _poll_traffic(self):
        # Periodically refresh packet table if new entries exist
        if len(self.hid.packet_history) != self.table.rowCount():
            self._refresh_table()

    def _refresh_table(self):
        history = list(self.hid.packet_history)
        self.table.setRowCount(0)
        for p in reversed(history):
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Timestamp
            self.table.setItem(row, 0, QTableWidgetItem(p["timestamp"]))

            # Direction
            dir_item = QTableWidgetItem(p["direction"])
            if "OUT" in p["direction"]:
                dir_item.setForeground(Qt.cyan)
            else:
                dir_item.setForeground(Qt.green)
            self.table.setItem(row, 1, dir_item)

            # Length
            self.table.setItem(row, 2, QTableWidgetItem(f"{p['length']}B"))

            # Hex dump
            self.table.setItem(row, 3, QTableWidgetItem(p["hex"]))

    def _clear_monitor(self):
        self.hid.packet_history.clear()
        self.table.setRowCount(0)
