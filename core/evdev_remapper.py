"""
OS-Level Key and Rotary Knob Remapper for Lingbao MK75 using evdev and uinput.
Intercepts hardware input events, applies custom remappings, executes macros and Linux commands,
and forwards remapped keystrokes to a virtual kernel device.
"""

import os
import time
import select
import logging
import threading
import subprocess
from typing import Dict, Any, Optional, List, Callable, Set

import evdev
from evdev import ecodes, UInput

from core.device_detector import DeviceInfo, MK75Detector
from core.macro_engine import MacroEngine

logger = logging.getLogger("MK75.Remapper")

def get_canonical_key_name(code: int) -> str:
    """Returns clean string keycode name, resolving kernel alias tuples/lists."""
    raw = ecodes.KEY.get(code, "")
    if isinstance(raw, (list, tuple)):
        # Prefer specific names over internal bounds markers like KEY_MIN_INTERESTING
        candidates = [k for k in raw if not k.startswith("KEY_MIN_") and not k.startswith("KEY_MAX_")]
        return candidates[0] if candidates else raw[0]
    return raw

MODIFIER_NAME_TO_ALIAS = {
    "KEY_LEFTCTRL": "CTRL",
    "KEY_RIGHTCTRL": "CTRL",
    "KEY_LEFTSHIFT": "SHIFT",
    "KEY_RIGHTSHIFT": "SHIFT",
    "KEY_LEFTALT": "ALT",
    "KEY_RIGHTALT": "ALT",
    "KEY_LEFTMETA": "SUPER",
    "KEY_RIGHTMETA": "SUPER",
}

