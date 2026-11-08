"""
Interactive Keybindings & Macro Builder for Lingbao MK75.
Provides a modern multi-modifier combo selector (Super, Ctrl, Alt, Shift + Key)
and dispatchers for Linux applications, shell commands, virtual shortcuts, and text snippets.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Set

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QKeyEvent, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QPlainTextEdit, QFrame, QScrollArea, QStackedWidget,
    QMessageBox, QDialog
)

from core.macro_engine import MacroEngine
from ui.icons import get_icon, render_svg_pixmap
from ui.theme import (
    BG_MAIN, BG_SURFACE, BG_CARD, BG_INPUT, BORDER_COLOR, ACCENT_PRIMARY, ACCENT_SKY,
    ACCENT_EMERALD, ACCENT_ROSE, ACCENT_AMBER, TEXT_PRIMARY, TEXT_MUTED
)

logger = logging.getLogger("MK75.MacrosView")

# Standard Linux App & System Presets
PRESET_COMMANDS = [
    ("Terminal (kitty)", "kitty &"),
    ("Screenshot", "grim -g \"$(slurp)\" - | wl-copy &"),
    ("App Launcher", "rofi -show drun"),
    ("Browser", "brave &"),
    ("File Manager", "xdg-open ~ &"),
    ("Mute Mic", "pactl set-source-mute @DEFAULT_SOURCE@ toggle"),
    ("Lock Session", "loginctl lock-session"),
]

PRESET_SHORTCUTS = [
    ("Copy", ["KEY_LEFTCTRL", "KEY_C"]),
    ("Paste", ["KEY_LEFTCTRL", "KEY_V"]),
    ("Undo", ["KEY_LEFTCTRL", "KEY_Z"]),
    ("New Tab", ["KEY_LEFTCTRL", "KEY_T"]),
    ("Close Tab", ["KEY_LEFTCTRL", "KEY_W"]),
    ("Close Window", ["KEY_LEFTALT", "KEY_F4"]),
]

QUICK_KEYS = [
    "Return", "Space", "Tab", "Escape", "K", "H", "W", "Q", "E",
    "R", "T", "B", "D", "A", "1", "Delete"
]

MODIFIER_OPTIONS = ["SUPER", "CTRL", "ALT", "SHIFT"]


def normalize_macro_dict(macro: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures a macro has valid trigger and action dictionaries."""
    data = dict(macro)
    if "trigger" not in data or not isinstance(data["trigger"], dict):
        mid = data.get("id", "")
        if "keys" in data:
            keys = data.get("keys", [])
            mods = []
            non_mod = None
            for k in keys:
                if "CTRL" in k:
                    mods.append("CTRL")
                elif "SHIFT" in k:
                    mods.append("SHIFT")
                elif "ALT" in k:
                    mods.append("ALT")
                elif "META" in k or "SUPER" in k:
                    mods.append("SUPER")
                else:
                    non_mod = k.replace("KEY_", "")
            if not mods:
                mods = ["CTRL", "SHIFT"]
            if not non_mod:
                non_mod = "K"
            data["trigger"] = {"modifiers": mods, "key": non_mod}
        elif mid == "macro_term":
            data["trigger"] = {"modifiers": ["CTRL", "SHIFT"], "key": "K"}
        elif mid == "macro_mute_mic":
            data["trigger"] = {"modifiers": ["SUPER"], "key": "M"}
        else:
            data["trigger"] = {"modifiers": ["SUPER"], "key": "K"}

    if "action" not in data or not isinstance(data["action"], dict):
        mtype = data.get("type", "command")
        action = {"type": mtype}
        if mtype == "command":
            action["command"] = data.get("command", "")
        elif mtype == "shortcut":
            action["keys"] = data.get("keys", [])
        elif mtype == "text":
            action["text"] = data.get("text", "")
        data["action"] = action

    return data


