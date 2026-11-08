# Lingbao MK75 Linux Controller (v1.0.0)

A native, modern, ultra-clean Linux GUI application and OS-level remapper for the **Lingbao MK75** (81-key, 75% mechanical keyboard with multifunction rotary knob and tri-mode connectivity).

Built with **Python 3**, **PySide6 (Qt6)**, **evdev**, and direct **`/dev/hidraw`** communication, designed specifically for Wayland and X11 on modern Linux distributions (Arch, Fedora, Ubuntu, Debian, etc.).

---

## Features

- **Hero 75% Keyboard Visualizer:** Accurate 81-key physical layout canvas with interactive rotary knob, real-time keypress highlighting, and reactive side-glow RGB strips.
- **Backlight Power & Stealth Off:** One-click master toggle and dedicated "Turn Off Backlight" control to instantly shut off key matrix LEDs and side chassis glow without disconnecting.
- **Physical Key Capture & Instant Remapping:** Click any key or the rotary knob and press any physical key on your keyboard to instantly record and bind it, or use one-click media chips (`Vol +`, `Vol -`, `Mute`, `Brightness`, `Play/Pause`, `Next`).
- **OS-Level Key & Knob Remapper (`evdev` & `uinput`):** Intercepts hardware key events and rotary knob turns/presses and maps them to custom keys, macros, or arbitrary Linux shell commands without latency.
- **Interactive Multi-Key Shortcut Builder:** Supports complex combinations (`Ctrl+Shift+T`, `Ctrl+Alt+T`, `Super+Space`) with live modifier detection (`Ctrl`, `Shift`, `Alt`, `Super`) and clickable modifier toggle chips.
- **Live Wireless Battery Telemetry:** Reverse-engineered Compx 2.4GHz status protocol (Report ID `0x13`, Command `0x4A`) decoding real-time battery percentage from the keyboard MCU and displaying it in the header and device diagnostics.
- **Hardware-Level HID Controller (`/dev/hidraw`):** Controls the 16 hardware RGB lighting effects, brightness levels, animation speeds, and chassis side-glow strips over 20-byte Report `0x13` (checksummed) and 8-byte Report `0x06` channels.
- **Simplified 3-Mode Macro Builder:** Create one-click Key Shortcuts (with automatic modifier order and release), Text Expanders (auto-typing snippets), or Linux App Launchers (`kitty &`, screenshot tools, pactl, etc.).
- **Vector SVG Monochrome Icons:** Crisp, resolution-independent vector icons (Lucide-style) rendered via `QSvgRenderer`.
- **HID Packet Inspector & Sniffer:** Interactive protocol inspector to craft, send, and analyze raw USB feature reports over `/dev/hidraw` for protocol exploration.
- **System Tray Mode & Headless Daemon:** Runs as a background daemon when the window is closed so custom shortcuts and knob bindings stay active, with an included `systemd` user service.
- **Zero-Sudo udev Integration:** Includes drop-in `/etc/udev/rules.d/99-lingbao-mk75.rules` with logind ACL (`TAG+="uaccess"`) support.

---

## Directory Structure

```
mk75/
├── 99-lingbao-mk75.rules       # udev permissions rule for hidraw, uinput, and evdev
├── requirements.txt            # Python dependencies (PySide6, evdev, hidapi, pyusb)
├── setup.sh                    # Automated setup script (udev rules + virtualenv)
├── run.sh                      # One-click launcher script (Wayland/X11 auto-detect)
├── main.py                     # Entry point & application lifecycle
├── config/
│   ├── default_profile.json    # Default key mappings and lighting config
│   └── keycodes.py             # 81-key layout coordinates & evdev keycode maps
├── core/
│   ├── device_detector.py      # USB / sysfs / evdev / hidraw hardware discovery
│   ├── evdev_remapper.py       # Input interception & uinput virtual injection
│   ├── hid_controller.py       # Dual-channel HID controller & battery telemetry
│   ├── macro_engine.py         # Asynchronous Shortcut / Text / Command engine
│   └── profile_manager.py      # JSON profile persistence & synchronization
└── ui/
    ├── icons.py                # Crisp vector SVG icon library (Lucide-style)
    ├── theme.py                # Restrained obsidian dark theme styling & QSS
    ├── main_window.py          # Master window with sidebar, header, & battery badge
    └── widgets/
        ├── keyboard_visualizer.py  # Precision 81-key canvas + rotary knob
        ├── key_config_panel.py     # Remap drawer with physical key capture
        ├── lighting_view.py        # 16 RGB effects, speed/brightness, color swatch
        ├── macros_view.py          # Simplified 3-mode macro builder
        ├── device_view.py          # Hardware status, battery, & udev diagnostics
        └── inspector_view.py       # Live HID Packet Inspector / Tester & sniffer
```

---

## Quick Start

### 1. Install Dependencies & udev Rules

Run the automated setup script:
```bash
./setup.sh
```
*Note: The script will prompt for `sudo` once to install the udev rule into `/etc/udev/rules.d/` and reload `udevadm`.*

### 2. Run the Application

```bash
./run.sh
```
Or run directly from the virtual environment:
```bash
.venv/bin/python3 main.py
```

### 3. Background Daemon & Autostart (Optional)

To run the key and knob remapper headlessly in the background on system startup:

```bash
systemctl --user daemon-reload
systemctl --user enable --now lingbao-mk75.service
```

To check service status:
```bash
systemctl --user status lingbao-mk75.service
```

---

## Hardware Protocol Details

The Lingbao MK75 uses the **Compx / SinoWealth** controller architecture:

- **2.4GHz Wireless USB Dongle:** `VID 0x3554 / PID 0xFA09`
- **Wired USB-C:** `VID 0x3554 / PID 0xFA08` (or `0x258A:0x010C`)
- **Primary Control HID Node:** `/dev/hidraw1` (Report ID `0x13`, 20 bytes; Report ID `0x06`, 8 bytes)
- **Battery Status Query:** Sending packet `13 4A 01 00 00 ... 5E` over `/dev/hidraw1` returns byte 5 containing the battery percentage (`0x48` = 72%).
- **Checksum Calculation:** Byte 19 of every Report `0x13` wireless packet must equal `sum(packet[:19]) & 0xFF`.

---

## Rotary Knob Mapping

The Lingbao MK75 top-right rotary knob emits standard consumer control events:
- **Turn Clockwise (CW):** Configurable to Volume Up, Brightness Up, Workspace Next, or custom commands.
- **Turn Counter-Clockwise (CCW):** Configurable to Volume Down, Brightness Down, Workspace Prev, or custom commands.
- **Knob Push / Click:** Configurable to Mute, Play/Pause, or custom scripts.
