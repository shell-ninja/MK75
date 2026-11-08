"""
Interactive Keyboard Macro & Shortcut Builder for MK75.
Click any key on the visual keyboard preview to assign a multi-key shortcut,
Linux shell command, or auto-type text expander.
"""

from typing import Dict, Any, List, Optional, Set
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QPlainTextEdit, QFrame, QScrollArea, QTabWidget,
    QComboBox, QMessageBox, QListView
)

from config.keycodes import KeyDef, KNOB_ACTIONS
from core.macro_engine import MacroEngine
from ui.icons import get_icon
from ui.theme import (
    BG_CARD, BORDER_COLOR, ACCENT_PRIMARY, ACCENT_SKY,
    ACCENT_EMERALD, ACCENT_ROSE, ACCENT_AMBER, TEXT_PRIMARY, TEXT_MUTED,
    configure_dark_combobox
)
from ui.widgets.keyboard_visualizer import KeyboardVisualizer
from ui.widgets.key_capture import KeyCaptureBox, PRESET_SHORTCUTS

# Standard Linux App & System Presets
PRESET_COMMANDS = [
    ("Terminal", "kitty &"),
    ("Screenshot", "grim -g \"$(slurp)\" - | wl-copy &"),
    ("Mute Mic", "pactl set-source-mute @DEFAULT_SOURCE@ toggle"),
    ("Play / Pause", "playerctl play-pause"),
    ("Next Track", "playerctl next"),
    ("Lock Session", "loginctl lock-session"),
    ("File Manager", "xdg-open ~ &"),
]


