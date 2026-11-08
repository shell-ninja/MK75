"""
Key and Rotary Knob Remapping Configuration Drawer / Panel.
Allows remapping keys to standard keycodes, macros, or arbitrary Linux shell commands.
Includes interactive physical key capture, quick media chips, and category selectors.
"""

from typing import Optional, Dict, Any, List
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QComboBox, QLineEdit, QFrame, QMessageBox, QListView
)

from config.keycodes import KeyDef, REMAP_ACTION_CATEGORIES, KNOB_ACTIONS
from ui.icons import get_icon
from ui.theme import (
    BG_CARD, BORDER_COLOR, ACCENT_PRIMARY, ACCENT_SKY,
    TEXT_PRIMARY, TEXT_MUTED
)

# Common Qt Key to Linux Evdev Keycode name
QT_KEY_TO_EVDEV = {
    Qt.Key_Escape: "KEY_ESC",
    Qt.Key_Tab: "KEY_TAB",
    Qt.Key_Backtab: "KEY_TAB",
    Qt.Key_Backspace: "KEY_BACKSPACE",
    Qt.Key_Return: "KEY_ENTER",
    Qt.Key_Enter: "KEY_KPENTER",
    Qt.Key_Insert: "KEY_INSERT",
    Qt.Key_Delete: "KEY_DELETE",
    Qt.Key_Pause: "KEY_PAUSE",
    Qt.Key_Print: "KEY_SYSRQ",
    Qt.Key_Home: "KEY_HOME",
    Qt.Key_End: "KEY_END",
    Qt.Key_Left: "KEY_LEFT",
    Qt.Key_Up: "KEY_UP",
    Qt.Key_Right: "KEY_RIGHT",
    Qt.Key_Down: "KEY_DOWN",
    Qt.Key_PageUp: "KEY_PAGEUP",
    Qt.Key_PageDown: "KEY_PAGEDOWN",
    Qt.Key_Shift: "KEY_LEFTSHIFT",
    Qt.Key_Control: "KEY_LEFTCTRL",
    Qt.Key_Meta: "KEY_LEFTMETA",
    Qt.Key_Alt: "KEY_LEFTALT",
    Qt.Key_AltGr: "KEY_RIGHTALT",
    Qt.Key_CapsLock: "KEY_CAPSLOCK",
    Qt.Key_NumLock: "KEY_NUMLOCK",
    Qt.Key_ScrollLock: "KEY_SCROLLLOCK",
    Qt.Key_Space: "KEY_SPACE",
    Qt.Key_Minus: "KEY_MINUS",
    Qt.Key_Equal: "KEY_EQUAL",
    Qt.Key_BracketLeft: "KEY_LEFTBRACE",
    Qt.Key_BracketRight: "KEY_RIGHTBRACE",
    Qt.Key_Semicolon: "KEY_SEMICOLON",
    Qt.Key_Apostrophe: "KEY_APOSTROPHE",
    Qt.Key_QuoteLeft: "KEY_GRAVE",
    Qt.Key_Backslash: "KEY_BACKSLASH",
    Qt.Key_Comma: "KEY_COMMA",
    Qt.Key_Period: "KEY_DOT",
    Qt.Key_Slash: "KEY_SLASH",
}

# Quick Media / Navigation Shortcuts
QUICK_MEDIA_CHIPS = [
    ("Vol +", "KEY_VOLUMEUP"),
    ("Vol -", "KEY_VOLUMEDOWN"),
    ("Mute", "KEY_MUTE"),
    ("Play/Pause", "KEY_PLAYPAUSE"),
    ("Next", "KEY_NEXTSONG"),
    ("Prev", "KEY_PREVIOUSSONG"),
    ("Bright +", "KEY_BRIGHTNESSUP"),
    ("Bright -", "KEY_BRIGHTNESSDOWN"),
    ("Calc", "KEY_CALC"),
]