class EvdevRemapper:
    """Background listener and remapping pipeline using evdev and uinput."""

    def __init__(self, profile_manager, macro_engine: Optional[MacroEngine] = None):
        self.profile_manager = profile_manager
        self.macro_engine = macro_engine or MacroEngine()
        self.running = False
        self._worker_thread: Optional[threading.Thread] = None
        self.devices: List[evdev.InputDevice] = []
        self.uinput: Optional[UInput] = None
        self.macro_engine.set_uinput(self.uinput)
        self.active_raw_modifiers: Set[str] = set()
        self.suppressed_combo_keys: Set[str] = set()
        self.key_event_listeners: List[Callable[[str, int], None]] = []

    @property
    def active_modifiers(self) -> Set[str]:
        return {MODIFIER_NAME_TO_ALIAS[k] for k in self.active_raw_modifiers if k in MODIFIER_NAME_TO_ALIAS}

    def _find_matching_combo_macro(self, active_mods: Set[str], key_name: str) -> Optional[Dict[str, Any]]:
        """Finds any macro whose trigger matches the currently pressed modifier combo and key."""
        if not active_mods:
            return None
        macros = self.profile_manager.get_macros()
        for m in macros:
            trigger = m.get("trigger")
            if not trigger or not isinstance(trigger, dict):
                continue
            req_mods = set(trigger.get("modifiers", []))
            req_key = str(trigger.get("key", "")).upper()

            # Normalize keys (strip KEY_ prefix if comparing)
            raw_clean = key_name.upper()
            raw_short = raw_clean[4:] if raw_clean.startswith("KEY_") else raw_clean
            req_short = req_key[4:] if req_key.startswith("KEY_") else req_key

            if req_mods == active_mods and (req_key == raw_clean or req_short == raw_short):
                return m
        return None

    def _release_active_modifiers(self) -> List[int]:
        """Temporarily releases held modifiers on the virtual uinput device."""
        if not self.uinput:
            return []
        released = []
        for mod_name in list(self.active_raw_modifiers):
            code = getattr(ecodes, mod_name, None)
            if code is not None:
                self.uinput.write(ecodes.EV_KEY, code, 0)
                released.append(code)
        if released:
            self.uinput.syn()
        return released

    def _restore_modifiers(self, codes: List[int]):
        """Restores physical modifiers on uinput if still held down."""
        if not self.uinput or not codes:
            return
        for code in codes:
            raw_name = get_canonical_key_name(code)
            if raw_name in self.active_raw_modifiers:
                self.uinput.write(ecodes.EV_KEY, code, 1)
        self.uinput.syn()

        # Callbacks for UI event notifications (e.g. visualizing keypresses in real-time)
        self.key_event_listeners: List[Callable[[str, int], None]] = []

    def add_key_listener(self, cb: Callable[[str, int], None]):
        self.key_event_listeners.append(cb)

    def _notify_key(self, key_id: str, value: int):
        for cb in self.key_event_listeners:
            try:
                cb(key_id, value)
            except Exception:
                pass

    def _init_uinput(self) -> bool:
        """Initializes the virtual uinput keyboard device."""
        if not os.path.exists("/dev/uinput") or not os.access("/dev/uinput", os.W_OK):
            logger.warning("/dev/uinput is not writable by current user. Remapping disabled.")
            return False

        try:
            # Enable all standard keys, media keys, and consumer keys (excluding EV_SYN which kernel manages)
            all_keys = [k for k in ecodes.KEY.keys() if isinstance(k, int) and k < 0x300]
            capabilities = {
                ecodes.EV_KEY: all_keys,
                ecodes.EV_REL: [ecodes.REL_WHEEL, ecodes.REL_HWHEEL],
            }
            self.uinput = UInput(
                capabilities,
                name="Lingbao MK75 Virtual Keyboard",
                vendor=0x1234,
                product=0x7500,
                version=0x0111
            )
            self.macro_engine.set_uinput(self.uinput)
            logger.info(f"Created virtual uinput device 'Lingbao MK75 Virtual Keyboard' with {len(all_keys)} keys")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize uinput device: {e}")
            return False

    def start_remapper(self, device_info: Optional[DeviceInfo] = None) -> bool:
        """Starts the evdev interception thread."""
        if self.running:
            return True

        if not device_info or not device_info.event_paths:
            device_info = MK75Detector.scan()

        if not device_info.event_paths:
            logger.warning("No input event paths found for MK75.")
            return False

        if not self._init_uinput():
            return False

        # Open and exclusively grab all relevant keyboard and consumer control event devices
        self.devices = []
        for path in device_info.event_paths:
            if os.path.exists(path) and os.access(path, os.R_OK):
                try:
                    dev = evdev.InputDevice(path)
                    if dev.name == "Lingbao MK75 Virtual Keyboard":
                        continue
                    caps = dev.capabilities()
                    # Only grab devices that report EV_KEY or EV_REL
                    if ecodes.EV_KEY in caps or ecodes.EV_REL in caps:
                        try:
                            dev.grab()
                            logger.info(f"Grabbed input device {path} ({dev.name})")
                        except Exception as e:
                            logger.warning(f"Could not grab {path} exclusively: {e}")
                        self.devices.append(dev)
                except Exception as e:
                    logger.error(f"Failed to open device {path}: {e}")

        if not self.devices:
            logger.warning("Could not access any MK75 input devices.")
            self._cleanup_uinput()
            return False

        self.running = True
        self._worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._worker_thread.start()
        logger.info(f"EvdevRemapper started listening on {len(self.devices)} devices.")
        return True

    def stop_remapper(self):
        """Stops the remapper thread and releases all grabbed devices."""
        self.running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=0.5)
        self._worker_thread = None

        self._cleanup_devices()
        self._cleanup_uinput()
        logger.info("EvdevRemapper stopped.")

    def _cleanup_devices(self):
        self.active_raw_modifiers.clear()
        self.suppressed_combo_keys.clear()
        for dev in self.devices:
            try:
                dev.ungrab()
            except Exception:
                pass
            try:
                dev.close()
            except Exception:
                pass
        self.devices = []

    def _cleanup_uinput(self):
        if self.uinput:
            try:
                self.uinput.close()
            except Exception:
                pass
            self.uinput = None

    def _run_loop(self):
        """Main event listener loop using select."""
        logger.info("EvdevRemapper event loop running...")
        while self.running and self.devices:
            try:
                r, _, _ = select.select(self.devices, [], [], 0.2)
                for dev in r:
                    for event in dev.read():
                        self._process_event(event)
            except (OSError, select.error):
                break
            except Exception as e:
                logger.error(f"Error in remapper event loop: {e}")
                break

        self._cleanup_devices()
        self.running = False

    def _process_event(self, event: evdev.InputEvent):
        if not self.uinput:
            return

        # 1. Handle Key Events (Standard keys, knob push, knob volume keys)
        if event.type == ecodes.EV_KEY:
            raw_key_name = get_canonical_key_name(event.code)
            key_id = raw_key_name

            # Map knob keys to canonical IDs
            if raw_key_name == "KEY_VOLUMEUP":
                key_id = "KNOB_CW"
            elif raw_key_name == "KEY_VOLUMEDOWN":
                key_id = "KNOB_CCW"
            elif raw_key_name == "KEY_MUTE":
                key_id = "KNOB_CLICK"

            self._notify_key(key_id, event.value)

            # Update modifier tracking
            if raw_key_name in MODIFIER_NAME_TO_ALIAS:
                if event.value in (1, 2):
                    self.active_raw_modifiers.add(raw_key_name)
                elif event.value == 0:
                    self.active_raw_modifiers.discard(raw_key_name)

                # Hardware modifier keys (Ctrl, Shift, Alt, Super) must ALWAYS pass through
                # directly to uinput so system shortcuts and typing are never broken.
                self.uinput.write(event.type, event.code, event.value)
                self.uinput.syn()
                return

            # Check if this key was part of an intercepted combo macro
            if raw_key_name in self.suppressed_combo_keys:
                if event.value == 0:
                    self.suppressed_combo_keys.discard(raw_key_name)
                return

            # Check for combo macro trigger on key press (event.value == 1)
            if event.value == 1 and self.active_modifiers and raw_key_name not in MODIFIER_NAME_TO_ALIAS:
                combo_macro = self._find_matching_combo_macro(self.active_modifiers, raw_key_name)
                if combo_macro:
                    self.suppressed_combo_keys.add(raw_key_name)
                    action = combo_macro.get("action", combo_macro)
                    logger.info(
                        f"Matched combo keybinding: {list(self.active_modifiers)} + {raw_key_name} -> {combo_macro.get('name', 'Action')}"
                    )
                    act_type = action.get("type", "command")
                    if act_type == "command":
                        cmd = action.get("command")
                        if cmd:
                            try:
                                subprocess.Popen(cmd, shell=True)
                            except Exception as e:
                                logger.error(f"Failed to execute combo command: {e}")
                    else:
                        released = self._release_active_modifiers()
                        self.macro_engine.run_macro_async(action, on_complete=lambda: self._restore_modifiers(released))
                    return

            # Check for remapping
            remap = self.profile_manager.get_remapping(key_id)
            if not remap and key_id != raw_key_name:
                remap = self.profile_manager.get_remapping(raw_key_name)

            if remap:
                remap_type = remap.get("type")
                if remap_type == "key":
                    target_name = remap.get("target")
                    target_code = getattr(ecodes, target_name, None)
                    if target_code is not None:
                        # For knob turns (momentary action), simulate clean press and release
                        if key_id in ("KNOB_CW", "KNOB_CCW"):
                            if event.value == 1:
                                self.uinput.write(ecodes.EV_KEY, target_code, 1)
                                self.uinput.syn()
                                time.sleep(0.01)
                                self.uinput.write(ecodes.EV_KEY, target_code, 0)
                                self.uinput.syn()
                        else:
                            self.uinput.write(ecodes.EV_KEY, target_code, event.value)
                            self.uinput.syn()
                        return
                elif remap_type in ("macro", "shortcut", "text"):
                    if event.value == 1:
                        if remap_type == "macro":
                            macro_id = remap.get("macro_id")
                            macro = next((m for m in self.profile_manager.get_macros() if m.get("id") == macro_id), None)
                        else:
                            macro = remap
                        if macro:
                            self.macro_engine.run_macro_async(macro)
                    # Consume press, release, and repeat events for remapped shortcut/macro
                    return
                elif remap_type == "command":
                    if event.value == 1:
                        cmd = remap.get("command")
                        if cmd:
                            try:
                                logger.info(f"Triggering mapped shell command: {cmd}")
                                subprocess.Popen(cmd, shell=True)
                            except Exception as e:
                                logger.error(f"Command execution error: {e}")
                    # Consume press, release, and repeat events for remapped shell command
                    return

            # Default passthrough
            self.uinput.write(event.type, event.code, event.value)
            self.uinput.syn()

        # 2. Handle Relative Events (Knob wheel turns)
        elif event.type == ecodes.EV_REL and event.code in (ecodes.REL_WHEEL, ecodes.REL_HWHEEL):
            key_id = "KNOB_CW" if event.value > 0 else "KNOB_CCW"
            self._notify_key(key_id, 1)

            remap = self.profile_manager.get_remapping(key_id)
            if remap:
                remap_type = remap.get("type")
                if remap_type == "key":
                    target_name = remap.get("target")
                    target_code = getattr(ecodes, target_name, None)
                    if target_code is not None:
                        self.uinput.write(ecodes.EV_KEY, target_code, 1)
                        self.uinput.syn()
                        time.sleep(0.01)
                        self.uinput.write(ecodes.EV_KEY, target_code, 0)
                        self.uinput.syn()
                        return
                elif remap_type in ("macro", "shortcut", "text"):
                    if remap_type == "macro":
                        macro_id = remap.get("macro_id")
                        macro = next((m for m in self.profile_manager.get_macros() if m.get("id") == macro_id), None)
                    else:
                        macro = remap
                    if macro:
                        self.macro_engine.run_macro_async(macro)
                        return
                elif remap_type == "command":
                    cmd = remap.get("command")
                    if cmd:
                        subprocess.Popen(cmd, shell=True)
                        return

            # Pass through relative event
            self.uinput.write(event.type, event.code, event.value)
            self.uinput.syn()

        else:
            # Passthrough other events (syn, misc, abs)
            self.uinput.write(event.type, event.code, event.value)
            if event.type != ecodes.EV_SYN:
                self.uinput.syn()
