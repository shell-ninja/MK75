"""
Human-Friendly Macro Execution Engine for Lingbao MK75.
Executes keyboard shortcuts, text typing, delays, and shell scripts cleanly.
"""

import time
import logging
import threading
import subprocess
from typing import Dict, Any, List, Optional, Callable
import evdev
from evdev import ecodes

logger = logging.getLogger("MK75.MacroEngine")

# Character to keycode mapping for clean automated typing
CHAR_MAP = {
    'a': ('KEY_A', False), 'b': ('KEY_B', False), 'c': ('KEY_C', False),
    'd': ('KEY_D', False), 'e': ('KEY_E', False), 'f': ('KEY_F', False),
    'g': ('KEY_G', False), 'h': ('KEY_H', False), 'i': ('KEY_I', False),
    'j': ('KEY_J', False), 'k': ('KEY_K', False), 'l': ('KEY_L', False),
    'm': ('KEY_M', False), 'n': ('KEY_N', False), 'o': ('KEY_O', False),
    'p': ('KEY_P', False), 'q': ('KEY_Q', False), 'r': ('KEY_R', False),
    's': ('KEY_S', False), 't': ('KEY_T', False), 'u': ('KEY_U', False),
    'v': ('KEY_V', False), 'w': ('KEY_W', False), 'x': ('KEY_X', False),
    'y': ('KEY_Y', False), 'z': ('KEY_Z', False),
    'A': ('KEY_A', True),  'B': ('KEY_B', True),  'C': ('KEY_C', True),
    'D': ('KEY_D', True),  'E': ('KEY_E', True),  'F': ('KEY_F', True),
    'G': ('KEY_G', True),  'H': ('KEY_H', True),  'I': ('KEY_I', True),
    'J': ('KEY_J', True),  'K': ('KEY_K', True),  'L': ('KEY_L', True),
    'M': ('KEY_M', True),  'N': ('KEY_N', True),  'O': ('KEY_O', True),
    'P': ('KEY_P', True),  'Q': ('KEY_Q', True),  'R': ('KEY_R', True),
    'S': ('KEY_S', True),  'T': ('KEY_T', True),  'U': ('KEY_U', True),
    'V': ('KEY_V', True),  'W': ('KEY_W', True),  'X': ('KEY_X', True),
    'Y': ('KEY_Y', True),  'Z': ('KEY_Z', True),
    '0': ('KEY_0', False), '1': ('KEY_1', False), '2': ('KEY_2', False),
    '3': ('KEY_3', False), '4': ('KEY_4', False), '5': ('KEY_5', False),
    '6': ('KEY_6', False), '7': ('KEY_7', False), '8': ('KEY_8', False),
    '9': ('KEY_9', False), ' ': ('KEY_SPACE', False), '\n': ('KEY_ENTER', False),
    '\t': ('KEY_TAB', False), '-': ('KEY_MINUS', False), '_': ('KEY_MINUS', True),
    '=': ('KEY_EQUAL', False), '+': ('KEY_EQUAL', True),
    '[': ('KEY_LEFTBRACE', False), '{': ('KEY_LEFTBRACE', True),
    ']': ('KEY_RIGHTBRACE', False), '}': ('KEY_RIGHTBRACE', True),
    '\\': ('KEY_BACKSLASH', False), '|': ('KEY_BACKSLASH', True),
    ';': ('KEY_SEMICOLON', False), ':': ('KEY_SEMICOLON', True),
    "'": ('KEY_APOSTROPHE', False), '"': ('KEY_APOSTROPHE', True),
    ',': ('KEY_COMMA', False), '<': ('KEY_COMMA', True),
    '.': ('KEY_DOT', False), '>': ('KEY_DOT', True),
    '/': ('KEY_SLASH', False), '?': ('KEY_SLASH', True),
    '!': ('KEY_1', True), '@': ('KEY_2', True), '#': ('KEY_3', True),
    '$': ('KEY_4', True), '%': ('KEY_5', True), '^': ('KEY_6', True),
    '&': ('KEY_7', True), '*': ('KEY_8', True), '(': ('KEY_9', True),
    ')': ('KEY_0', True),
}

