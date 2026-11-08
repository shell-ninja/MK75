"""
Keycode definitions, layout specifications, and action presets for the Lingbao MK75.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class KeyDef:
    id: str                 # Unique key ID, e.g. "K_ESC", "KNOB_CLICK", "KNOB_CW"
    label: str              # Primary display label, e.g. "Esc", "Volume Up"
    sub_label: str          # Secondary sub-label / symbol, e.g. "~", "F1"
    keycode_name: str       # Default evdev keycode name, e.g. "KEY_ESC"
    row: int                # Row index (0-5)
    x: float                # Grid unit offset X
    y: float                # Grid unit offset Y
    w: float = 1.0          # Key width in standard key units (1.0 = 1u)
    h: float = 1.0          # Key height in standard key units (1.0 = 1u)
    is_knob: bool = False
    is_modifier: bool = False
    is_special: bool = False

# 75% 81-Key Layout definitions with accurate physical proportions
LAYOUT_75_PERCENT: List[KeyDef] = [
    # Row 0: Function row + Rotary Knob
    KeyDef("KEY_ESC", "Esc", "", "KEY_ESC", 0, 0.0, 0.0, 1.0),
    KeyDef("KEY_F1", "F1", "", "KEY_F1", 0, 1.25, 0.0, 1.0),
    KeyDef("KEY_F2", "F2", "", "KEY_F2", 0, 2.25, 0.0, 1.0),
    KeyDef("KEY_F3", "F3", "", "KEY_F3", 0, 3.25, 0.0, 1.0),
    KeyDef("KEY_F4", "F4", "", "KEY_F4", 0, 4.25, 0.0, 1.0),
    KeyDef("KEY_F5", "F5", "", "KEY_F5", 0, 5.75, 0.0, 1.0),
    KeyDef("KEY_F6", "F6", "", "KEY_F6", 0, 6.75, 0.0, 1.0),
    KeyDef("KEY_F7", "F7", "", "KEY_F7", 0, 7.75, 0.0, 1.0),
    KeyDef("KEY_F8", "F8", "", "KEY_F8", 0, 8.75, 0.0, 1.0),
    KeyDef("KEY_F9", "F9", "", "KEY_F9", 0, 10.25, 0.0, 1.0),
    KeyDef("KEY_F10", "F10", "", "KEY_F10", 0, 11.25, 0.0, 1.0),
    KeyDef("KEY_F11", "F11", "", "KEY_F11", 0, 12.25, 0.0, 1.0),
    KeyDef("KEY_F12", "F12", "", "KEY_F12", 0, 13.25, 0.0, 1.0),
    KeyDef("KEY_DELETE", "Del", "", "KEY_DELETE", 0, 14.5, 0.0, 1.0, is_special=True),
    KeyDef("KNOB_CLICK", "Knob", "Push", "KEY_MUTE", 0, 15.65, -0.15, 1.25, 1.25, is_knob=True),

    # Row 1: Number row + Navigation column
    KeyDef("KEY_GRAVE", "~", "`", "KEY_GRAVE", 1, 0.0, 1.2, 1.0),
    KeyDef("KEY_1", "1", "!", "KEY_1", 1, 1.0, 1.2, 1.0),
    KeyDef("KEY_2", "2", "@", "KEY_2", 1, 2.0, 1.2, 1.0),
    KeyDef("KEY_3", "3", "#", "KEY_3", 1, 3.0, 1.2, 1.0),
    KeyDef("KEY_4", "4", "$", "KEY_4", 1, 4.0, 1.2, 1.0),
    KeyDef("KEY_5", "5", "%", "KEY_5", 1, 5.0, 1.2, 1.0),
    KeyDef("KEY_6", "6", "^", "KEY_6", 1, 6.0, 1.2, 1.0),
    KeyDef("KEY_7", "7", "&", "KEY_7", 1, 7.0, 1.2, 1.0),
    KeyDef("KEY_8", "8", "*", "KEY_8", 1, 8.0, 1.2, 1.0),
    KeyDef("KEY_9", "9", "(", "KEY_9", 1, 9.0, 1.2, 1.0),
    KeyDef("KEY_0", "0", ")", "KEY_0", 1, 10.0, 1.2, 1.0),
    KeyDef("KEY_MINUS", "-", "_", "KEY_MINUS", 1, 11.0, 1.2, 1.0),
    KeyDef("KEY_EQUAL", "=", "+", "KEY_EQUAL", 1, 12.0, 1.2, 1.0),
    KeyDef("KEY_BACKSPACE", "Backspace", "", "KEY_BACKSPACE", 1, 13.0, 1.2, 2.0, is_special=True),
    KeyDef("KEY_PAGEUP", "PgUp", "", "KEY_PAGEUP", 1, 15.2, 1.2, 1.0, is_special=True),

    # Row 2: QWERTY + Navigation column
    KeyDef("KEY_TAB", "Tab", "", "KEY_TAB", 2, 0.0, 2.3, 1.5, is_special=True),
    KeyDef("KEY_Q", "Q", "", "KEY_Q", 2, 1.5, 2.3, 1.0),
    KeyDef("KEY_W", "W", "", "KEY_W", 2, 2.5, 2.3, 1.0),
    KeyDef("KEY_E", "E", "", "KEY_E", 2, 3.5, 2.3, 1.0),
    KeyDef("KEY_R", "R", "", "KEY_R", 2, 4.5, 2.3, 1.0),
    KeyDef("KEY_T", "T", "", "KEY_T", 2, 5.5, 2.3, 1.0),
    KeyDef("KEY_Y", "Y", "", "KEY_Y", 2, 6.5, 2.3, 1.0),
    KeyDef("KEY_U", "U", "", "KEY_U", 2, 7.5, 2.3, 1.0),
    KeyDef("KEY_I", "I", "", "KEY_I", 2, 8.5, 2.3, 1.0),
    KeyDef("KEY_O", "O", "", "KEY_O", 2, 9.5, 2.3, 1.0),
    KeyDef("KEY_P", "P", "", "KEY_P", 2, 10.5, 2.3, 1.0),
    KeyDef("KEY_LEFTBRACE", "[", "{", "KEY_LEFTBRACE", 2, 11.5, 2.3, 1.0),
    KeyDef("KEY_RIGHTBRACE", "]", "}", "KEY_RIGHTBRACE", 2, 12.5, 2.3, 1.0),
    KeyDef("KEY_BACKSLASH", "\\", "|", "KEY_BACKSLASH", 2, 13.5, 2.3, 1.5),
    KeyDef("KEY_PAGEDOWN", "PgDn", "", "KEY_PAGEDOWN", 2, 15.2, 2.3, 1.0, is_special=True),

    # Row 3: ASDF Home row + End
    KeyDef("KEY_CAPSLOCK", "Caps", "", "KEY_CAPSLOCK", 3, 0.0, 3.4, 1.75, is_special=True),
    KeyDef("KEY_A", "A", "", "KEY_A", 3, 1.75, 3.4, 1.0),
    KeyDef("KEY_S", "S", "", "KEY_S", 3, 2.75, 3.4, 1.0),
    KeyDef("KEY_D", "D", "", "KEY_D", 3, 3.75, 3.4, 1.0),
    KeyDef("KEY_F", "F", "", "KEY_F", 3, 4.75, 3.4, 1.0),
    KeyDef("KEY_G", "G", "", "KEY_G", 3, 5.75, 3.4, 1.0),
    KeyDef("KEY_H", "H", "", "KEY_H", 3, 6.75, 3.4, 1.0),
    KeyDef("KEY_J", "J", "", "KEY_J", 3, 7.75, 3.4, 1.0),
    KeyDef("KEY_K", "K", "", "KEY_K", 3, 8.75, 3.4, 1.0),
    KeyDef("KEY_L", "L", "", "KEY_L", 3, 9.75, 3.4, 1.0),
    KeyDef("KEY_SEMICOLON", ";", ":", "KEY_SEMICOLON", 3, 10.75, 3.4, 1.0),
    KeyDef("KEY_APOSTROPHE", "'", "\"", "KEY_APOSTROPHE", 3, 11.75, 3.4, 1.0),
    KeyDef("KEY_ENTER", "Enter", "", "KEY_ENTER", 3, 12.75, 3.4, 2.25, is_special=True),
    KeyDef("KEY_END", "End", "", "KEY_END", 3, 15.2, 3.4, 1.0, is_special=True),

    # Row 4: Shift row + Arrow Up
    KeyDef("KEY_LEFTSHIFT", "Shift", "", "KEY_LEFTSHIFT", 4, 0.0, 4.5, 2.25, is_modifier=True),
    KeyDef("KEY_Z", "Z", "", "KEY_Z", 4, 2.25, 4.5, 1.0),
    KeyDef("KEY_X", "X", "", "KEY_X", 4, 3.25, 4.5, 1.0),
    KeyDef("KEY_C", "C", "", "KEY_C", 4, 4.25, 4.5, 1.0),
    KeyDef("KEY_V", "V", "", "KEY_V", 4, 5.25, 4.5, 1.0),
    KeyDef("KEY_B", "B", "", "KEY_B", 4, 6.25, 4.5, 1.0),
    KeyDef("KEY_N", "N", "", "KEY_N", 4, 7.25, 4.5, 1.0),
    KeyDef("KEY_M", "M", "", "KEY_M", 4, 8.25, 4.5, 1.0),
    KeyDef("KEY_COMMA", ",", "<", "KEY_COMMA", 4, 9.25, 4.5, 1.0),
    KeyDef("KEY_DOT", ".", ">", "KEY_DOT", 4, 10.25, 4.5, 1.0),
    KeyDef("KEY_SLASH", "/", "?", "KEY_SLASH", 4, 11.25, 4.5, 1.0),
    KeyDef("KEY_RIGHTSHIFT", "Shift", "", "KEY_RIGHTSHIFT", 4, 12.25, 4.5, 1.75, is_modifier=True),
    KeyDef("KEY_UP", "Up", "", "KEY_UP", 4, 14.15, 4.5, 1.0, is_special=True),

    # Row 5: Bottom row + Arrow Left, Down, Right
    KeyDef("KEY_LEFTCTRL", "Ctrl", "", "KEY_LEFTCTRL", 5, 0.0, 5.6, 1.25, is_modifier=True),
    KeyDef("KEY_LEFTMETA", "Super", "Win", "KEY_LEFTMETA", 5, 1.25, 5.6, 1.25, is_modifier=True),
    KeyDef("KEY_LEFTALT", "Alt", "", "KEY_LEFTALT", 5, 2.5, 5.6, 1.25, is_modifier=True),
    KeyDef("KEY_SPACE", "Space", "", "KEY_SPACE", 5, 3.75, 5.6, 6.25),
    KeyDef("KEY_RIGHTALT", "Alt", "", "KEY_RIGHTALT", 5, 10.0, 5.6, 1.0, is_modifier=True),
    KeyDef("KEY_FN", "Fn", "", "KEY_FN", 5, 11.0, 5.6, 1.0, is_modifier=True),
    KeyDef("KEY_RIGHTCTRL", "Ctrl", "", "KEY_RIGHTCTRL", 5, 12.0, 5.6, 1.0, is_modifier=True),
    KeyDef("KEY_LEFT", "Left", "", "KEY_LEFT", 5, 13.15, 5.6, 1.0, is_special=True),
    KeyDef("KEY_DOWN", "Down", "", "KEY_DOWN", 5, 14.15, 5.6, 1.0, is_special=True),
    KeyDef("KEY_RIGHT", "Right", "", "KEY_RIGHT", 5, 15.15, 5.6, 1.0, is_special=True),
]

# Knob specific virtual keys (Clockwise turn, Counter-Clockwise turn)
KNOB_ACTIONS = [
    {"id": "KNOB_CW", "label": "Knob Turn Clockwise (Right)", "default": "KEY_VOLUMEUP"},
    {"id": "KNOB_CCW", "label": "Knob Turn Counter-Clockwise (Left)", "default": "KEY_VOLUMEDOWN"},
    {"id": "KNOB_CLICK", "label": "Knob Push / Click", "default": "KEY_MUTE"},
]

# Presets for quick remap assignment
REMAP_ACTION_CATEGORIES = {
    "Media & Volume": [
        ("KEY_VOLUMEUP", "Volume Up"),
        ("KEY_VOLUMEDOWN", "Volume Down"),
        ("KEY_MUTE", "Mute Audio"),
        ("KEY_PLAYPAUSE", "Play / Pause"),
        ("KEY_NEXTSONG", "Next Track"),
        ("KEY_PREVIOUSSONG", "Previous Track"),
        ("KEY_STOPCD", "Stop Media"),
    ],
    "Display & System": [
        ("KEY_BRIGHTNESSUP", "Brightness Up"),
        ("KEY_BRIGHTNESSDOWN", "Brightness Down"),
        ("KEY_SLEEP", "Sleep System"),
        ("KEY_POWER", "Power Button"),
        ("KEY_SCREENLOCK", "Lock Screen"),
    ],
    "Navigation & Desktop": [
        ("KEY_PAGEUP", "Page Up"),
        ("KEY_PAGEDOWN", "Page Down"),
        ("KEY_HOME", "Home"),
        ("KEY_END", "End"),
        ("KEY_INSERT", "Insert"),
        ("KEY_PRINT", "Print Screen / Screenshot"),
    ],
    "Modifiers": [
        ("KEY_LEFTCTRL", "Left Ctrl"),
        ("KEY_LEFTSHIFT", "Left Shift"),
        ("KEY_LEFTALT", "Left Alt"),
        ("KEY_LEFTMETA", "Left Super / Win"),
        ("KEY_RIGHTCTRL", "Right Ctrl"),
        ("KEY_RIGHTSHIFT", "Right Shift"),
        ("KEY_RIGHTALT", "Right Alt"),
    ],
}