class MacroEditorDialog(QDialog):
    """
    Modern modal dialog to configure multi-modifier keybindings:
    SUPER, CTRL, ALT, SHIFT + Key -> Linux Command, Shortcut, or Text.
    """

    def __init__(self, macro_engine: MacroEngine, existing_macro: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.macro_engine = macro_engine
        self.existing_macro = existing_macro

        self.selected_modifiers: Set[str] = set()
        self.selected_key: str = "K"
        self.action_type: str = "command"
        self.is_recording: bool = False

        self._mod_buttons: Dict[str, QPushButton] = {}

        self.setWindowTitle("Edit Keybinding" if existing_macro else "Add New Keybinding")
        self.setMinimumWidth(680)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_MAIN};
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
            }}
            QLabel {{
                color: {TEXT_PRIMARY};
            }}
            QLineEdit, QPlainTextEdit {{
                background-color: #121622;
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 8px 12px;
                color: #FFFFFF;
                font-size: 13px;
            }}
            QLineEdit:focus, QPlainTextEdit:focus {{
                border: 1px solid {ACCENT_SKY};
            }}
        """)

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 1. Header with Close Button
        header_box = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(2)

        title = QLabel("Edit Keybinding" if self.existing_macro else "Add New Keybinding")
        title.setStyleSheet("font-size: 17px; font-weight: 700; color: #FFFFFF;")
        subtitle = QLabel("Hold any combination of Super, Ctrl, Alt, Shift and assign an action.")
        subtitle.setStyleSheet("font-size: 12px; color: #9CA3AF;")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_box.addLayout(header_text)
        header_box.addStretch()

        close_btn = QPushButton()
        close_btn.setIcon(get_icon("cross", normal_color="#E2E8F0", size=12))
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #171C2B;
                border: 1px solid #283144;
                border-radius: 14px;
            }
            QPushButton:hover {
                background: #252D3F;
                border-color: #38BDF8;
            }
        """)
        close_btn.clicked.connect(self.reject)
        header_box.addWidget(close_btn)
        layout.addLayout(header_box)

        # 2. Section 1: Key Combination
        sec1_lbl = QLabel("1. Key Combination (Hold any combination of Super, Ctrl, Alt, Shift)")
        sec1_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #38BDF8;")
        layout.addWidget(sec1_lbl)

        # Combination Banner Card
        banner = QFrame()
        banner.setObjectName("BannerCard")
        banner.setStyleSheet("""
            QFrame#BannerCard {
                background-color: #121624;
                border: 1px solid #232B3E;
                border-radius: 10px;
            }
        """)
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(16, 12, 16, 12)
        banner_layout.setSpacing(14)

        kb_icon_lbl = QLabel()
        kb_icon_lbl.setPixmap(render_svg_pixmap("keyboard", color="#38BDF8", size=24))
        banner_layout.addWidget(kb_icon_lbl)

        combo_text_box = QVBoxLayout()
        combo_text_box.setSpacing(2)
        self.combo_label = QLabel("Assigned Combination: SUPER")
        self.combo_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        combo_sub = QLabel("Supports any combination of SUPER, CTRL, ALT, and SHIFT")
        combo_sub.setStyleSheet("font-size: 11px; color: #9CA3AF;")
        combo_text_box.addWidget(self.combo_label)
        combo_text_box.addWidget(combo_sub)
        banner_layout.addLayout(combo_text_box)
        banner_layout.addStretch()

        self.record_btn = QPushButton(" Record Shortcut")
        self.record_btn.setIcon(get_icon("record", normal_color="#38BDF8", size=14))
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #182234;
                border: 1px solid #0284C7;
                color: #38BDF8;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0284C7;
                color: #FFFFFF;
            }
        """)
        self.record_btn.clicked.connect(self._toggle_recording)
        banner_layout.addWidget(self.record_btn)
        layout.addWidget(banner)

        # Modifiers Row
        mod_row = QHBoxLayout()
        mod_row.setSpacing(8)
        mod_lbl = QLabel("Modifiers:")
        mod_lbl.setStyleSheet("font-weight: 600; font-size: 12px; color: #9CA3AF; min-width: 65px;")
        mod_row.addWidget(mod_lbl)

        for mod in MODIFIER_OPTIONS:
            btn = QPushButton(mod)
            btn.setCheckable(True)
            btn.setFixedSize(85, 32)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #161A26;
                    border: 1px solid #262E40;
                    border-radius: 6px;
                    color: #9CA3AF;
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: #1F2536;
                    color: #E2E8F0;
                }}
                QPushButton:checked {{
                    background-color: #0284C7;
                    border: 1px solid #38BDF8;
                    color: #FFFFFF;
                    font-weight: 700;
                }}
            """)
            btn.toggled.connect(lambda checked, m=mod: self._on_mod_toggled(m, checked))
            self._mod_buttons[mod] = btn
            mod_row.addWidget(btn)
        mod_row.addStretch()
        layout.addLayout(mod_row)

        # Key Input & Quick Pills Row
        key_row = QHBoxLayout()
        key_row.setSpacing(8)
        key_lbl = QLabel("Key:")
        key_lbl.setStyleSheet("font-weight: 600; font-size: 12px; color: #9CA3AF; min-width: 65px;")
        key_row.addWidget(key_lbl)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("e.g. Return, Q, H, Space...")
        self.key_input.setFixedWidth(140)
        self.key_input.textChanged.connect(self._on_key_input_changed)
        key_row.addWidget(self.key_input)

        # Quick Key Pills (Scrollable with hidden scrollbar)
        quick_scroll = QScrollArea()
        quick_scroll.setWidgetResizable(True)
        quick_scroll.setFixedHeight(34)
        quick_scroll.setFrameShape(QFrame.NoFrame)
        quick_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        quick_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        quick_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollBar { height: 0px; width: 0px; }")

        quick_widget = QWidget()
        quick_widget.setStyleSheet("background: transparent; border: none;")
        quick_layout = QHBoxLayout(quick_widget)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(5)

        for qk in QUICK_KEYS:
            qbtn = QPushButton(qk)
            qbtn.setStyleSheet("""
                QPushButton {
                    background-color: #151924;
                    border: 1px solid #252D3F;
                    border-radius: 5px;
                    color: #CBD5E1;
                    padding: 3px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #242D40;
                    color: #38BDF8;
                    border-color: #38BDF8;
                }
            """)
            qbtn.clicked.connect(lambda _, k=qk: self.key_input.setText(k))
            quick_layout.addWidget(qbtn)
        quick_layout.addStretch()
        quick_scroll.setWidget(quick_widget)
        key_row.addWidget(quick_scroll, 1)

        layout.addLayout(key_row)

        # 3. Section 2: Action Type
        sec2_lbl = QLabel("2. Action Type")
        sec2_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #38BDF8; margin-top: 4px;")
        layout.addWidget(sec2_lbl)

        # Action Type Segmented Buttons
        seg_box = QHBoxLayout()
        seg_box.setSpacing(6)
        self.btn_action_cmd = QPushButton("Launch Command")
        self.btn_action_cmd.setCheckable(True)
        self.btn_action_sc = QPushButton("Send Shortcut")
        self.btn_action_sc.setCheckable(True)
        self.btn_action_txt = QPushButton("Auto-Type Text")
        self.btn_action_txt.setCheckable(True)

        for btn in (self.btn_action_cmd, self.btn_action_sc, self.btn_action_txt):
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #161A26;
                    border: 1px solid #262E40;
                    border-radius: 6px;
                    padding: 7px 16px;
                    color: #9CA3AF;
                    font-weight: 600;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #1F2536;
                    color: #FFFFFF;
                }
                QPushButton:checked {
                    background-color: #1E293B;
                    border: 1px solid #38BDF8;
                    color: #38BDF8;
                    font-weight: 700;
                }
            """)

        self.btn_action_cmd.clicked.connect(lambda: self._set_action_mode("command"))
        self.btn_action_sc.clicked.connect(lambda: self._set_action_mode("shortcut"))
        self.btn_action_txt.clicked.connect(lambda: self._set_action_mode("text"))

        seg_box.addWidget(self.btn_action_cmd)
        seg_box.addWidget(self.btn_action_sc)
        seg_box.addWidget(self.btn_action_txt)
        seg_box.addStretch()
        layout.addLayout(seg_box)

        # Stacked Action Configuration Pages
        self.action_stack = QStackedWidget()

        # Page 0: Launch Command
        p_cmd = QWidget()
        p_cmd_layout = QVBoxLayout(p_cmd)
        p_cmd_layout.setContentsMargins(0, 6, 0, 0)
        p_cmd_layout.setSpacing(8)

        cmd_title = QLabel("Command / Application to Run:")
        cmd_title.setStyleSheet("font-size: 12px; color: #9CA3AF;")
        p_cmd_layout.addWidget(cmd_title)

        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("e.g. kitty, brave, rofi -show drun, pactl set-sink-mute @DEFAULT_SINK@ toggle...")
        self.cmd_input.textChanged.connect(self._update_live_preview)
        p_cmd_layout.addWidget(self.cmd_input)

        cmd_presets_box = QHBoxLayout()
        cmd_presets_box.setSpacing(6)
        pres_lbl = QLabel("Presets:")
        pres_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        cmd_presets_box.addWidget(pres_lbl)

        for name, cmd in PRESET_COMMANDS:
            pbtn = QPushButton(name)
            pbtn.setStyleSheet("""
                QPushButton {
                    background-color: #141724;
                    border: 1px solid #232838;
                    border-radius: 5px;
                    color: #94A3B8;
                    padding: 3px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #232B3E;
                    color: #FFFFFF;
                }
            """)
            pbtn.clicked.connect(lambda _, c=cmd: self.cmd_input.setText(c))
            cmd_presets_box.addWidget(pbtn)
        cmd_presets_box.addStretch()
        p_cmd_layout.addLayout(cmd_presets_box)
        self.action_stack.addWidget(p_cmd)

        # Page 1: Send Shortcut
        p_sc = QWidget()
        p_sc_layout = QVBoxLayout(p_sc)
        p_sc_layout.setContentsMargins(0, 6, 0, 0)
        p_sc_layout.setSpacing(8)

        sc_title = QLabel("Shortcut to Dispatch (virtual keystrokes):")
        sc_title.setStyleSheet("font-size: 12px; color: #9CA3AF;")
        p_sc_layout.addWidget(sc_title)

        self.shortcut_input = QLineEdit()
        self.shortcut_input.setPlaceholderText("e.g. KEY_LEFTCTRL + KEY_V")
        self.shortcut_input.textChanged.connect(self._update_live_preview)
        p_sc_layout.addWidget(self.shortcut_input)

        sc_presets_box = QHBoxLayout()
        sc_presets_box.setSpacing(6)
        sc_pres_lbl = QLabel("Presets:")
        sc_pres_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        sc_presets_box.addWidget(sc_pres_lbl)

        for name, keys in PRESET_SHORTCUTS:
            pbtn = QPushButton(name)
            pbtn.setStyleSheet("""
                QPushButton {
                    background-color: #141724;
                    border: 1px solid #232838;
                    border-radius: 5px;
                    color: #94A3B8;
                    padding: 3px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #232B3E;
                    color: #FFFFFF;
                }
            """)
            pbtn.clicked.connect(lambda _, k=keys: self.shortcut_input.setText(" + ".join(k)))
            sc_presets_box.addWidget(pbtn)
        sc_presets_box.addStretch()
        p_sc_layout.addLayout(sc_presets_box)
        self.action_stack.addWidget(p_sc)

        # Page 2: Auto-Type Text
        p_txt = QWidget()
        p_txt_layout = QVBoxLayout(p_txt)
        p_txt_layout.setContentsMargins(0, 6, 0, 0)
        p_txt_layout.setSpacing(8)

        txt_title = QLabel("Text to Automatically Type:")
        txt_title.setStyleSheet("font-size: 12px; color: #9CA3AF;")
        p_txt_layout.addWidget(txt_title)

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("e.g. echo 'Hello from MK75' or snippet...")
        self.text_input.textChanged.connect(self._update_live_preview)
        p_txt_layout.addWidget(self.text_input)
        self.action_stack.addWidget(p_txt)

        layout.addWidget(self.action_stack)

        # 4. Section 3: Live Action Statement
        sec3_lbl = QLabel("3. Live Action Statement:")
        sec3_lbl.setStyleSheet("font-weight: 600; font-size: 12px; color: #9CA3AF; margin-top: 4px;")
        layout.addWidget(sec3_lbl)

        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet("""
            QFrame {
                background-color: #0E121B;
                border: 1px solid #1E2536;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        pf_layout = QHBoxLayout(self.preview_frame)
        pf_layout.setContentsMargins(12, 8, 12, 8)

        self.preview_lbl = QLabel("Trigger: [ CTRL + SHIFT + K ]  ➔  Action: Launch 'kitty &'")
        self.preview_lbl.setStyleSheet("font-family: monospace; font-size: 13px; color: #38BDF8; font-weight: 600;")
        pf_layout.addWidget(self.preview_lbl)
        layout.addWidget(self.preview_frame)

        # 5. Buttons Row
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #171B26;
                border: 1px solid #2B3346;
                border-radius: 6px;
                padding: 8px 18px;
                color: #9CA3AF;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #232B3E;
                color: #FFFFFF;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        self.save_btn = QPushButton("Save Changes" if self.existing_macro else "Save to Apply")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                border: 1px solid #38BDF8;
                border-radius: 6px;
                padding: 8px 22px;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self.save_btn.clicked.connect(self._on_save_clicked)
        btn_box.addWidget(self.save_btn)

        layout.addLayout(btn_box)

    def _load_data(self):
        if self.existing_macro:
            macro = normalize_macro_dict(self.existing_macro)
            trigger = macro.get("trigger", {})
            mods = trigger.get("modifiers", [])
            for m in mods:
                if m in self._mod_buttons:
                    self._mod_buttons[m].setChecked(True)
            self.selected_modifiers = set(mods)

            key = trigger.get("key", "K")
            clean_key = key[4:] if key.startswith("KEY_") else key
            self.key_input.setText(clean_key)

            action = macro.get("action", {})
            act_type = action.get("type", "command")
            self._set_action_mode(act_type)

            if act_type == "command":
                self.cmd_input.setText(action.get("command", ""))
            elif act_type == "shortcut":
                keys = action.get("keys", [])
                self.shortcut_input.setText(" + ".join(keys))
            elif act_type == "text":
                self.text_input.setText(action.get("text", ""))
        else:
            # Defaults
            self._mod_buttons["CTRL"].setChecked(True)
            self._mod_buttons["SHIFT"].setChecked(True)
            self.selected_modifiers = {"CTRL", "SHIFT"}
            self.key_input.setText("K")
            self._set_action_mode("command")
            self.cmd_input.setText("kitty &")

        self._update_combination_banner()
        self._update_live_preview()

    def _on_mod_toggled(self, mod: str, checked: bool):
        if checked:
            self.selected_modifiers.add(mod)
        else:
            self.selected_modifiers.discard(mod)
        self._update_combination_banner()
        self._update_live_preview()

    def _on_key_input_changed(self, text: str):
        self.selected_key = text.strip()
        self._update_combination_banner()
        self._update_live_preview()

    def _set_action_mode(self, mode: str):
        self.action_type = mode
        self.btn_action_cmd.setChecked(mode == "command")
        self.btn_action_sc.setChecked(mode == "shortcut")
        self.btn_action_txt.setChecked(mode == "text")

        if mode == "command":
            self.action_stack.setCurrentIndex(0)
        elif mode == "shortcut":
            self.action_stack.setCurrentIndex(1)
        elif mode == "text":
            self.action_stack.setCurrentIndex(2)

        self._update_live_preview()

    def _update_combination_banner(self):
        # Order modifiers cleanly: SUPER, CTRL, ALT, SHIFT
        ordered_mods = [m for m in MODIFIER_OPTIONS if m in self.selected_modifiers]
        key_str = self.selected_key.upper() if self.selected_key else "..."

        if ordered_mods:
            combo_str = " + ".join(ordered_mods) + f" + {key_str}"
        else:
            combo_str = key_str

        self.combo_label.setText(f"Assigned Combination: {combo_str}")

    def _update_live_preview(self):
        ordered_mods = [m for m in MODIFIER_OPTIONS if m in self.selected_modifiers]
        key_str = self.selected_key.upper() if self.selected_key else "?"
        combo_str = " + ".join(ordered_mods + ([key_str] if key_str else []))

        if self.action_type == "command":
            cmd = self.cmd_input.text().strip() or "kitty &"
            act_desc = f"Launch '{cmd}'"
        elif self.action_type == "shortcut":
            sc = self.shortcut_input.text().strip() or "KEY_LEFTCTRL + KEY_V"
            act_desc = f"Dispatch Shortcut [ {sc} ]"
        else:
            txt = self.text_input.text().strip() or "text snippet"
            act_desc = f"Auto-Type '{txt}'"

        self.preview_lbl.setText(f"Trigger: [ {combo_str} ]  ➔  Action: {act_desc}")

    def _toggle_recording(self):
        self.is_recording = not self.is_recording
        if self.is_recording:
            self.record_btn.setText(" Listening... Press combination")
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0284C7;
                    border: 1px solid #38BDF8;
                    color: #FFFFFF;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-weight: 700;
                    font-size: 12px;
                }
            """)
        else:
            self.record_btn.setText(" Record Shortcut")
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background-color: #182234;
                    border: 1px solid #0284C7;
                    color: #38BDF8;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-weight: 600;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #0284C7;
                    color: #FFFFFF;
                }
            """)

    def keyPressEvent(self, event: QKeyEvent):
        if not self.is_recording:
            super().keyPressEvent(event)
            return

        qt_key = event.key()

        # Update modifier states on physical modifier press
        if qt_key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            if qt_key == Qt.Key_Control:
                self._mod_buttons["CTRL"].setChecked(True)
            elif qt_key == Qt.Key_Shift:
                self._mod_buttons["SHIFT"].setChecked(True)
            elif qt_key == Qt.Key_Alt:
                self._mod_buttons["ALT"].setChecked(True)
            elif qt_key == Qt.Key_Meta:
                self._mod_buttons["SUPER"].setChecked(True)
            event.accept()
            return

        # It's a standard key: capture key text
        key_name = event.text().strip()
        if not key_name or ord(key_name[0]) < 32:
            # Special keys like Return, Space, Tab
            special_map = {
                Qt.Key_Return: "Return",
                Qt.Key_Enter: "Return",
                Qt.Key_Space: "Space",
                Qt.Key_Tab: "Tab",
                Qt.Key_Escape: "Escape",
                Qt.Key_Delete: "Delete",
                Qt.Key_Backspace: "Backspace"
            }
            key_name = special_map.get(qt_key, chr(qt_key) if qt_key < 128 else "K")

        self.key_input.setText(key_name.upper())
        self._toggle_recording()
        event.accept()

    def _on_save_clicked(self):
        if not self.selected_key:
            QMessageBox.warning(self, "Missing Key", "Please enter or select a key for the shortcut combination.")
            return

        if self.action_type == "command" and not self.cmd_input.text().strip():
            QMessageBox.warning(self, "Missing Command", "Please provide a Linux command or application to execute.")
            return
        elif self.action_type == "shortcut":
            sc_text = self.shortcut_input.text().strip()
            if not sc_text:
                QMessageBox.warning(self, "Missing Shortcut", "Please provide keycodes for the shortcut to dispatch.")
                return

            # Check for circular self-binding (e.g. Trigger CTRL+V -> Action Ctrl+V or CTRL+C -> Ctrl+C)
            sc_raw = sc_text.upper()
            ordered_mods = [m for m in MODIFIER_OPTIONS if m in self.selected_modifiers]
            clean_k = self.selected_key.strip().upper()
            if ordered_mods == ["CTRL"] and clean_k in ("C", "V", "X", "Z", "A"):
                if f"KEY_{clean_k}" in sc_raw and "CTRL" in sc_raw and "SHIFT" not in sc_raw and "ALT" not in sc_raw:
                    QMessageBox.information(
                        self,
                        "Native Shortcut",
                        f"CTRL + {clean_k} is already your operating system's native shortcut (Copy/Paste/Undo/Select).\n\n"
                        "You do not need to bind it to itself — standard shortcuts work out of the box!"
                    )
                    return
        elif self.action_type == "text" and not self.text_input.text().strip():
            QMessageBox.warning(self, "Missing Text", "Please provide text snippet to type.")
            return

        self.accept()

    def get_macro_data(self) -> Dict[str, Any]:
        """Constructs clean macro dictionary with combo trigger and action definition."""
        ordered_mods = [m for m in MODIFIER_OPTIONS if m in self.selected_modifiers]
        clean_key = self.selected_key.strip().upper()
        if not clean_key.startswith("KEY_"):
            # Map common special keys
            name_map = {
                "RETURN": "KEY_ENTER",
                "ENTER": "KEY_ENTER",
                "SPACE": "KEY_SPACE",
                "TAB": "KEY_TAB",
                "ESCAPE": "KEY_ESC",
                "ESC": "KEY_ESC",
                "DELETE": "KEY_DELETE",
                "DEL": "KEY_DELETE",
                "BACKSPACE": "KEY_BACKSPACE",
            }
            canonical_key = name_map.get(clean_key, f"KEY_{clean_key}")
        else:
            canonical_key = clean_key

        macro_id = self.existing_macro.get("id") if self.existing_macro else f"macro_{int(time.time() * 1000)}"

        # Friendly name
        combo_str = " + ".join(ordered_mods + [clean_key])
        if self.action_type == "command":
            cmd = self.cmd_input.text().strip()
            name = f"Run {cmd.split()[0]}"
            action_dict = {"type": "command", "command": cmd}
        elif self.action_type == "shortcut":
            raw_keys = [k.strip() for k in self.shortcut_input.text().replace("+", " ").split() if k.strip()]
            name = f"Shortcut {combo_str}"
            action_dict = {"type": "shortcut", "keys": raw_keys}
        else:
            txt = self.text_input.text().strip()
            name = f"Type '{txt[:15]}...'"
            action_dict = {"type": "text", "text": txt}

        macro_data = {
            "id": macro_id,
            "name": self.existing_macro.get("name", name) if self.existing_macro else name,
            "type": self.action_type,
            "trigger": {
                "modifiers": ordered_mods,
                "key": canonical_key
            },
            "action": action_dict
        }

        # Flat aliases for backwards compatibility
        if self.action_type == "command":
            macro_data["command"] = self.cmd_input.text().strip()
        elif self.action_type == "shortcut":
            macro_data["keys"] = action_dict["keys"]
        elif self.action_type == "text":
            macro_data["text"] = action_dict["text"]

        return macro_data


