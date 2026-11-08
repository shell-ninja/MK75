"""
Key and Rotary Knob Remapping Configuration Drawer / Panel.
Allows remapping keys to multi-key shortcuts, standard keycodes, macros, or arbitrary Linux shell commands.
Includes interactive shortcut capture, modifier toggle chips, quick media chips, and command presets.
"""

from typing import Optional, Dict, Any, List, Set
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QComboBox, QLineEdit, QFrame
)

from config.keycodes import KeyDef, REMAP_ACTION_CATEGORIES, KNOB_ACTIONS
from ui.icons import get_icon
from ui.theme import configure_dark_combobox
from ui.widgets.key_capture import (
    KeyCaptureBox, SingleKeyCaptureBox, PRESET_SHORTCUTS
)

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

# Quick Linux Command Presets
COMMAND_PRESETS = [
    ("Terminal", "kitty &"),
    ("Screenshot", "grim -g \"$(slurp)\" - | wl-copy &"),
    ("Volume +5%", "pactl set-sink-volume @DEFAULT_SINK@ +5%"),
    ("Volume -5%", "pactl set-sink-volume @DEFAULT_SINK@ -5%"),
    ("Mute Mic", "pactl set-source-mute @DEFAULT_SOURCE@ toggle"),
    ("Next Track", "playerctl next"),
]


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
        self.modifier_buttons: Dict[str, QPushButton] = {}
        self._is_loading = False

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # 1. Header Section
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Select a Key or the Knob")
        self.title_label.setObjectName("TitleLabel")
        header_layout.addWidget(self.title_label)
        header_layout.addSpacing(10)

        self.status_badge = QLabel("Default")
        self.status_badge.setObjectName("Badge")
        header_layout.addWidget(self.status_badge)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 2. Knob Action Sub-Selector (Visible only when Knob is selected)
        self.knob_selector_frame = QFrame()
        knob_layout = QHBoxLayout(self.knob_selector_frame)
        knob_layout.setContentsMargins(0, 0, 0, 0)
        knob_label = QLabel("Knob Action:")
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
        layout.addWidget(self.knob_selector_frame)
        self.knob_selector_frame.hide()

        # 3. Tabs for Remapping Type
        self.tabs = QTabWidget()

        # --- Tab 0: Shortcut (Multi-key combinations) ---
        self.tab_shortcut = QWidget()
        tab_sc_layout = QVBoxLayout(self.tab_shortcut)
        tab_sc_layout.setContentsMargins(14, 14, 14, 14)
        tab_sc_layout.setSpacing(10)

        sc_desc = QLabel("Assign a multi-key shortcut (press combination or pick from presets):")
        sc_desc.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        tab_sc_layout.addWidget(sc_desc)

        self.shortcut_capture_box = KeyCaptureBox()
        self.shortcut_capture_box.shortcut_recorded.connect(self._on_shortcut_recorded)
        self.shortcut_capture_box.modifiers_updated.connect(self._on_modifiers_updated)
        tab_sc_layout.addWidget(self.shortcut_capture_box)

        # Modifier Toggle Chips
        mod_box = QHBoxLayout()
        mod_box.setSpacing(6)
        mod_lbl = QLabel("Modifiers:")
        mod_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        mod_box.addWidget(mod_lbl)

        modifiers = [
            ("Ctrl", "KEY_LEFTCTRL"),
            ("Shift", "KEY_LEFTSHIFT"),
            ("Alt", "KEY_LEFTALT"),
            ("Super", "KEY_LEFTMETA")
        ]
        for label, mod_code in modifiers:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(
                "QPushButton { font-size: 11px; padding: 4px 10px; background: #161A26; border-radius: 4px; }"
                "QPushButton:checked { background-color: #6366F1; color: #FFFFFF; font-weight: 600; border: 1px solid #7578F8; }"
            )
            btn.clicked.connect(lambda checked, m=mod_code: self._toggle_modifier(m, checked))
            mod_box.addWidget(btn)
            self.modifier_buttons[mod_code] = btn
        mod_box.addStretch()
        tab_sc_layout.addLayout(mod_box)

        # Quick Popular Shortcuts
        presets_sc_box = QVBoxLayout()
        presets_sc_box.setSpacing(6)
        presets_sc_lbl = QLabel("Popular Shortcuts:")
        presets_sc_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        presets_sc_box.addWidget(presets_sc_lbl)

        presets_grid = QHBoxLayout()
        presets_grid.setSpacing(6)
        for label, keys in PRESET_SHORTCUTS[:5]:
            btn = QPushButton(label)
            btn.setStyleSheet("font-size: 11px; padding: 4px 8px; background: #161A26;")
            btn.clicked.connect(lambda _, k=keys: self._apply_preset_shortcut(k))
            presets_grid.addWidget(btn)
        presets_grid.addStretch()
        presets_sc_box.addLayout(presets_grid)

        presets_grid_2 = QHBoxLayout()
        presets_grid_2.setSpacing(6)
        for label, keys in PRESET_SHORTCUTS[5:]:
            btn = QPushButton(label)
            btn.setStyleSheet("font-size: 11px; padding: 4px 8px; background: #161A26;")
            btn.clicked.connect(lambda _, k=keys: self._apply_preset_shortcut(k))
            presets_grid_2.addWidget(btn)
        presets_grid_2.addStretch()
        presets_sc_box.addLayout(presets_grid_2)

        tab_sc_layout.addLayout(presets_sc_box)
        self.tabs.addTab(self.tab_shortcut, get_icon("keyboard", size=14), "Shortcut")

        # --- Tab 1: Single Key / Media Remap ---
        self.tab_key = QWidget()
        tab_key_layout = QVBoxLayout(self.tab_key)
        tab_key_layout.setContentsMargins(14, 14, 14, 14)
        tab_key_layout.setSpacing(10)

        short_desc = QLabel("Option 1: Click the box below and press any key on your keyboard to assign it directly:")
        short_desc.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        tab_key_layout.addWidget(short_desc)

        self.key_capture_box = SingleKeyCaptureBox()
        self.key_capture_box.key_captured.connect(self._on_key_captured)
        tab_key_layout.addWidget(self.key_capture_box)

        # Quick Media / Volume Chips
        media_box = QVBoxLayout()
        media_box.setSpacing(6)
        media_lbl = QLabel("Option 2: One-click media & navigation shortcuts:")
        media_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        media_box.addWidget(media_lbl)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)
        for label, code in QUICK_MEDIA_CHIPS:
            btn = QPushButton(label)
            btn.setStyleSheet("font-size: 11px; padding: 5px 10px; background: #161A26; border-radius: 6px; min-height: 26px;")
            btn.clicked.connect(lambda _, c=code: self._select_target_key(c))
            chips_row.addWidget(btn)
        chips_row.addStretch()
        media_box.addLayout(chips_row)
        tab_key_layout.addLayout(media_box)

        # Dropdown Search / Category Selector
        cat_box = QHBoxLayout()
        cat_box.setSpacing(10)
        cat_box.addWidget(QLabel("Category:"))
        self.cat_combo = QComboBox()
        configure_dark_combobox(self.cat_combo)
        for cat in REMAP_ACTION_CATEGORIES.keys():
            self.cat_combo.addItem(cat)
        self.cat_combo.currentIndexChanged.connect(self._populate_keys_combo)
        cat_box.addWidget(self.cat_combo)

        cat_box.addWidget(QLabel("Action:"))
        self.key_action_combo = QComboBox()
        configure_dark_combobox(self.key_action_combo)
        self.key_action_combo.currentIndexChanged.connect(self._on_action_combo_changed)
        cat_box.addWidget(self.key_action_combo, 1)
        tab_key_layout.addLayout(cat_box)

        self.tabs.addTab(self.tab_key, get_icon("keyboard", size=14), "Key / Media")

        # --- Tab 2: Macro Assignment ---
        self.tab_macro = QWidget()
        tab_macro_layout = QVBoxLayout(self.tab_macro)
        tab_macro_layout.setContentsMargins(14, 14, 14, 14)
        tab_macro_layout.setSpacing(10)
        tab_macro_layout.addWidget(QLabel("Select a saved macro sequence to trigger:"))
        self.macro_combo = QComboBox()
        configure_dark_combobox(self.macro_combo)
        self.macro_combo.currentIndexChanged.connect(self._on_macro_combo_changed)
        tab_macro_layout.addWidget(self.macro_combo)
        tab_macro_layout.addStretch()
        self.tabs.addTab(self.tab_macro, get_icon("macro", size=14), "Macro Sequence")

        # --- Tab 3: Linux Shell Command ---
        self.tab_command = QWidget()
        tab_cmd_layout = QVBoxLayout(self.tab_command)
        tab_cmd_layout.setContentsMargins(14, 14, 14, 14)
        tab_cmd_layout.setSpacing(10)
        tab_cmd_layout.addWidget(QLabel("Execute custom Linux shell command when pressed:"))
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("e.g. kitty & or pactl set-sink-volume @DEFAULT_SINK@ +5%")
        self.cmd_input.editingFinished.connect(self._on_command_editing_finished)
        tab_cmd_layout.addWidget(self.cmd_input)

        presets_lbl = QLabel("Quick Command Presets:")
        presets_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        tab_cmd_layout.addWidget(presets_lbl)

        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(6)
        for name, cmd in COMMAND_PRESETS:
            btn = QPushButton(name)
            btn.setStyleSheet("font-size: 11px; padding: 4px 8px; background: #161A26;")
            btn.clicked.connect(lambda _, c=cmd: self._apply_preset_command(c))
            presets_layout.addWidget(btn)
        presets_layout.addStretch()
        tab_cmd_layout.addLayout(presets_layout)
        tab_cmd_layout.addStretch()
        self.tabs.addTab(self.tab_command, get_icon("terminal", size=14), "Linux Command")

        layout.addWidget(self.tabs)

        # 4. Bottom Actions Row
        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.setIcon(get_icon("trash", normal_color="#F87171", size=14))
        self.reset_btn.setObjectName("DangerButton")
        self.reset_btn.clicked.connect(self._on_reset_remap)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()

        self.auto_save_pill = QLabel("Auto-applies immediately")
        self.auto_save_pill.setObjectName("Badge")
        self.auto_save_pill.setStyleSheet(
            "color: #10B981; background-color: #13261C; border: 1px solid #1E4D38; "
            "padding: 5px 12px; font-size: 11px; font-weight: 500; border-radius: 4px;"
        )
        btn_layout.addWidget(self.auto_save_pill)

        layout.addLayout(btn_layout)

        self._populate_keys_combo()
        self._populate_macros_combo()

    def _select_target_key(self, code: str):
        self.selected_target_key = code
        self.key_capture_box.set_key(code)
        self._sync_combo_to_key(code)
        if not self._is_loading:
            self._auto_apply_key(code)

    def _on_key_captured(self, code: str):
        self.selected_target_key = code
        self._sync_combo_to_key(code)
        if not self._is_loading:
            self._auto_apply_key(code)

    def _on_shortcut_recorded(self, keys: List[str]):
        self._sync_modifier_chips(keys)
        if not self._is_loading:
            self._auto_apply_shortcut(keys)

    def _on_modifiers_updated(self, held_mods: Set[str]):
        for mod_code, btn in self.modifier_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(mod_code in held_mods)
            btn.blockSignals(False)

    def _toggle_modifier(self, mod_code: str, active: bool):
        self.shortcut_capture_box.set_modifier_toggled(mod_code, active)

    def _apply_preset_shortcut(self, keys: List[str]):
        self.shortcut_capture_box.set_keys(keys)
        self._sync_modifier_chips(keys)
        if not self._is_loading:
            self._auto_apply_shortcut(keys)

    def _apply_preset_command(self, cmd: str):
        self.cmd_input.setText(cmd)
        if not self._is_loading:
            self._auto_apply_command(cmd)

    def _on_command_editing_finished(self):
        if not self._is_loading:
            self._auto_apply_command(self.cmd_input.text())

    def _on_macro_combo_changed(self):
        if not self._is_loading:
            macro_id = self.macro_combo.currentData()
            if macro_id:
                self._auto_apply_macro(macro_id)

    def _sync_modifier_chips(self, keys: List[str]):
        for mod_code, btn in self.modifier_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(mod_code in keys)
            btn.blockSignals(False)

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
            if not self._is_loading:
                self._auto_apply_key(code)

    def _populate_keys_combo(self):
        cat = self.cat_combo.currentText()
        items = REMAP_ACTION_CATEGORIES.get(cat, [])
        self.key_action_combo.blockSignals(True)
        self.key_action_combo.clear()
        for code, label in items:
            self.key_action_combo.addItem(f"{label} ({code})", code)
        self.key_action_combo.blockSignals(False)

    def _populate_macros_combo(self):
        self.macro_combo.blockSignals(True)
        self.macro_combo.clear()
        macros = self.profile_manager.get_macros()
        for m in macros:
            self.macro_combo.addItem(m.get("name", "Unnamed"), m.get("id"))
        self.macro_combo.blockSignals(False)

    def set_key(self, key_def: KeyDef):
        self._is_loading = True
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

        self._load_active_mapping(skip_tab=False)
        self._is_loading = False

    def _on_knob_action_changed(self):
        if self.current_key and self.current_key.is_knob:
            self._is_loading = True
            self.active_target_id = self.knob_combo.currentData()
            self._load_active_mapping(skip_tab=False)
            self._is_loading = False

    def _load_active_mapping(self, skip_tab: bool = False):
        remap = self.profile_manager.get_remapping(self.active_target_id)
        if not remap:
            self.status_badge.setText("Default")
            self.status_badge.setStyleSheet("color: #9CA3AF; background-color: #1A1F2C; border: 1px solid #283042; padding: 3px 8px; border-radius: 4px;")
            self.status_badge.adjustSize()
            default_key = self.current_key.keycode_name if (self.current_key and not self.current_key.is_knob) else "KEY_MUTE"
            self.selected_target_key = default_key
            self.key_capture_box.set_key(default_key)
            self._sync_combo_to_key(default_key)
            self.shortcut_capture_box.set_keys([], emit_signal=False)
            self._sync_modifier_chips([])
            self.cmd_input.clear()
            if not skip_tab:
                # If knob, default tab is Key/Media (tab 1); if key switch, default tab is Shortcut (tab 0)
                self.tabs.setCurrentIndex(1 if (self.current_key and self.current_key.is_knob) else 0)
            return

        remap_type = remap.get("type")
        if remap_type == "shortcut":
            keys = remap.get("keys", [])
            clean_str = " + ".join(k.replace("KEY_LEFT", "").replace("KEY_RIGHT", "").replace("KEY_", "") for k in keys)
            self.status_badge.setText(f"Shortcut: {clean_str}")
            self.status_badge.setStyleSheet("color: #38BDF8; background-color: #122538; border: 1px solid #1D4363; padding: 3px 8px; border-radius: 4px;")
            self.status_badge.adjustSize()
            if not skip_tab:
                self.tabs.setCurrentIndex(0)
            self.shortcut_capture_box.set_keys(keys)
            self._sync_modifier_chips(keys)
        elif remap_type == "key":
            target = remap.get("target")
            clean_name = target.replace("KEY_", "")
            self.status_badge.setText(f"Mapped: {clean_name}")
            self.status_badge.setStyleSheet("color: #6366F1; background-color: #1D1E3A; border: 1px solid #34376E; padding: 3px 8px; border-radius: 4px;")
            self.status_badge.adjustSize()
            if not skip_tab:
                self.tabs.setCurrentIndex(1)
            self.selected_target_key = target
            self.key_capture_box.set_key(target)
            self._sync_combo_to_key(target)
        elif remap_type == "macro":
            self.status_badge.setText("Macro Assigned")
            self.status_badge.setStyleSheet("color: #A855F7; background-color: #271638; border: 1px solid #48236A; padding: 3px 8px; border-radius: 4px;")
            self.status_badge.adjustSize()
            if not skip_tab:
                self.tabs.setCurrentIndex(2)
            macro_id = remap.get("macro_id")
            for i in range(self.macro_combo.count()):
                if self.macro_combo.itemData(i) == macro_id:
                    self.macro_combo.blockSignals(True)
                    self.macro_combo.setCurrentIndex(i)
                    self.macro_combo.blockSignals(False)
                    break
        elif remap_type == "command":
            self.status_badge.setText("Shell Command")
            self.status_badge.setStyleSheet("color: #10B981; background-color: #13261C; border: 1px solid #1E4D38; padding: 3px 8px; border-radius: 4px;")
            self.status_badge.adjustSize()
            if not skip_tab:
                self.tabs.setCurrentIndex(3)
            self.cmd_input.setText(remap.get("command", ""))

    PROTECTED_MODIFIER_KEYS = {
        "KEY_LEFTCTRL", "KEY_RIGHTCTRL", "KEY_LEFTSHIFT", "KEY_RIGHTSHIFT",
        "KEY_LEFTALT", "KEY_RIGHTALT", "KEY_LEFTMETA", "KEY_RIGHTMETA"
    }

    def _auto_apply_shortcut(self, keys: List[str]):
        if not keys or not self.active_target_id:
            return
        if self.active_target_id in self.PROTECTED_MODIFIER_KEYS:
            return
        self.profile_manager.set_remapping(self.active_target_id, {
            "type": "shortcut",
            "name": f"Shortcut for {self.active_target_id}",
            "keys": list(keys)
        })
        self._load_active_mapping(skip_tab=True)
        self.remap_changed.emit()

    def _auto_apply_key(self, code: str):
        if not code or not self.active_target_id:
            return
        if self.active_target_id in self.PROTECTED_MODIFIER_KEYS:
            return
        self.profile_manager.set_key_remap(self.active_target_id, code)
        self._load_active_mapping(skip_tab=True)
        self.remap_changed.emit()

    def _auto_apply_macro(self, macro_id: str):
        if not macro_id or not self.active_target_id:
            return
        if self.active_target_id in self.PROTECTED_MODIFIER_KEYS:
            return
        self.profile_manager.set_macro_remap(self.active_target_id, macro_id)
        self._load_active_mapping(skip_tab=True)
        self.remap_changed.emit()

    def _auto_apply_command(self, cmd: str):
        if not self.active_target_id:
            return
        if self.active_target_id in self.PROTECTED_MODIFIER_KEYS:
            return
        cmd = cmd.strip()
        if cmd:
            self.profile_manager.set_command_remap(self.active_target_id, cmd)
        else:
            self.profile_manager.clear_remap(self.active_target_id)
        self._load_active_mapping(skip_tab=True)
        self.remap_changed.emit()

    def _on_reset_remap(self):
        self.profile_manager.clear_remap(self.active_target_id)
        self._load_active_mapping(skip_tab=True)
        self.remap_changed.emit()
