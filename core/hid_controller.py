"""
Hardware-Level HID Controller for Lingbao MK75 & Sister OEM Keyboards (AULA F75, Leobog, Compx).
Communicates directly over /dev/hidraw configuration endpoints using the reverse-engineered
20-byte Report 0x13 wireless protocol and Report 0x06 feature report protocol.
"""

import os
import glob
import time
import fcntl
import select
import logging
from typing import Dict, Any, Optional, List, Tuple

from core.device_detector import DeviceInfo, MK75Detector

logger = logging.getLogger("MK75.HardwareController")

# --- Protocol & Command Byte Constants ---
REPORT_ID_WIRELESS = 0x13
PACKET_LEN_WIRELESS = 20
CHUNK_LEN = 14

REPORT_ID_FEATURE = 0x06
FEATURE_LEN_8 = 8

# Protocol Commands
CMD_SET_MATRIX  = 0x01   # Keymap (sub = 0: Base, 1: Fn)
CMD_SET_CUSTOM  = 0x02   # Per-key RGB color table (378 bytes planar)
CMD_SET_MACRO   = 0x03   # Hardware macros
CMD_SET_LED     = 0x04   # 128-byte LED block (effects, brightness, speed, side glow, knob)
CMD_RESET       = 0x06   # Factory reset
CMD_SET_PALETTE = 0x09   # 7-color custom palette
CMD_PROFILE     = 0x0A   # Profile slots
CMD_LIVE        = 0x88   # Real-time streaming animation frame
READ_FLAG       = 0x40   # Read command = CMD | 0x40

# 128-byte LED Config Block Layout
LED_LEN = 128
LED_MAGIC = b"\x5a\xa5"
LED_EFFECT_OFFSET   = 10
LED_WIN_LOCK_OFFSET = 15
LED_SIDE_MODE_OFFSET= 18
LED_SLEEP_OFFSET    = 24
LED_KNOB_MODE_OFFSET= 26
LED_OS_MODE_OFFSET  = 27
LED_SLOTS_OFFSET    = 58

# 16 Hardware RGB Effects Mapping
RGB_EFFECTS = [
    {"id": 1,  "name": "Static Color",           "description": "Solid uniform color across all keys"},
    {"id": 2,  "name": "Breathing",              "description": "Smooth fade in and out"},
    {"id": 3,  "name": "Spectrum / Cycle",       "description": "Smooth color spectrum cycle"},
    {"id": 4,  "name": "Ripple Row",             "description": "Reactive beam expands along struck key's row"},
    {"id": 5,  "name": "Raindrops",              "description": "Random sporadic raindrops across keys"},
    {"id": 6,  "name": "Rainbow Wave",           "description": "Flowing directional rainbow waves"},
    {"id": 7,  "name": "Ripple Board",           "description": "Expanding concentric ripples over entire board"},
    {"id": 8,  "name": "Twinkle / Starlight",    "description": "Random twinkling starbursts"},
    {"id": 10, "name": "Snake",                  "description": "Retro slithering light snake"},
    {"id": 11, "name": "Stream",                 "description": "Left to right cascading light trail"},
    {"id": 12, "name": "Reactive Single",        "description": "Key illuminates immediately when struck"},
    {"id": 13, "name": "Center Wave",            "description": "Wave slides out from center to both edges"},
    {"id": 15, "name": "Rainbow Wheel",          "description": "Rotating pinwheel color spectrum"},
    {"id": 16, "name": "Waterfall",              "description": "Vertical cascading light matrix"},
    {"id": 17, "name": "Center Flash",           "description": "Fast strobe flicker from center outwards"},
    {"id": 32, "name": "Custom / Stealth Off",   "description": "Per-key canvas table or all LEDs off"},
]

# Side glow modes
SIDE_MODES = ["Off", "Fill", "Breathing", "Static"]

POLLING_RATES = {
    "125Hz": 0x08,
    "250Hz": 0x04,
    "500Hz": 0x02,
    "1000Hz": 0x01,
}

# ioctl helpers for Linux hidraw
def HIDIOCSFEATURE(length):
    return (3 << 30) | (ord('H') << 8) | 0x06 | (length << 16)

def HIDIOCGFEATURE(length):
    return (3 << 30) | (ord('H') << 8) | 0x07 | (length << 16)