class MacroEngine:
    """Executes shortcuts, text typing, and shell commands asynchronously."""

    def __init__(self, uinput_device=None):
        self.uinput_device = uinput_device

    def set_uinput(self, uinput_device):
        self.uinput_device = uinput_device

    def run_macro_async(self, macro: Dict[str, Any], on_complete: Optional[Callable[[], None]] = None):
        """Runs macro in a dedicated background daemon thread."""
        thread = threading.Thread(target=self._execute_with_callback, args=(macro, on_complete), daemon=True)
        thread.start()

    def _execute_with_callback(self, macro: Dict[str, Any], on_complete: Optional[Callable[[], None]] = None):
        try:
            self._execute(macro)
        finally:
            if on_complete:
                try:
                    on_complete()
                except Exception as e:
                    logger.error(f"Error in macro on_complete callback: {e}")

    def _execute(self, macro: Dict[str, Any]):
        if "action" in macro and isinstance(macro["action"], dict):
            action_data = macro["action"]
            name = macro.get("name", action_data.get("name", "Unnamed Macro"))
            mtype = action_data.get("type", "command")
            macro_obj = {**action_data, "name": name, "type": mtype}
        else:
            macro_obj = macro
            name = macro.get("name", "Unnamed Macro")
            mtype = macro.get("type", "shortcut")

        logger.info(f"Executing macro: {name} (type: {mtype})")

        # 1. Human-Friendly Shortcut Mode (e.g. ["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_T"])
        if mtype == "shortcut":
            keys = macro_obj.get("keys", [])
            if not keys or not self.uinput_device:
                return

            keycodes = [getattr(ecodes, k, None) for k in keys if getattr(ecodes, k, None) is not None]
            try:
                # Press all keys in sequence
                for code in keycodes:
                    self.uinput_device.write(ecodes.EV_KEY, code, 1)
                    self.uinput_device.syn()
                    time.sleep(0.01)

                time.sleep(0.03)

                # Release all keys in reverse
                for code in reversed(keycodes):
                    self.uinput_device.write(ecodes.EV_KEY, code, 0)
                    self.uinput_device.syn()
                    time.sleep(0.01)
            except Exception as e:
                logger.error(f"Error executing shortcut macro: {e}")

        # 2. Text Expander Mode (Types string directly)
        elif mtype == "text":
            text = macro_obj.get("text", "")
            delay_ms = macro_obj.get("speed_ms", 12)
            if not text or not self.uinput_device:
                return

            delay_s = max(0.001, delay_ms / 1000.0)
            shift_code = ecodes.KEY_LEFTSHIFT

            for ch in text:
                mapping = CHAR_MAP.get(ch)
                if not mapping:
                    continue
                key_name, need_shift = mapping
                code = getattr(ecodes, key_name, None)
                if code is None:
                    continue

                try:
                    if need_shift:
                        self.uinput_device.write(ecodes.EV_KEY, shift_code, 1)
                        self.uinput_device.syn()
                        time.sleep(0.005)

                    self.uinput_device.write(ecodes.EV_KEY, code, 1)
                    self.uinput_device.syn()
                    time.sleep(delay_s)
                    self.uinput_device.write(ecodes.EV_KEY, code, 0)
                    self.uinput_device.syn()

                    if need_shift:
                        time.sleep(0.005)
                        self.uinput_device.write(ecodes.EV_KEY, shift_code, 0)
                        self.uinput_device.syn()

                    time.sleep(delay_s)
                except Exception as e:
                    logger.error(f"Error typing character '{ch}': {e}")

        # 3. Shell Command Mode
        elif mtype == "command":
            cmd = macro_obj.get("command", "")
            if cmd:
                try:
                    subprocess.Popen(cmd, shell=True)
                except Exception as e:
                    logger.error(f"Error executing command '{cmd}': {e}")

        # 4. Fallback: Step Sequence
        elif "steps" in macro_obj:
            for step in macro_obj.get("steps", []):
                act = step.get("action")
                if act == "command":
                    cmd = step.get("command")
                    if cmd:
                        subprocess.Popen(cmd, shell=True)
                elif act in ("down", "up", "press") and self.uinput_device:
                    kname = step.get("key")
                    code = getattr(ecodes, kname, None)
                    if code is not None:
                        val = 1 if act in ("down", "press") else 0
                        self.uinput_device.write(ecodes.EV_KEY, code, val)
                        self.uinput_device.syn()
                        if act == "press":
                            time.sleep(0.02)
                            self.uinput_device.write(ecodes.EV_KEY, code, 0)
                            self.uinput_device.syn()
                elif act == "delay":
                    time.sleep(max(0.001, step.get("delay_ms", 50) / 1000.0))
