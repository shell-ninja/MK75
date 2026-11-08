"""
Device detector for Lingbao MK75 and compatible OEM boards.
Discovers USB devices, input event nodes (/dev/input/event*),
raw HID nodes (/dev/hidraw*), connection modes, and permission status.
"""

import os
import glob
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# Known Vendor & Product IDs
KNOWN_DEVICES = [
    {"vid": 0x3554, "pid": 0xFA09, "name": "Lingbao MK75 / Compx 2.4G Receiver", "default_mode": "2.4GHz Wireless"},
    {"vid": 0x3554, "pid": 0xFA08, "name": "Lingbao MK75 / Compx Wired", "default_mode": "USB-C Wired"},
    {"vid": 0x3554, "pid": 0xFA10, "name": "Lingbao MK75 Wireless Variant", "default_mode": "2.4GHz Wireless"},
    {"vid": 0x258A, "pid": 0x010C, "name": "Aula F75 / SinoWealth OEM", "default_mode": "USB-C Wired"},
    {"vid": 0x258A, "pid": 0x2012, "name": "Leobog Hi75 / SinoWealth OEM", "default_mode": "USB-C Wired"},
    {"vid": 0x258A, "pid": 0x0049, "name": "SinoWealth 75% Keyboard", "default_mode": "USB-C Wired"},
    {"vid": 0x0C45, "pid": 0x8513, "name": "EVision / Sonix OEM Keyboard", "default_mode": "USB-C Wired"},
    {"vid": 0x320F, "pid": 0x5088, "name": "Ajazz / BY Tech OEM Keyboard", "default_mode": "USB-C Wired"},
]

@dataclass
class DeviceInfo:
    detected: bool = False
    name: str = "Unknown / Not Detected"
    vid: int = 0
    pid: int = 0
    connection_type: str = "Disconnected"  # USB-C Wired, 2.4GHz Wireless, Bluetooth
    event_paths: List[str] = field(default_factory=list)      # e.g. ["/dev/input/event3", "/dev/input/event5"]
    hidraw_paths: List[str] = field(default_factory=list)     # e.g. ["/dev/hidraw0", "/dev/hidraw1"]
    primary_hidraw: Optional[str] = None
    uinput_accessible: bool = False
    event_accessible: bool = False
    hidraw_accessible: bool = False
    details: Dict[str, str] = field(default_factory=dict)