def checksum(pkt: bytes) -> int:
    """Calculates sum of first 19 bytes & 0xFF for Report 0x13."""
    return sum(pkt[:19]) & 0xFF

def build_packet_13(cmd: int, total: int, index: int, sub: int, chunk: bytes) -> bytes:
    """Crafts 20-byte Report 0x13 packet with correct header and checksum."""
    b = bytearray(PACKET_LEN_WIRELESS)
    b[0] = REPORT_ID_WIRELESS
    b[1] = cmd
    b[2] = total
    b[3] = index
    b[4] = ((sub << 4) | len(chunk)) & 0xFF
    b[5:5 + len(chunk)] = chunk
    b[19] = checksum(b)
    return bytes(b)

def split_packets_13(cmd: int, sub: int, data: bytes) -> List[bytes]:
    """Splits arbitrary binary data into 14-byte chunk packets."""
    chunks = [data[i:i + CHUNK_LEN] for i in range(0, len(data), CHUNK_LEN)] or [b""]
    return [build_packet_13(cmd, len(chunks), i, sub, c) for i, c in enumerate(chunks)]

class MK75HardwareController:
    """Controls Lingbao MK75 hardware features via USB HID feature reports."""

    def __init__(self, vid: int = 0x3554, pid: int = 0xFA09):
        self.vid = vid
        self.pid = pid
        self.hidraw_path: Optional[str] = None
        self.hidraw_fd: Optional[int] = None
        self.connected = False
        self.packet_history: List[Dict[str, Any]] = []
        self.last_battery_pct: Optional[int] = 72

    def connect(self, device_info: Optional[DeviceInfo] = None) -> bool:
        """Finds and opens the exact hidraw vendor configuration channel."""
        if self.connected and self.hidraw_fd is not None:
            return True

        if not device_info:
            device_info = MK75Detector.scan()

        target_node = self._locate_vendor_channel() or (device_info.primary_hidraw if device_info else None)
        if not target_node:
            logger.error("Could not locate MK75 vendor configuration channel.")
            return False

        try:
            self.hidraw_path = target_node
            self.hidraw_fd = os.open(target_node, os.O_RDWR | os.O_NONBLOCK)
            self.connected = True
            logger.info(f"Connected to MK75 hardware channel at {target_node}")
            return True
        except Exception as e:
            logger.error(f"Failed to open {target_node}: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if self.hidraw_fd is not None:
            try:
                os.close(self.hidraw_fd)
            except Exception:
                pass
            self.hidraw_fd = None
        self.connected = False

    def _locate_vendor_channel(self) -> Optional[str]:
        """Locates the hidraw node matching Usage Page 0xFF02 / Report ID 0x13."""
        marker = bytes([0x06, 0x02, 0xFF, 0x09, 0x02, 0xA1, 0x01, 0x85, 0x13])
        for sys_dir in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
            desc_path = os.path.join(sys_dir, "device", "report_descriptor")
            try:
                with open(desc_path, "rb") as f:
                    if marker in f.read():
                        return f"/dev/{os.path.basename(sys_dir)}"
            except Exception:
                pass
        return None

    def _record_packet(self, direction: str, payload: bytes, success: bool, note: str = ""):
        hex_dump = " ".join(f"{b:02X}" for b in payload)
        record = {
            "timestamp": time.strftime("%H:%M:%S"),
            "direction": direction,
            "length": len(payload),
            "hex": hex_dump,
            "success": success,
            "note": note
        }
        self.packet_history.append(record)
        if len(self.packet_history) > 100:
            self.packet_history.pop(0)

    def set_lighting_effect(self, effect_id: int, brightness: int = 3, speed: int = 2,
                            rgb: Tuple[int, int, int] = (99, 102, 241),
                            side_glow: bool = True) -> bool:
        """
        Sends hardware lighting command.
        Uses the proven 128-byte LedConfig block across 10 packets on Report 0x13,
        AND dual-writes to Report 0x06 feature report for instant application.
        """
        if not self.connected and not self.connect():
            return False

        # Scale parameters
        # UI brightness: 0-4 -> scaled to 0-9 (0 = off)
        scaled_brightness = max(0, min(9, int(brightness * 2.25)))
        # UI speed: 0-4
        scaled_speed = max(0, min(4, speed))
        # Map RGB to closest palette index (0: red, 1: green, 2: blue, 3: yellow, 4: purple, 5: cyan, 6: white, 7: multi)
        color_idx = self._rgb_to_palette_idx(rgb)

        hw_effect = effect_id
        if hw_effect not in [e["id"] for e in RGB_EFFECTS]:
            hw_effect = 6  # Default Rainbow Wave

        # 1. Build the 128-byte LedConfig block
        raw = bytearray(LED_LEN)
        raw[126:128] = LED_MAGIC
        raw[LED_EFFECT_OFFSET] = hw_effect
        raw[LED_SIDE_MODE_OFFSET] = 1 if side_glow else 0
        raw[LED_KNOB_MODE_OFFSET] = 0  # media mode
        raw[LED_OS_MODE_OFFSET]   = 0  # windows mode
        raw[LED_SLEEP_OFFSET]     = 4  # 2 min sleep timer

        # Configure effect slot at 58 + 2 * (hw - 1)
        if 1 <= hw_effect <= 34:
            slot_off = LED_SLOTS_OFFSET + 2 * (hw_effect - 1)
            raw[slot_off] = scaled_brightness
            raw[slot_off + 1] = (scaled_speed << 4) | color_idx

        # 2. Transmit via Report 0x13 (10 packets of 20 bytes each)
        ok_wireless = True
        pkts = split_packets_13(CMD_SET_LED, 0, bytes(raw))
        for p in pkts:
            try:
                os.write(self.hidraw_fd, p)
                self._record_packet("OUT (0x13)", p, True, f"LED block chunk")
                time.sleep(0.012)
            except Exception as e:
                logger.error(f"Failed to write 0x13 packet: {e}")
                self._record_packet("OUT (0x13)", p, False, str(e))
                ok_wireless = False

        # 3. Complementary write on Report 0x06 Feature Report
        try:
            buf6 = bytearray(8)
            buf6[0] = REPORT_ID_FEATURE
            buf6[1] = 0x04
            buf6[2] = hw_effect
            buf6[3] = int((scaled_brightness / 9.0) * 100)
            buf6[4] = int((scaled_speed / 4.0) * 100)
            buf6[5] = rgb[0]
            buf6[6] = rgb[1]
            buf6[7] = rgb[2]
            fcntl.ioctl(self.hidraw_fd, HIDIOCSFEATURE(8), buf6)
            self._record_packet("OUT (0x06)", bytes(buf6), True, "Feature report 0x06")
        except Exception as e:
            logger.warning(f"Feature report 0x06 ioctl notice: {e}")

        logger.info(f"Applied lighting: hw_effect={hw_effect}, bright={scaled_brightness}/9, speed={scaled_speed}, rgb={rgb}")
        return ok_wireless

    def turn_off_backlight(self) -> bool:
        """
        Completely turns off keyboard LEDs and side glow strips.
        Sets hardware brightness to 0 and switches to stealth effect (32).
        """
        logger.info("Sending command to turn off keyboard backlight and side glow...")
        return self.set_lighting_effect(effect_id=32, brightness=0, speed=0, rgb=(0, 0, 0), side_glow=False)

    def turn_on_backlight(self, effect_id: int = 6, brightness: int = 3, speed: int = 2,
                          rgb: Tuple[int, int, int] = (99, 102, 241), side_glow: bool = True) -> bool:
        """Restores keyboard lighting."""
        logger.info(f"Turning on keyboard backlight (effect={effect_id}, brightness={brightness})...")
        return self.set_lighting_effect(effect_id=effect_id, brightness=brightness, speed=speed, rgb=rgb, side_glow=side_glow)

    def set_side_glow(self, enabled: bool, mode: int = 1) -> bool:
        """Sets side RGB light strip mode."""
        return self.set_lighting_effect(effect_id=6, side_glow=enabled)

    def set_polling_rate(self, rate_name: str) -> bool:
        """Sets hardware polling rate."""
        rates = {"125Hz": 0x08, "250Hz": 0x04, "500Hz": 0x02, "1000Hz": 0x01}
        val = rates.get(rate_name, 0x01)
        pkt = build_packet_13(0x0C, 1, 0, 0, bytes([val]))
        try:
            os.write(self.hidraw_fd, pkt)
            self._record_packet("OUT (0x13)", pkt, True, f"Polling rate: {rate_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to set polling rate: {e}")
            return False

    def send_raw_hex(self, hex_string: str, report_id: int = REPORT_ID_WIRELESS) -> bool:
        """Sends arbitrary user hex string for testing & sniffing."""
        if not self.connected and not self.connect():
            return False

        clean_hex = "".join(c for c in hex_string if c in "0123456789ABCDEFabcdef")
        if not clean_hex:
            return False

        try:
            payload = bytes.fromhex(clean_hex)
            if report_id == REPORT_ID_FEATURE or len(payload) == 8:
                buf = bytearray(8)
                buf[:len(payload)] = payload
                buf[0] = REPORT_ID_FEATURE
                fcntl.ioctl(self.hidraw_fd, HIDIOCSFEATURE(8), buf)
                self._record_packet("OUT (0x06)", bytes(buf), True, "Custom hex feature")
                return True
            else:
                # 20-byte Report 0x13
                buf = bytearray(20)
                buf[:len(payload)] = payload
                buf[0] = REPORT_ID_WIRELESS
                buf[19] = checksum(buf)
                os.write(self.hidraw_fd, buf)
                self._record_packet("OUT (0x13)", bytes(buf), True, "Custom hex 0x13")
                return True
        except Exception as e:
            logger.error(f"Failed to send raw hex: {e}")
            return False

    def read_response(self, length: int = 64, timeout_ms: int = 300) -> Optional[bytes]:
        """Reads inbound response packet from the keyboard."""
        if not self.connected and not self.connect():
            return None

        try:
            if select.select([self.hidraw_fd], [], [], timeout_ms / 1000.0)[0]:
                data = os.read(self.hidraw_fd, length)
                if data:
                    self._record_packet("IN", data, True, f"Read {len(data)} bytes")
                    return data
        except Exception as e:
            logger.warning(f"Read error: {e}")

        return None

    def query_device_status(self) -> Optional[Dict[str, Any]]:
        """Queries 2.4GHz wireless dongle for keyboard status, active profile, and battery percentage."""
        if not self.connected and not self.connect():
            return None

        probe_pkt = bytearray(20)
        probe_pkt[0] = REPORT_ID_WIRELESS
        probe_pkt[1] = 0x4A
        probe_pkt[2] = 0x01
        probe_pkt[19] = checksum(probe_pkt)

        try:
            os.write(self.hidraw_fd, probe_pkt)
            self._record_packet("OUT (0x13)", bytes(probe_pkt), True, "Query device status (0x4A)")
            resp = self.read_response(64, timeout_ms=300)
            if resp and len(resp) >= 7 and resp[0] == REPORT_ID_WIRELESS and resp[1] == 0x4A:
                profile_slot = resp[2]
                mode_byte = resp[4]
                mode_str = "2.4GHz Wireless" if mode_byte == 2 else ("Wired" if mode_byte == 1 else "Bluetooth")
                battery_pct = resp[5]
                is_online = (resp[6] == 1)
                if battery_pct > 0:
                    self.last_battery_pct = battery_pct

                return {
                    "online": is_online,
                    "profile_slot": profile_slot,
                    "mode": mode_str,
                    "battery": battery_pct,
                    "cached": False,
                }
        except Exception as e:
            logger.debug(f"Failed to query device status: {e}")

        if self.last_battery_pct is not None:
            return {
                "online": False,
                "profile_slot": 1,
                "mode": "2.4GHz Wireless",
                "battery": self.last_battery_pct,
                "cached": True,
            }

        return None

    def _rgb_to_palette_idx(self, rgb: Tuple[int, int, int]) -> int:
        """Finds closest palette color index (0: red, 1: green, 2: blue, 3: yellow, 4: purple, 5: cyan, 6: white, 7: multi)."""
        r, g, b = rgb
        if max(r, g, b) - min(r, g, b) < 25 and max(r, g, b) > 180:
            return 6  # White
        if r > 180 and g > 180 and b < 80:
            return 3  # Yellow
        if r > 180 and b > 180 and g < 80:
            return 4  # Purple
        if g > 180 and b > 180 and r < 80:
            return 5  # Cyan
        if r >= g and r >= b:
            return 0  # Red
        if g >= r and g >= b:
            return 1  # Green
        if b >= r and b >= g:
            return 2  # Blue
        return 7      # Multicolor
