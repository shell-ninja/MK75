"""
Profile Manager for Lingbao MK75 configuration.
Handles persistence, serialization, profile switching, and defaults.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger("MK75.ProfileManager")

DEFAULT_PROFILE: Dict[str, Any] = {
    "version": 1,
    "profile_name": "Default Profile",
    "active": True,
    "remapping": {
        "KNOB_CW": {
            "type": "key",
            "target": "KEY_VOLUMEUP"
        },
        "KNOB_CCW": {
            "type": "key",
            "target": "KEY_VOLUMEDOWN"
        },
        "KNOB_CLICK": {
            "type": "key",
            "target": "KEY_MUTE"
        }
    },
    "lighting": {
        "effect_id": 3,
        "effect_name": "Rainbow Wave",
        "brightness": 3,
        "speed": 2,
        "color": [99, 102, 241],
        "side_glow_enabled": True,
        "side_glow_mode": 1
    },
    "macros": [
        {
            "id": "macro_term",
            "name": "Quick Terminal",
            "type": "command",
            "command": "kitty &"
        },
        {
            "id": "macro_mute_mic",
            "name": "Mute Microphone",
            "type": "command",
            "command": "pactl set-source-mute @DEFAULT_SOURCE@ toggle"
        },
        {
            "id": "macro_paste",
            "name": "Quick Paste",
            "type": "shortcut",
            "keys": ["KEY_LEFTCTRL", "KEY_V"]
        }
    ]
}

class ProfileManager:
    """Manages active settings and configuration profiles for MK75."""

    def __init__(self, config_dir: Optional[str] = None):
        if not config_dir:
            config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
            config_dir = os.path.join(config_home, "lingbao-mk75")
        
        self.config_dir = config_dir
        self.config_file = os.path.join(self.config_dir, "profile.json")
        self.profile: Dict[str, Any] = dict(DEFAULT_PROFILE)
        self._change_listeners: List[Callable[[Dict[str, Any]], None]] = []

        self.ensure_config_dir()
        self.load()

    def ensure_config_dir(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create config dir {self.config_dir}: {e}")

    def add_listener(self, listener: Callable[[Dict[str, Any]], None]):
        self._change_listeners.append(listener)

    def _notify(self):
        for cb in self._change_listeners:
            try:
                cb(self.profile)
            except Exception as e:
                logger.error(f"Error calling profile change listener: {e}")

    def load(self) -> bool:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.profile = data
                    logger.info(f"Loaded profile from {self.config_file}")
                    self._notify()
                    return True
            except Exception as e:
                logger.error(f"Failed to load profile from {self.config_file}: {e}")
        
        # Fallback to default
        self.profile = dict(DEFAULT_PROFILE)
        self.save()
        return False

    def save(self) -> bool:
        try:
            self.ensure_config_dir()
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.profile, f, indent=2)
            logger.info(f"Saved profile to {self.config_file}")
            self._notify()
            return True
        except Exception as e:
            logger.error(f"Failed to save profile to {self.config_file}: {e}")
            return False

    def export_to_file(self, filepath: str) -> bool:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.profile, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to export profile to {filepath}: {e}")
            return False

    def import_from_file(self, filepath: str) -> bool:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.profile = data
                self.save()
                return True
        except Exception as e:
            logger.error(f"Failed to import profile from {filepath}: {e}")
            return False

    # --- Key Remap Helpers ---
    def get_remapping(self, key_id: str) -> Optional[Dict[str, Any]]:
        return self.profile.get("remapping", {}).get(key_id)

    def set_key_remap(self, key_id: str, target_key: str):
        if "remapping" not in self.profile:
            self.profile["remapping"] = {}
        self.profile["remapping"][key_id] = {
            "type": "key",
            "target": target_key
        }
        self.save()

    def set_remapping(self, key_id: str, remap_dict: Dict[str, Any]):
        if "remapping" not in self.profile:
            self.profile["remapping"] = {}
        self.profile["remapping"][key_id] = remap_dict
        self.save()

    def set_macro_remap(self, key_id: str, macro_id: str):
        if "remapping" not in self.profile:
            self.profile["remapping"] = {}
        self.profile["remapping"][key_id] = {
            "type": "macro",
            "macro_id": macro_id
        }
        self.save()

    def set_command_remap(self, key_id: str, command: str):
        if "remapping" not in self.profile:
            self.profile["remapping"] = {}
        self.profile["remapping"][key_id] = {
            "type": "command",
            "command": command
        }
        self.save()

    def clear_remap(self, key_id: str):
        if "remapping" in self.profile and key_id in self.profile["remapping"]:
            del self.profile["remapping"][key_id]
            self.save()

    # --- Lighting Helpers ---
    def get_lighting(self) -> Dict[str, Any]:
        return self.profile.get("lighting", dict(DEFAULT_PROFILE["lighting"]))

    def update_lighting(self, **kwargs):
        if "lighting" not in self.profile:
            self.profile["lighting"] = dict(DEFAULT_PROFILE["lighting"])
        self.profile["lighting"].update(kwargs)
        self.save()

    # --- Macro Helpers ---
    def get_macros(self) -> List[Dict[str, Any]]:
        return self.profile.get("macros", [])

    def save_macro(self, macro_data: Dict[str, Any]):
        if "macros" not in self.profile:
            self.profile["macros"] = []
        macros = self.profile["macros"]
        for idx, m in enumerate(macros):
            if m.get("id") == macro_data.get("id"):
                macros[idx] = macro_data
                self.save()
                return
        macros.append(macro_data)
        self.save()

    def delete_macro(self, macro_id: str):
        if "macros" in self.profile:
            self.profile["macros"] = [m for m in self.profile["macros"] if m.get("id") != macro_id]
            self.save()