class MacrosView(QWidget):
    """
    Visual Macro & Shortcut configurator.
    Shows the keyboard preview on top. Clicking any key opens the shortcut/command
    assignment card underneath with interactive modifier chips and step guidance.
    """

    macro_changed = Signal()

    def __init__(self, profile_manager, macro_engine: MacroEngine, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.macro_engine = macro_engine
        self.current_key: Optional[KeyDef] = None
        self.active_target_id: str = "KEY_DELETE"

        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Wrap in scroll area so small screens / tiled windows never clip
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(14)

        # 1. Header
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Macros & Shortcuts")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Click any key on the visual keyboard below to bind custom shortcuts or Linux commands.")
        subtitle.setObjectName("SubtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # 2. Interactive Keyboard Visualizer (Hero Component)
        self.visualizer = KeyboardVisualizer(self.profile_manager)
        self.visualizer.key_selected.connect(self._on_key_selected)
        layout.addWidget(self.visualizer)

        # 3. Step-by-Step Visual Guidance Banner
        guide_bar = QFrame()
        guide_bar.setStyleSheet(
            "background-color: #141722; border: 1px solid #232838; border-radius: 8px; padding: 6px 12px;"
        )
        guide_layout = QHBoxLayout(guide_bar)
        guide_layout.setContentsMargins(8, 6, 8, 6)
        guide_layout.setSpacing(12)

        s1 = QLabel("1. Click a key above")
        s1.setStyleSheet("color: #38BDF8; font-weight: 600; font-size: 11px;")
        arrow1 = QLabel("→")
        arrow1.setStyleSheet("color: #4B5563; font-weight: 700;")
        s2 = QLabel("2. Select Shortcut, Command, or Text")
        s2.setStyleSheet("color: #E2E8F0; font-weight: 500; font-size: 11px;")
        arrow2 = QLabel("→")
        arrow2.setStyleSheet("color: #4B5563; font-weight: 700;")
        s3 = QLabel("3. Click 'Save & Apply to Key'")
        s3.setStyleSheet("color: #10B981; font-weight: 600; font-size: 11px;")

        guide_layout.addWidget(s1)
        guide_layout.addWidget(arrow1)
        guide_layout.addWidget(s2)
        guide_layout.addWidget(arrow2)
        guide_layout.addWidget(s3)
        guide_layout.addStretch()
        layout.addWidget(guide_bar)

        # 4. Macro Configuration Card (Under Keyboard)
        self.card = QFrame()
        self.card.setObjectName("Card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(14)

        # Header Row: Key Title + Status Badge
        header_row = QHBoxLayout()
        self.lbl_selected = QLabel("Selected Key: Delete (KEY_DELETE)")
        self.lbl_selected.setObjectName("TitleLabel")
        header_row.addWidget(self.lbl_selected)

        self.status_badge = QLabel("No Macro (Default)")
        self.status_badge.setObjectName("Badge")
        header_row.addWidget(self.status_badge)
        header_row.addStretch()
        card_layout.addLayout(header_row)

        # Knob turn sub-selector (visible when knob is clicked)
        self.knob_selector_frame = QFrame()
        knob_layout = QHBoxLayout(self.knob_selector_frame)
        knob_layout.setContentsMargins(0, 0, 0, 0)
        knob_label = QLabel("Knob Action to Bind:")
        knob_label.setStyleSheet("font-weight: 600; color: #38BDF8;")
        knob_layout.addWidget(knob_label)

        self.knob_combo = QComboBox()
        self.knob_combo.setFixedWidth(280)
        configure_dark_combobox(self.knob_combo)
        for action in KNOB_ACTIONS:
            self.knob_combo.addItem(action["label"], action["id"])
        self.knob_combo.currentIndexChanged.connect(self._on_knob_action_changed)
        knob_layout.addWidget(self.knob_combo)
        knob_layout.addStretch()
        card_layout.addWidget(self.knob_selector_frame)
        self.knob_selector_frame.hide()

        # Tabs: Shortcut vs Command vs Text
        self.tabs = QTabWidget()

        # Tab 1: Key Shortcut
        self.tab_shortcut = QWidget()
        short_layout = QVBoxLayout(self.tab_shortcut)
        short_layout.setContentsMargins(14, 14, 14, 14)
        short_layout.setSpacing(12)

        # Modifier Toggle Chips
        mod_box = QHBoxLayout()
        mod_box.setSpacing(8)
        mod_lbl = QLabel("Hold / Toggle Modifiers:")
        mod_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: 500;")
        mod_box.addWidget(mod_lbl)

        self.mod_ctrl_btn = QPushButton("Ctrl")
        self.mod_shift_btn = QPushButton("Shift")
        self.mod_alt_btn = QPushButton("Alt")
        self.mod_super_btn = QPushButton("Super / Win")

        mod_style = """
            QPushButton {
                font-size: 12px;
                font-weight: 600;
                padding: 5px 14px;
                border-radius: 6px;
                background-color: #161A26;
                color: #9CA3AF;
                border: 1px solid #2B3245;
            }
            QPushButton:hover {
                background-color: #212738;
                color: #FFFFFF;
            }
            QPushButton:checked {
                background-color: #1E2B4D;
                color: #38BDF8;
                border: 1px solid #3B82F6;
            }
        """

        for btn, code in [
            (self.mod_ctrl_btn, "KEY_LEFTCTRL"),
            (self.mod_shift_btn, "KEY_LEFTSHIFT"),
            (self.mod_alt_btn, "KEY_LEFTALT"),
            (self.mod_super_btn, "KEY_LEFTMETA"),
        ]:
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(mod_style)
            btn.toggled.connect(lambda checked, c=code: self.capture_box.set_modifier_toggled(c, checked))
            mod_box.addWidget(btn)

        mod_box.addStretch()
        short_layout.addLayout(mod_box)

        # Primary Key Capture Box
        rec_desc = QLabel("Keystroke Capture Box (Click and press combination on keyboard):")
        rec_desc.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        short_layout.addWidget(rec_desc)

        self.capture_box = KeyCaptureBox()
        self.capture_box.shortcut_recorded.connect(self._sync_modifier_buttons)
        self.capture_box.modifiers_updated.connect(self._on_modifiers_held_live)
        short_layout.addWidget(self.capture_box)

        # Quick preset chips
        chips_box = QVBoxLayout()
        chips_box.setSpacing(6)
        chips_lbl = QLabel("Quick Shortcut Presets:")
        chips_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        chips_box.addWidget(chips_lbl)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)
        for label, keys in PRESET_SHORTCUTS:
            btn = QPushButton(label)
            btn.setStyleSheet("font-size: 11px; padding: 4px 9px; background: #161A26;")
            btn.clicked.connect(lambda _, k=keys: self._apply_preset_shortcut(k))
            chips_row.addWidget(btn)
        chips_row.addStretch()
        chips_box.addLayout(chips_row)
        short_layout.addLayout(chips_box)

        self.tabs.addTab(self.tab_shortcut, get_icon("keyboard", size=14), "Key Shortcut")

        # Tab 2: Linux Command
        self.tab_cmd = QWidget()
        cmd_layout = QVBoxLayout(self.tab_cmd)
        cmd_layout.setContentsMargins(14, 14, 14, 14)
        cmd_layout.setSpacing(10)

        cmd_desc = QLabel("Execute a Linux shell command or launch an application when pressed:")
        cmd_desc.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        cmd_layout.addWidget(cmd_desc)

        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("e.g. kitty & or pactl set-sink-volume @DEFAULT_SINK@ +5%")
        cmd_layout.addWidget(self.cmd_input)

        pills_box = QVBoxLayout()
        pills_box.setSpacing(6)
        pills_lbl = QLabel("Quick Linux App Presets:")
        pills_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        pills_box.addWidget(pills_lbl)

        pills_row = QHBoxLayout()
        pills_row.setSpacing(6)
        for label, cmd_str in PRESET_COMMANDS:
            btn = QPushButton(label)
            btn.setStyleSheet("font-size: 11px; padding: 4px 9px; background: #161A26;")
            btn.clicked.connect(lambda _, c=cmd_str: self.cmd_input.setText(c))
            pills_row.addWidget(btn)
        pills_row.addStretch()
        pills_box.addLayout(pills_row)
        cmd_layout.addLayout(pills_box)

        self.tabs.addTab(self.tab_cmd, get_icon("terminal", size=14), "Linux Command")

        # Tab 3: Text Expander
        self.tab_text = QWidget()
        text_layout = QVBoxLayout(self.tab_text)
        text_layout.setContentsMargins(14, 14, 14, 14)
        text_layout.setSpacing(10)

        text_desc = QLabel("Automatically type text or code snippet when key is pressed:")
        text_desc.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        text_layout.addWidget(text_desc)

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("e.g. git status or my_email@domain.com")
        text_layout.addWidget(self.text_input)
        text_layout.addStretch()

        self.tabs.addTab(self.tab_text, get_icon("macro", size=14), "Auto-Type Text")

        card_layout.addWidget(self.tabs)

        # Bottom Action Buttons Row
        actions_row = QHBoxLayout()
        self.clear_btn = QPushButton("Reset Key (Clear Macro)")
        self.clear_btn.setIcon(get_icon("trash", normal_color="#F87171", size=14))
        self.clear_btn.setObjectName("DangerButton")
        self.clear_btn.clicked.connect(self._clear_macro)
        actions_row.addWidget(self.clear_btn)

        self.test_btn = QPushButton("Test Macro")
        self.test_btn.setIcon(get_icon("play", normal_color="#38BDF8", size=14))
        self.test_btn.setStyleSheet("color: #38BDF8; font-weight: 600; padding: 6px 14px;")
        self.test_btn.clicked.connect(self._test_macro)
        actions_row.addWidget(self.test_btn)

        self.feedback_label = QLabel("")
        self.feedback_label.setStyleSheet("color: #10B981; font-weight: 500; font-size: 12px; padding-left: 8px;")
        actions_row.addWidget(self.feedback_label)

        actions_row.addStretch()

        self.save_btn = QPushButton("Save & Apply to Key")
        self.save_btn.setIcon(get_icon("check", normal_color="#FFFFFF", size=14))
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.setMinimumHeight(38)
        self.save_btn.clicked.connect(self._save_macro)
        actions_row.addWidget(self.save_btn)

        card_layout.addLayout(actions_row)
        layout.addWidget(self.card)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

        # Select Delete key by default
        self.visualizer.select_key("KEY_DELETE")

    def _apply_preset_shortcut(self, keys: List[str]):
        self.capture_box.set_keys(keys)
        self._sync_modifier_buttons(keys)

    def _sync_modifier_buttons(self, keys: List[str]):
        self.mod_ctrl_btn.blockSignals(True)
        self.mod_shift_btn.blockSignals(True)
        self.mod_alt_btn.blockSignals(True)
        self.mod_super_btn.blockSignals(True)

        self.mod_ctrl_btn.setChecked("KEY_LEFTCTRL" in keys)
        self.mod_shift_btn.setChecked("KEY_LEFTSHIFT" in keys)
        self.mod_alt_btn.setChecked("KEY_LEFTALT" in keys)
        self.mod_super_btn.setChecked("KEY_LEFTMETA" in keys)

        self.mod_ctrl_btn.blockSignals(False)
        self.mod_shift_btn.blockSignals(False)
        self.mod_alt_btn.blockSignals(False)
        self.mod_super_btn.blockSignals(False)

    def _on_modifiers_held_live(self, held: Set[str]):
        self.mod_ctrl_btn.blockSignals(True)
        self.mod_shift_btn.blockSignals(True)
        self.mod_alt_btn.blockSignals(True)
        self.mod_super_btn.blockSignals(True)

        self.mod_ctrl_btn.setChecked("KEY_LEFTCTRL" in held)
        self.mod_shift_btn.setChecked("KEY_LEFTSHIFT" in held)
        self.mod_alt_btn.setChecked("KEY_LEFTALT" in held)
        self.mod_super_btn.setChecked("KEY_LEFTMETA" in held)

        self.mod_ctrl_btn.blockSignals(False)
        self.mod_shift_btn.blockSignals(False)
        self.mod_alt_btn.blockSignals(False)
        self.mod_super_btn.blockSignals(False)

    def _on_key_selected(self, key_def: KeyDef):
        self.current_key = key_def
        self.feedback_label.setText("")

        if key_def.is_knob:
            self.knob_selector_frame.show()
            self.active_target_id = self.knob_combo.currentData()
            self.lbl_selected.setText("Multifunction Rotary Knob")
        else:
            self.knob_selector_frame.hide()
            self.active_target_id = key_def.id
            self.lbl_selected.setText(f"Selected Key: {key_def.label} ({key_def.keycode_name})")

        self._load_active_macro()

    def _on_knob_action_changed(self):
        if self.current_key and self.current_key.is_knob:
            self.active_target_id = self.knob_combo.currentData()
            self._load_active_macro()

    def _load_active_macro(self):
        remap = self.profile_manager.get_remapping(self.active_target_id)
        if not remap:
            self.status_badge.setText("No Macro (Default)")
            self.status_badge.setStyleSheet("color: #9CA3AF;")
            self.capture_box.set_keys(["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_T"])
            self._sync_modifier_buttons(["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_T"])
            self.cmd_input.clear()
            self.text_input.clear()
            self.tabs.setCurrentIndex(0)
            return

        mtype = remap.get("type")
        if mtype == "shortcut":
            keys = remap.get("keys", ["KEY_LEFTCTRL", "KEY_T"])
            readable = [k.replace("KEY_LEFT", "").replace("KEY_RIGHT", "").replace("KEY_", "") for k in keys]
            self.status_badge.setText(f"Shortcut: {'+'.join(readable)}")
            self.status_badge.setStyleSheet("color: #38BDF8;")
            self.capture_box.set_keys(keys)
            self._sync_modifier_buttons(keys)
            self.tabs.setCurrentIndex(0)
        elif mtype == "command":
            cmd = remap.get("command", "")
            self.status_badge.setText("Linux Command Assigned")
            self.status_badge.setStyleSheet("color: #10B981;")
            self.cmd_input.setText(cmd)
            self.tabs.setCurrentIndex(1)
        elif mtype == "text":
            txt = remap.get("text", "")
            self.status_badge.setText("Text Expander Assigned")
            self.status_badge.setStyleSheet("color: #F59E0B;")
            self.text_input.setText(txt)
            self.tabs.setCurrentIndex(2)
        elif mtype == "macro":
            macro_id = remap.get("macro_id")
            macro = next((m for m in self.profile_manager.get_macros() if m.get("id") == macro_id), None)
            if macro:
                self.status_badge.setText(f"Macro: {macro.get('name', macro_id)}")
                self.status_badge.setStyleSheet("color: #38BDF8;")
                if macro.get("type") == "command":
                    self.cmd_input.setText(macro.get("command", ""))
                    self.tabs.setCurrentIndex(1)
                else:
                    k = macro.get("keys", ["KEY_LEFTCTRL", "KEY_T"])
                    self.capture_box.set_keys(k)
                    self._sync_modifier_buttons(k)
                    self.tabs.setCurrentIndex(0)
        elif mtype == "key":
            target = remap.get("target", "")
            self.status_badge.setText(f"Standard Remap: {target.replace('KEY_', '')}")
            self.status_badge.setStyleSheet("color: #6366F1;")

    def _collect_current_macro(self) -> Dict[str, Any]:
        tab_idx = self.tabs.currentIndex()
        if tab_idx == 0:
            return {
                "type": "shortcut",
                "name": f"Shortcut for {self.active_target_id}",
                "keys": self.capture_box.captured_keys
            }
        elif tab_idx == 1:
            return {
                "type": "command",
                "name": f"Command for {self.active_target_id}",
                "command": self.cmd_input.text().strip()
            }
        else:
            return {
                "type": "text",
                "name": f"Text for {self.active_target_id}",
                "text": self.text_input.text()
            }

    def _save_macro(self):
        macro_data = self._collect_current_macro()
        self.profile_manager.set_remapping(self.active_target_id, macro_data)
        self.visualizer.update()
        self._load_active_macro()
        self.feedback_label.setText(f"✓ Saved {macro_data['type']} to {self.active_target_id}!")
        self.macro_changed.emit()

    def _clear_macro(self):
        self.profile_manager.clear_remap(self.active_target_id)
        self.visualizer.update()
        self._load_active_macro()
        self.feedback_label.setText("✓ Key reset to default function.")
        self.macro_changed.emit()

    def _test_macro(self):
        macro_data = self._collect_current_macro()
        self.feedback_label.setText("Running macro test...")
        self.macro_engine.run_macro_async(macro_data)