class SingleKeyCaptureBox(QPushButton):
    """Button that listens for a single physical keystroke to remap."""

    key_captured = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recording = False
        self.captured_key: Optional[str] = None
        self.setMinimumHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self._update_display()
        self.clicked.connect(self._toggle_recording)

    def set_key(self, key_code: Optional[str]):
        self.captured_key = key_code
        self.recording = False
        self._update_display()

    def _update_display(self):
        if self.recording:
            self.setText("Listening... Press any key on keyboard (or Esc to cancel)")
            self.setStyleSheet(
                "background-color: #2D2418; color: #F59E0B; border: 2px dashed #D97706; "
                "font-size: 13px; font-weight: 600; border-radius: 8px;"
            )
        else:
            if not self.captured_key:
                self.setText("Click to record key directly from keyboard...")
                self.setStyleSheet(
                    "background-color: #171A26; color: #8A94A6; border: 1px dashed #2E384D; "
                    "font-size: 13px; border-radius: 8px;"
                )
            else:
                clean_name = self.captured_key.replace("KEY_", "")
                self.setText(f"Target Key: [ {clean_name} ]  (Click to record new key)")
                self.setStyleSheet(
                    "background-color: #1A2236; color: #FFFFFF; border: 1px solid #3B4666; "
                    "font-size: 13px; font-weight: 600; border-radius: 8px;"
                )

    def _toggle_recording(self):
        self.recording = not self.recording
        self._update_display()

    def keyPressEvent(self, event: QKeyEvent):
        if not self.recording:
            super().keyPressEvent(event)
            return

        key_val = event.key()
        if key_val == Qt.Key_Escape:
            self.recording = False
            self._update_display()
            return

        evdev_key = QT_KEY_TO_EVDEV.get(key_val)
        if not evdev_key:
            if Qt.Key_A <= key_val <= Qt.Key_Z:
                evdev_key = f"KEY_{chr(key_val)}"
            elif Qt.Key_0 <= key_val <= Qt.Key_9:
                evdev_key = f"KEY_{chr(key_val)}"
            elif Qt.Key_F1 <= key_val <= Qt.Key_F12:
                evdev_key = f"KEY_F{key_val - Qt.Key_F1 + 1}"

        if evdev_key:
            self.captured_key = evdev_key
            self.recording = False
            self._update_display()
            self.key_captured.emit(evdev_key)


