"""
Key and Shortcut Capture Widgets for MK75 Controller.
Provides interactive keystroke recording for single keys and multi-key shortcuts
with modifier pills and preset quick-chips.
"""

from typing import Optional, List, Set, Tuple
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QPushButton

# Modifier mappings
MODIFIERS_MAP = {
    Qt.Key_Control: "KEY_LEFTCTRL",
    Qt.Key_Shift: "KEY_LEFTSHIFT",
    Qt.Key_Alt: "KEY_LEFTALT",
    Qt.Key_AltGr: "KEY_RIGHTALT",
    Qt.Key_Meta: "KEY_LEFTMETA",
    Qt.Key_Super_L: "KEY_LEFTMETA",
    Qt.Key_Super_R: "KEY_RIGHTMETA",
}

# Common Qt Key to Linux Evdev Keycode name
EVDEV_KEY_MAP = {
    Qt.Key_Return: "KEY_ENTER",
    Qt.Key_Enter: "KEY_KPENTER",
    Qt.Key_Tab: "KEY_TAB",
    Qt.Key_Backtab: "KEY_TAB",
    Qt.Key_Space: "KEY_SPACE",
    Qt.Key_Backspace: "KEY_BACKSPACE",
    Qt.Key_Delete: "KEY_DELETE",
    Qt.Key_Insert: "KEY_INSERT",
    Qt.Key_Home: "KEY_HOME",
    Qt.Key_End: "KEY_END",
    Qt.Key_PageUp: "KEY_PAGEUP",
    Qt.Key_PageDown: "KEY_PAGEDOWN",
    Qt.Key_Left: "KEY_LEFT",
    Qt.Key_Right: "KEY_RIGHT",
    Qt.Key_Up: "KEY_UP",
    Qt.Key_Down: "KEY_DOWN",
    Qt.Key_Escape: "KEY_ESC",
    Qt.Key_CapsLock: "KEY_CAPSLOCK",
    Qt.Key_ScrollLock: "KEY_SCROLLLOCK",
    Qt.Key_NumLock: "KEY_NUMLOCK",
    Qt.Key_Print: "KEY_SYSRQ",
    Qt.Key_Pause: "KEY_PAUSE",
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

# Standard Shortcut Presets
PRESET_SHORTCUTS: List[Tuple[str, List[str]]] = [
    ("Ctrl+C (Copy)", ["KEY_LEFTCTRL", "KEY_C"]),
    ("Ctrl+V (Paste)", ["KEY_LEFTCTRL", "KEY_V"]),
    ("Ctrl+Z (Undo)", ["KEY_LEFTCTRL", "KEY_Z"]),
    ("Ctrl+A (Select All)", ["KEY_LEFTCTRL", "KEY_A"]),
    ("Ctrl+W (Close Tab)", ["KEY_LEFTCTRL", "KEY_W"]),
    ("Ctrl+Shift+T (Reopen)", ["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_T"]),
    ("Ctrl+Alt+T (Terminal)", ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_T"]),
    ("Alt+Tab (Switch App)", ["KEY_LEFTALT", "KEY_TAB"]),
    ("Super+D (Desktop)", ["KEY_LEFTMETA", "KEY_D"]),
    ("Super+Space (Launcher)", ["KEY_LEFTMETA", "KEY_SPACE"]),
]


class KeyCaptureBox(QPushButton):
    """
    Interactive button that records physical keystroke shortcuts (modifiers + target key).
    Properly handles modifier keys without prematurely ending recording, allowing multi-key combinations.
    """

    shortcut_recorded = Signal(list)
    modifiers_updated = Signal(set)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recording = False
        self.captured_keys: List[str] = ["KEY_LEFTCTRL", "KEY_C"]
        self.held_modifiers: Set[str] = set()
        self.setMinimumHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self._update_display()
        self.clicked.connect(self._toggle_recording)

    def set_keys(self, keys: List[str], emit_signal: bool = False):
        self.captured_keys = list(keys)
        self.recording = False
        self.held_modifiers.clear()
        self._update_display()
        if emit_signal:
            self.shortcut_recorded.emit(self.captured_keys)

    def set_modifier_toggled(self, mod_code: str, active: bool):
        """Called when user clicks an interactive modifier pill."""
        current_mods = [k for k in self.captured_keys if k in ("KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_LEFTALT", "KEY_LEFTMETA")]
        primary_keys = [k for k in self.captured_keys if k not in ("KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_LEFTALT", "KEY_LEFTMETA")]

        mod_set = set(current_mods)
        if active:
            mod_set.add(mod_code)
        else:
            mod_set.discard(mod_code)

        ordered = []
        for m in ("KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_LEFTALT", "KEY_LEFTMETA"):
            if m in mod_set:
                ordered.append(m)

        if not primary_keys:
            primary_keys = ["KEY_C"]

        self.captured_keys = ordered + primary_keys
        self._update_display()
        self.shortcut_recorded.emit(self.captured_keys)

    def _update_display(self):
        if self.recording:
            if self.held_modifiers:
                readable = [k.replace("KEY_LEFT", "").replace("KEY_", "") for k in sorted(self.held_modifiers)]
                mod_str = " + ".join(readable)
                self.setText(f"Listening...  [ {mod_str} + ... ]  Press key to finish (or Esc to cancel)")
            else:
                self.setText("Listening... Press shortcut on keyboard (e.g. Ctrl + Shift + T)")
            self.setStyleSheet(
                "background-color: #2D2418; color: #F59E0B; border: 2px dashed #D97706; "
                "font-size: 13px; font-weight: 600; border-radius: 8px;"
            )
        else:
            if not self.captured_keys:
                self.setText("Click to record shortcut directly from keyboard...")
                self.setStyleSheet(
                    "background-color: #171A26; color: #8A94A6; border: 1px dashed #2E384D; "
                    "font-size: 13px; border-radius: 8px;"
                )
            else:
                readable = [k.replace("KEY_LEFT", "").replace("KEY_RIGHT", "").replace("KEY_", "") for k in self.captured_keys]
                label_text = "  +  ".join(readable)
                self.setText(f"Shortcut:  [ {label_text} ]   (Click here to re-record)")
                self.setStyleSheet(
                    "background-color: #1A2236; color: #FFFFFF; border: 1px solid #3B4666; "
                    "font-size: 13px; font-weight: 600; border-radius: 8px;"
                )

    def _toggle_recording(self):
        self.recording = not self.recording
        self.held_modifiers.clear()
        self._update_display()

    def keyPressEvent(self, event: QKeyEvent):
        if not self.recording:
            super().keyPressEvent(event)
            return

        key_val = event.key()

        # Cancel on Escape when no modifier is held
        if key_val == Qt.Key_Escape and not self.held_modifiers:
            self.recording = False
            self.held_modifiers.clear()
            self._update_display()
            return

        # 1. Check if the key pressed is a modifier (Control, Shift, Alt, Meta)
        if key_val in MODIFIERS_MAP:
            mod_name = MODIFIERS_MAP[key_val]
            self.held_modifiers.add(mod_name)
            self._update_display()
            self.modifiers_updated.emit(self.held_modifiers)
            return  # Keep recording open! Wait for next key!

        # 2. Key is a non-modifier! Collect all held modifiers
        mods = event.modifiers()
        active_mods = set(self.held_modifiers)
        if mods & Qt.ControlModifier:
            active_mods.add("KEY_LEFTCTRL")
        if mods & Qt.ShiftModifier:
            active_mods.add("KEY_LEFTSHIFT")
        if mods & Qt.AltModifier:
            active_mods.add("KEY_LEFTALT")
        if mods & Qt.MetaModifier:
            active_mods.add("KEY_LEFTMETA")

        # 3. Resolve primary key name
        primary_key = None
        if key_val in EVDEV_KEY_MAP:
            primary_key = EVDEV_KEY_MAP[key_val]
        elif Qt.Key_A <= key_val <= Qt.Key_Z:
            primary_key = f"KEY_{chr(key_val)}"
        elif Qt.Key_0 <= key_val <= Qt.Key_9:
            primary_key = f"KEY_{chr(key_val)}"
        elif Qt.Key_F1 <= key_val <= Qt.Key_F12:
            primary_key = f"KEY_F{key_val - Qt.Key_F1 + 1}"
        else:
            primary_key = EVDEV_KEY_MAP.get(key_val, f"KEY_{key_val}")

        # Order modifiers cleanly: Ctrl, Shift, Alt, Super
        ordered_keys = []
        for m in ("KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_LEFTALT", "KEY_LEFTMETA"):
            if m in active_mods:
                ordered_keys.append(m)

        if primary_key:
            ordered_keys.append(primary_key)

        self.captured_keys = ordered_keys
        self.recording = False
        self.held_modifiers.clear()
        self._update_display()
        self.shortcut_recorded.emit(self.captured_keys)


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

        evdev_key = EVDEV_KEY_MAP.get(key_val)
        if not evdev_key:
            if key_val in MODIFIERS_MAP:
                evdev_key = MODIFIERS_MAP[key_val]
            elif Qt.Key_A <= key_val <= Qt.Key_Z:
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