class MacrosView(QWidget):
    """
    Keybindings & Macros Page for Lingbao MK75.
    Lists active keybindings and provides the "+ Add Keybind" builder dialog.
    """

    macro_changed = Signal()

    def __init__(self, profile_manager, macro_engine: MacroEngine, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.macro_engine = macro_engine

        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 20, 24, 20)
        root_layout.setSpacing(16)

        # 1. Top Header with Title and "+ Add Keybind" Button
        header_box = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(3)

        title = QLabel("Keybindings & Macros")
        title.setObjectName("TitleLabel")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #FFFFFF;")

        subtitle = QLabel("Assign multi-modifier shortcuts (e.g. CTRL + SHIFT + K) to launch Linux applications, run shell commands, or trigger macros.")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setStyleSheet("font-size: 12px; color: #9CA3AF;")

        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_box.addLayout(header_text)
        header_box.addStretch()

        self.add_keybind_btn = QPushButton(" + Add Keybind")
        self.add_keybind_btn.setIcon(get_icon("plus", normal_color="#FFFFFF", size=14))
        self.add_keybind_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                border: 1px solid #38BDF8;
                border-radius: 8px;
                padding: 10px 20px;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self.add_keybind_btn.clicked.connect(self._open_add_dialog)
        header_box.addWidget(self.add_keybind_btn)
        root_layout.addLayout(header_box)

        # 2. Search / Count Filter Bar
        bar_frame = QFrame()
        bar_frame.setStyleSheet("""
            QFrame {
                background-color: #121622;
                border: 1px solid #232B3E;
                border-radius: 8px;
                padding: 6px 12px;
            }
        """)
        bar_layout = QHBoxLayout(bar_frame)
        bar_layout.setContentsMargins(4, 2, 4, 2)
        bar_layout.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter keybindings by combination or command...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-size: 12px;
            }
        """)
        self.search_input.textChanged.connect(self._on_filter_changed)
        bar_layout.addWidget(self.search_input, 1)

        self.count_badge = QLabel("0 Keybindings")
        self.count_badge.setStyleSheet("color: #38BDF8; font-weight: 600; font-size: 11px;")
        bar_layout.addWidget(self.count_badge)

        root_layout.addWidget(bar_frame)

        # 3. Scrollable List of Keybindings
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)

        self.scroll_area.setWidget(self.cards_container)
        root_layout.addWidget(self.scroll_area, 1)

    def refresh_list(self):
        """Rebuilds the list of active keybinding cards."""
        # Cleanly unparent and delete existing items
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        raw_macros = self.profile_manager.get_macros()
        search_query = self.search_input.text().strip().lower()

        count = 0
        for macro in raw_macros:
            norm = normalize_macro_dict(macro)
            trigger = norm.get("trigger", {})
            action = norm.get("action", {})

            mods = trigger.get("modifiers", [])
            key = trigger.get("key", "")
            clean_key = key[4:] if key.startswith("KEY_") else key

            combo_display = " + ".join(mods + [clean_key])
            act_type = action.get("type", "command").upper()
            detail = action.get("command", "") or " + ".join(action.get("keys", [])) or action.get("text", "")

            # Filter check
            if search_query and (search_query not in combo_display.lower() and search_query not in detail.lower()):
                continue

            card = self._create_keybind_card(norm, combo_display, act_type, detail)
            self.cards_layout.addWidget(card)
            count += 1

        self.count_badge.setText(f"{count} Active Keybinding{'s' if count != 1 else ''}")

        if count == 0 and not search_query:
            self._show_empty_state()

        self.cards_layout.addStretch()

    def _create_keybind_card(self, macro: Dict[str, Any], combo_display: str, act_type: str, detail: str) -> QFrame:
        card = QFrame()
        card.setObjectName("KeybindCard")
        card.setStyleSheet("""
            QFrame#KeybindCard {
                background-color: #131724;
                border: 1px solid #232B3E;
                border-radius: 10px;
            }
            QFrame#KeybindCard:hover {
                border-color: #38BDF8;
                background-color: #161B2B;
            }
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(16)

        # Trigger Pills Layout
        trigger_box = QHBoxLayout()
        trigger_box.setSpacing(5)

        trigger_parts = combo_display.split(" + ")
        for i, part in enumerate(trigger_parts):
            pill = QLabel(part)
            pill.setObjectName("KeycapPill")
            pill.setStyleSheet("""
                QLabel#KeycapPill {
                    background-color: #1A2234;
                    border: 1px solid #2B3852;
                    border-radius: 5px;
                    padding: 4px 10px;
                    color: #38BDF8;
                    font-weight: 700;
                    font-size: 12px;
                }
            """)
            trigger_box.addWidget(pill)
            if i < len(trigger_parts) - 1:
                plus = QLabel("+")
                plus.setStyleSheet("background: transparent; border: none; color: #64748B; font-weight: bold; font-size: 12px;")
                trigger_box.addWidget(plus)

        layout.addLayout(trigger_box)

        # Arrow
        arrow = QLabel("➔")
        arrow.setStyleSheet("background: transparent; border: none; color: #64748B; font-size: 15px; font-weight: bold;")
        layout.addWidget(arrow)

        # Action Details
        act_box = QVBoxLayout()
        act_box.setSpacing(4)

        top_act_row = QHBoxLayout()
        top_act_row.setSpacing(8)

        # Badge color by type
        if act_type == "COMMAND":
            badge_bg, badge_fg = "#312E81", "#818CF8"
        elif act_type == "SHORTCUT":
            badge_bg, badge_fg = "#064E3B", "#34D399"
        else:
            badge_bg, badge_fg = "#78350F", "#FBBF24"

        type_badge = QLabel(act_type)
        type_badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_fg};
            border-radius: 4px;
            padding: 2px 7px;
            font-size: 10px;
            font-weight: 700;
            border: none;
        """)
        top_act_row.addWidget(type_badge)

        name_lbl = QLabel(macro.get("name", "Keybinding"))
        name_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #FFFFFF; background: transparent; border: none;")
        top_act_row.addWidget(name_lbl)
        top_act_row.addStretch()
        act_box.addLayout(top_act_row)

        detail_lbl = QLabel(detail)
        detail_lbl.setStyleSheet("""
            background-color: #0E121B;
            border: 1px solid #1E2536;
            border-radius: 5px;
            padding: 4px 8px;
            font-family: monospace;
            font-size: 11px;
            color: #94A3B8;
        """)
        act_box.addWidget(detail_lbl)

        layout.addLayout(act_box, 1)

        # Action Buttons: Test, Edit, Delete
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        test_btn = QPushButton(" Test")
        test_btn.setIcon(get_icon("play", normal_color="#10B981", size=13))
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #142423;
                border: 1px solid #065F46;
                border-radius: 6px;
                padding: 6px 12px;
                color: #34D399;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #065F46;
                color: #FFFFFF;
            }
        """)
        test_btn.clicked.connect(lambda _, m=macro, b=test_btn: self._test_macro(m, b))
        btn_row.addWidget(test_btn)

        edit_btn = QPushButton(" Edit")
        edit_btn.setIcon(get_icon("edit", normal_color="#9CA3AF", size=13))
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #171C2B;
                border: 1px solid #283144;
                border-radius: 6px;
                padding: 6px 12px;
                color: #9CA3AF;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #232B3E;
                color: #FFFFFF;
                border-color: #38BDF8;
            }
        """)
        edit_btn.clicked.connect(lambda _, m=macro: self._open_edit_dialog(m))
        btn_row.addWidget(edit_btn)

        del_btn = QPushButton()
        del_btn.setIcon(get_icon("trash", normal_color="#F43F5E", size=13))
        del_btn.setFixedSize(32, 30)
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: #22151C;
                border: 1px solid #4C1D2D;
                border-radius: 6px;
                color: #F43F5E;
            }
            QPushButton:hover {
                background-color: #9F1239;
                color: #FFFFFF;
            }
        """)
        del_btn.clicked.connect(lambda _, mid=macro.get("id"): self._delete_macro(mid))
        btn_row.addWidget(del_btn)

        layout.addLayout(btn_row)
        return card

    def _show_empty_state(self):
        empty_card = QFrame()
        empty_card.setStyleSheet("""
            QFrame {
                background-color: #121520;
                border: 1px dashed #242B3C;
                border-radius: 12px;
                padding: 40px;
            }
        """)
        empty_layout = QVBoxLayout(empty_card)
        empty_layout.setSpacing(12)
        empty_layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setPixmap(render_svg_pixmap("keyboard", color="#64748B", size=48))
        empty_layout.addWidget(icon_lbl)

        txt = QLabel("No Keybindings Configured")
        txt.setAlignment(Qt.AlignCenter)
        txt.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        empty_layout.addWidget(txt)

        sub = QLabel("Assign multi-modifier combinations like CTRL + SHIFT + K to execute Linux commands or shortcuts.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        empty_layout.addWidget(sub)

        create_btn = QPushButton(" + Add Your First Keybind")
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                border: 1px solid #38BDF8;
                border-radius: 8px;
                padding: 10px 22px;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 13px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        create_btn.clicked.connect(self._open_add_dialog)
        empty_layout.addWidget(create_btn, alignment=Qt.AlignCenter)

        self.cards_layout.insertWidget(0, empty_card)

    def _open_add_dialog(self):
        dialog = MacroEditorDialog(self.macro_engine, existing_macro=None, parent=self)
        if dialog.exec() == QDialog.Accepted:
            new_macro = dialog.get_macro_data()
            self.profile_manager.save_macro(new_macro)
            self.refresh_list()
            self.macro_changed.emit()

    def _open_edit_dialog(self, macro: Dict[str, Any]):
        dialog = MacroEditorDialog(self.macro_engine, existing_macro=macro, parent=self)
        if dialog.exec() == QDialog.Accepted:
            updated_macro = dialog.get_macro_data()
            self.profile_manager.save_macro(updated_macro)
            self.refresh_list()
            self.macro_changed.emit()

    def _delete_macro(self, macro_id: str):
        if not macro_id:
            return
        reply = QMessageBox.question(
            self,
            "Delete Keybinding",
            "Are you sure you want to delete this keybinding?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.profile_manager.delete_macro(macro_id)
            self.refresh_list()
            self.macro_changed.emit()

    def _test_macro(self, macro: Dict[str, Any], button: QPushButton):
        norm = normalize_macro_dict(macro)
        action = norm.get("action", norm)
        self.macro_engine.run_macro_async(action)

        orig_text = button.text()
        button.setText(" ✓ Sent!")
        QTimer.singleShot(1200, lambda: button.setText(orig_text))

    def _on_filter_changed(self):
        self.refresh_list()