class KeyConfigPanel(QFrame):
    """Configuration panel to customize the selected key or rotary knob."""

    remap_changed = Signal()

    def __init__(self, profile_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.profile_manager = profile_manager
        self.current_key: Optional[KeyDef] = None
        self.active_target_id: str = "KEY_ESC"
        self.selected_target_key: Optional[str] = "KEY_ESC"

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Header Section
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Select a Key or the Knob")
        self.title_label.setObjectName("TitleLabel")
        header_layout.addWidget(self.title_label)

        self.status_badge = QLabel("Default")
        self.status_badge.setObjectName("Badge")
        header_layout.addWidget(self.status_badge)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Knob Action Sub-Selector (Visible only when Knob is selected)
        self.knob_selector_frame = QFrame()
        knob_layout = QHBoxLayout(self.knob_selector_frame)
        knob_layout.setContentsMargins(0, 0, 0, 0)
        knob_label = QLabel("Knob Action:")
        knob_label.setStyleSheet("font-weight: 600; color: #38BDF8;")
        knob_layout.addWidget(knob_label)

        self.knob_combo = QComboBox()
        self.knob_combo.setView(QListView())
        for action in KNOB_ACTIONS:
            self.knob_combo.addItem(action["label"], action["id"])
        self.knob_combo.currentIndexChanged.connect(self._on_knob_action_changed)
        knob_layout.addWidget(self.knob_combo)
        layout.addWidget(self.knob_selector_frame)
        self.knob_selector_frame.hide()

        # Tabs for Remapping Type
        self.tabs = QTabWidget()

        # Tab 1: Direct Key / Media Remap
        self.tab_key = QWidget()
        tab_key_layout = QVBoxLayout(self.tab_key)
        tab_key_layout.setContentsMargins(14, 14, 14, 14)
        tab_key_layout.setSpacing(10)

        # 1. Interactive Key Capture Box
        short_desc = QLabel("Option 1: Click the box below and press any key on your keyboard to assign it directly:")
        short_desc.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        tab_key_layout.addWidget(short_desc)

        self.key_capture_box = SingleKeyCaptureBox()
        self.key_capture_box.key_captured.connect(self._on_key_captured)
        tab_key_layout.addWidget(self.key_capture_box)

        # 2. Quick Media / Volume Chips
        media_box = QVBoxLayout()
        media_box.setSpacing(6)
        media_lbl = QLabel("Option 2: One-click media & navigation shortcuts:")
        media_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        media_box.addWidget(media_lbl)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)
        for label, code in QUICK_MEDIA_CHIPS:
            btn = QPushButton(label)
            btn.setStyleSheet("font-size: 11px; padding: 4px 9px; background: #161A26;")
            btn.clicked.connect(lambda _, c=code: self._select_target_key(c))
            chips_row.addWidget(btn)
        chips_row.addStretch()
        media_box.addLayout(chips_row)
        tab_key_layout.addLayout(media_box)

        # 3. Dropdown Search / Category Selector
        cat_box = QHBoxLayout()
        cat_box.setSpacing(10)
        cat_box.addWidget(QLabel("Category:"))
        self.cat_combo = QComboBox()
        self.cat_combo.setView(QListView())
        for cat in REMAP_ACTION_CATEGORIES.keys():
            self.cat_combo.addItem(cat)
        self.cat_combo.currentIndexChanged.connect(self._populate_keys_combo)
        cat_box.addWidget(self.cat_combo)

        cat_box.addWidget(QLabel("Action:"))
        self.key_action_combo = QComboBox()
        self.key_action_combo.setView(QListView())
        self.key_action_combo.currentIndexChanged.connect(self._on_action_combo_changed)
        cat_box.addWidget(self.key_action_combo, 1)
        tab_key_layout.addLayout(cat_box)

        self.tabs.addTab(self.tab_key, get_icon("keyboard", size=14), "Key / Media")

        # Tab 2: Macro Assignment
        self.tab_macro = QWidget()
        tab_macro_layout = QVBoxLayout(self.tab_macro)
        tab_macro_layout.setContentsMargins(14, 14, 14, 14)
        tab_macro_layout.setSpacing(10)
        tab_macro_layout.addWidget(QLabel("Select a saved macro to trigger:"))
        self.macro_combo = QComboBox()
        self.macro_combo.setView(QListView())
        tab_macro_layout.addWidget(self.macro_combo)
        tab_macro_layout.addStretch()
        self.tabs.addTab(self.tab_macro, get_icon("macro", size=14), "Macro")

        # Tab 3: Linux Shell Command
        self.tab_command = QWidget()
        tab_cmd_layout = QVBoxLayout(self.tab_command)
        tab_cmd_layout.setContentsMargins(14, 14, 14, 14)
        tab_cmd_layout.setSpacing(10)
        tab_cmd_layout.addWidget(QLabel("Execute custom Linux shell command when pressed:"))
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("e.g. kitty & or pactl set-sink-volume @DEFAULT_SINK@ +5%")
        tab_cmd_layout.addWidget(self.cmd_input)

        presets_lbl = QLabel("Quick Presets:")
        presets_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        tab_cmd_layout.addWidget(presets_lbl)

        presets_layout = QHBoxLayout()
        presets = [
            ("Terminal", "kitty &"),
            ("Screenshot", "grim -g \"$(slurp)\" - | wl-copy &"),
            ("Volume +5%", "pactl set-sink-volume @DEFAULT_SINK@ +5%"),
            ("Volume -5%", "pactl set-sink-volume @DEFAULT_SINK@ -5%"),
            ("Mute Toggle", "pactl set-sink-mute @DEFAULT_SINK@ toggle"),
            ("Next Track", "playerctl next"),
        ]
        for name, cmd in presets:
            btn = QPushButton(name)
            btn.setStyleSheet("font-size: 11px; padding: 4px 8px; background: #161A26;")
            btn.clicked.connect(lambda _, c=cmd: self.cmd_input.setText(c))
            presets_layout.addWidget(btn)
        presets_layout.addStretch()
        tab_cmd_layout.addLayout(presets_layout)
        tab_cmd_layout.addStretch()
        self.tabs.addTab(self.tab_command, get_icon("terminal", size=14), "Linux Command")

        layout.addWidget(self.tabs)

        # Bottom Actions Row
        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.setIcon(get_icon("trash", normal_color="#F87171", size=14))
        self.reset_btn.setObjectName("DangerButton")
        self.reset_btn.clicked.connect(self._on_reset_remap)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()

        self.apply_btn = QPushButton("Apply Mapping")
        self.apply_btn.setIcon(get_icon("check", normal_color="#FFFFFF", size=14))
        self.apply_btn.setObjectName("PrimaryButton")
        self.apply_btn.setMinimumHeight(38)
        self.apply_btn.clicked.connect(self._on_apply_remap)
        btn_layout.addWidget(self.apply_btn)

        layout.addLayout(btn_layout)

        self._populate_keys_combo()
        self._populate_macros_combo()

    def _select_target_key(self, code: str):
        self.selected_target_key = code
        self.key_capture_box.set_key(code)
        self._sync_combo_to_key(code)

    def _on_key_captured(self, code: str):
        self.selected_target_key = code
        self._sync_combo_to_key(code)

    def _sync_combo_to_key(self, code: str):
        for cat, items in REMAP_ACTION_CATEGORIES.items():
            for c, label in items:
                if c == code:
                    self.cat_combo.blockSignals(True)
                    self.cat_combo.setCurrentText(cat)
                    self.cat_combo.blockSignals(False)
                    self._populate_keys_combo()

                    self.key_action_combo.blockSignals(True)
                    for i in range(self.key_action_combo.count()):
                        if self.key_action_combo.itemData(i) == code:
                            self.key_action_combo.setCurrentIndex(i)
                            break
                    self.key_action_combo.blockSignals(False)
                    return

    def _on_action_combo_changed(self):
        code = self.key_action_combo.currentData()
        if code:
            self.selected_target_key = code
            self.key_capture_box.set_key(code)

    def _populate_keys_combo(self):
        cat = self.cat_combo.currentText()
        items = REMAP_ACTION_CATEGORIES.get(cat, [])
        self.key_action_combo.blockSignals(True)
        self.key_action_combo.clear()
        for code, label in items:
            self.key_action_combo.addItem(f"{label} ({code})", code)
        self.key_action_combo.blockSignals(False)

    def _populate_macros_combo(self):
        self.macro_combo.clear()
        macros = self.profile_manager.get_macros()
        for m in macros:
            self.macro_combo.addItem(m.get("name", "Unnamed"), m.get("id"))

    def set_key(self, key_def: KeyDef):
        self.current_key = key_def
        self._populate_macros_combo()

        if key_def.is_knob:
            self.knob_selector_frame.show()
            self.active_target_id = self.knob_combo.currentData()
            self.title_label.setText("Multifunction Rotary Knob")
        else:
            self.knob_selector_frame.hide()
            self.active_target_id = key_def.id
            self.title_label.setText(f"Key: {key_def.label} ({key_def.keycode_name})")

        self._load_active_mapping()

    def _on_knob_action_changed(self):
        if self.current_key and self.current_key.is_knob:
            self.active_target_id = self.knob_combo.currentData()
            self._load_active_mapping()

    def _load_active_mapping(self):
        remap = self.profile_manager.get_remapping(self.active_target_id)
        if not remap:
            self.status_badge.setText("Default")
            self.status_badge.setStyleSheet("color: #9CA3AF;")
            self.tabs.setCurrentIndex(0)
            default_key = self.current_key.keycode_name if (self.current_key and not self.current_key.is_knob) else "KEY_MUTE"
            self._select_target_key(default_key)
            self.cmd_input.clear()
            return

        remap_type = remap.get("type")
        if remap_type == "key":
            target = remap.get("target")
            clean_name = target.replace("KEY_", "")
            self.status_badge.setText(f"Mapped: {clean_name}")
            self.status_badge.setStyleSheet("color: #6366F1;")
            self.tabs.setCurrentIndex(0)
            self._select_target_key(target)
        elif remap_type == "macro":
            self.status_badge.setText("Macro Assigned")
            self.status_badge.setStyleSheet("color: #38BDF8;")
            self.tabs.setCurrentIndex(1)
            macro_id = remap.get("macro_id")
            for i in range(self.macro_combo.count()):
                if self.macro_combo.itemData(i) == macro_id:
                    self.macro_combo.setCurrentIndex(i)
                    break
        elif remap_type == "command":
            self.status_badge.setText("Shell Command")
            self.status_badge.setStyleSheet("color: #10B981;")
            self.tabs.setCurrentIndex(2)
            self.cmd_input.setText(remap.get("command", ""))

    def _on_apply_remap(self):
        tab_idx = self.tabs.currentIndex()
        if tab_idx == 0:
            target_key = self.selected_target_key or self.key_action_combo.currentData()
            if target_key:
                self.profile_manager.set_key_remap(self.active_target_id, target_key)
        elif tab_idx == 1:
            macro_id = self.macro_combo.currentData()
            if macro_id:
                self.profile_manager.set_macro_remap(self.active_target_id, macro_id)
        elif tab_idx == 2:
            cmd = self.cmd_input.text().strip()
            if cmd:
                self.profile_manager.set_command_remap(self.active_target_id, cmd)

        self._load_active_mapping()
        self.remap_changed.emit()

    def _on_reset_remap(self):
        self.profile_manager.clear_remap(self.active_target_id)
        self._load_active_mapping()
        self.remap_changed.emit()