class MK75Detector:
    """Scans and monitors system hardware for the Lingbao MK75 keyboard."""

    @classmethod
    def scan(cls) -> DeviceInfo:
        info = DeviceInfo()
        info.uinput_accessible = os.access("/dev/uinput", os.W_OK)

        # 1. Check /proc/bus/input/devices for Compx / Lingbao / target boards
        input_devices = cls._parse_proc_input_devices()
        target_input = None

        for dev in input_devices:
            vid = dev.get("vendor", 0)
            pid = dev.get("product", 0)
            name = dev.get("name", "")

            # Check matching known VIDs/PIDs or keywords
            matched_known = next((k for k in KNOWN_DEVICES if k["vid"] == vid and k["pid"] == pid), None)
            name_lower = name.lower()
            is_candidate = (
                matched_known is not None or
                "compx" in name_lower or
                "lingbao" in name_lower or
                "mk75" in name_lower or
                ("2.4g wireless receiver" in name_lower and vid in (0x3554, 0x258a))
            )

            if is_candidate:
                if not target_input:
                    target_input = dev
                    info.detected = True
                    info.vid = vid
                    info.pid = pid
                    info.name = matched_known["name"] if matched_known else name
                    
                    # Determine connection mode
                    if "wireless" in name_lower or "2.4g" in name_lower or (matched_known and "Wireless" in matched_known["default_mode"]):
                        info.connection_type = "2.4GHz Wireless"
                    elif "bluetooth" in name_lower or dev.get("bus", "") == "0005":
                        info.connection_type = "Bluetooth"
                    else:
                        info.connection_type = "USB-C Wired"

                # Collect all event handlers for this device
                for handler in dev.get("handlers", []):
                    if handler.startswith("event"):
                        event_path = f"/dev/input/{handler}"
                        if event_path not in info.event_paths:
                            info.event_paths.append(event_path)

        # 2. Check /sys/class/hidraw to locate matching hidraw nodes
        cls._scan_hidraw(info)

        # 3. Check access permissions
        if info.event_paths:
            info.event_accessible = any(os.access(p, os.R_OK) for p in info.event_paths)
        if info.hidraw_paths:
            info.hidraw_accessible = any(os.access(p, os.W_OK) for p in info.hidraw_paths)

        return info

    @classmethod
    def _parse_proc_input_devices(cls) -> List[Dict]:
        """Parses /proc/bus/input/devices into structured dictionaries."""
        devices = []
        if not os.path.exists("/proc/bus/input/devices"):
            return devices

        try:
            with open("/proc/bus/input/devices", "r") as f:
                content = f.read()
        except Exception:
            return devices

        blocks = content.strip().split("\n\n")
        for block in blocks:
            dev = {}
            for line in block.splitlines():
                line = line.strip()
                if line.startswith("I:"):
                    # I: Bus=0003 Vendor=3554 Product=fa09 Version=0111
                    for match in re.finditer(r'([A-Za-z]+)=([0-9a-fA-F]+)', line):
                        key = match.group(1).lower()
                        val = int(match.group(2), 16)
                        dev[key] = val
                elif line.startswith("N: Name="):
                    dev["name"] = line.split("Name=", 1)[1].strip('"')
                elif line.startswith("H: Handlers="):
                    dev["handlers"] = line.split("Handlers=", 1)[1].strip().split()
                elif line.startswith("S: Sysfs="):
                    dev["sysfs"] = line.split("Sysfs=", 1)[1].strip()
            if dev:
                devices.append(dev)
        return devices

    @classmethod
    def _scan_hidraw(cls, info: DeviceInfo):
        """Scans /sys/class/hidraw to link hidraw nodes to the detected device."""
        hidraw_dirs = sorted(glob.glob("/sys/class/hidraw/hidraw*"))
        for hidraw_dir in hidraw_dirs:
            hidraw_node = f"/dev/{os.path.basename(hidraw_dir)}"
            uevent_path = os.path.join(hidraw_dir, "device", "uevent")
            if not os.path.exists(uevent_path):
                continue

            try:
                with open(uevent_path, "r") as f:
                    uevent_text = f.read()

                # HID_ID=0003:00003554:0000FA09
                match = re.search(r'HID_ID=[0-9A-Fa-f]+:([0-9A-Fa-f]+):([0-9A-Fa-f]+)', uevent_text)
                if match:
                    node_vid = int(match.group(1), 16)
                    node_pid = int(match.group(2), 16)
                    if (info.vid and node_vid == info.vid and node_pid == info.pid) or (node_vid == 0x3554 and node_pid == 0xFA09):
                        info.hidraw_paths.append(hidraw_node)
                        # Interface 1 or higher is typically the feature report / lighting interface
                        if "input1" in uevent_text or not info.primary_hidraw:
                            info.primary_hidraw = hidraw_node
            except Exception:
                pass

        if info.hidraw_paths and not info.primary_hidraw:
            # Pick the second interface if available (e.g. hidraw1) as it hosts vendor reports
            info.primary_hidraw = info.hidraw_paths[-1]

    @classmethod
    def get_udev_check_summary(cls, info: DeviceInfo) -> Dict[str, Any]:
        """Provides human-readable diagnostic checks for the UI."""
        return {
            "device_detected": info.detected,
            "device_name": info.name,
            "vid_pid": f"{info.vid:04X}:{info.pid:04X}" if info.vid else "N/A",
            "connection": info.connection_type,
            "uinput_ok": info.uinput_accessible,
            "event_ok": info.event_accessible,
            "hidraw_ok": info.hidraw_accessible,
            "event_nodes": ", ".join(info.event_paths) if info.event_paths else "None found",
            "hidraw_nodes": ", ".join(info.hidraw_paths) if info.hidraw_paths else "None found",
            "all_permissions_ok": (info.uinput_accessible and info.event_accessible and info.hidraw_accessible),
        }
