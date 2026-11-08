#!/usr/bin/env bash
# setup.sh - Environment, udev rules, icons, and launcher installer for MK75
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UDEV_RULE_FILE="99-lingbao-mk75.rules"
UDEV_DEST="/etc/udev/rules.d/${UDEV_RULE_FILE}"

echo "=========================================================="
echo " MK75 Linux Controller - Setup, Permissions & App Launcher"
echo "=========================================================="

# 1. Install udev rules
if [ -f "${SCRIPT_DIR}/${UDEV_RULE_FILE}" ]; then
    echo "[*] Installing udev rules to ${UDEV_DEST}..."
    if [ "$EUID" -ne 0 ]; then
        echo "    Elevating with sudo to copy udev rules and load uinput module..."
        sudo cp "${SCRIPT_DIR}/${UDEV_RULE_FILE}" "${UDEV_DEST}"
        sudo modprobe uinput || true
        sudo udevadm control --reload-rules
        sudo udevadm trigger
    else
        cp "${SCRIPT_DIR}/${UDEV_RULE_FILE}" "${UDEV_DEST}"
        modprobe uinput || true
        udevadm control --reload-rules
        udevadm trigger
    fi
    echo "[OK] udev rules installed and reloaded successfully!"
    echo "     (If keyboard is plugged in, replug 2.4G dongle or USB-C cable)"
fi

# 2. Check or create Python virtual environment
if [ ! -d "${SCRIPT_DIR}/.venv" ]; then
    echo "[*] Creating Python virtual environment in .venv..."
    python3 -m venv "${SCRIPT_DIR}/.venv"
fi

echo "[*] Installing Python dependencies..."
"${SCRIPT_DIR}/.venv/bin/pip" install --upgrade pip --quiet
"${SCRIPT_DIR}/.venv/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt" --quiet

# 3. Install App Icon & Desktop Launcher Entry (App Name: MK75)
echo "[*] Installing Desktop Application Entry ('MK75') and Icons..."
ICON_DIR_256="${HOME}/.local/share/icons/hicolor/256x256/apps"
ICON_DIR_SVG="${HOME}/.local/share/icons/hicolor/scalable/apps"
APPS_DIR="${HOME}/.local/share/applications"

mkdir -p "${ICON_DIR_256}" "${ICON_DIR_SVG}" "${APPS_DIR}"

if [ -f "${SCRIPT_DIR}/assets/mk75.png" ]; then
    cp "${SCRIPT_DIR}/assets/mk75.png" "${ICON_DIR_256}/mk75.png"
fi
if [ -f "${SCRIPT_DIR}/assets/mk75.svg" ]; then
    cp "${SCRIPT_DIR}/assets/mk75.svg" "${ICON_DIR_SVG}/mk75.svg"
fi

cat <<EOF > "${APPS_DIR}/mk75.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=MK75
GenericName=Keyboard Controller
Comment=Native Linux Controller & Remapper for Lingbao MK75 Keyboard
Exec=${SCRIPT_DIR}/run.sh
Icon=mk75
Terminal=false
Categories=Utility;Settings;HardwareSettings;
Keywords=keyboard;remap;rgb;lighting;knob;mk75;lingbao;
StartupWMClass=mk75
EOF

chmod +x "${APPS_DIR}/mk75.desktop"

# Refresh desktop database & icon cache
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APPS_DIR}" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "[OK] MK75 application launcher and icons installed."

echo "=========================================================="
echo " Setup complete!"
echo " You can now search for 'MK75' in your app launcher (Rofi/Wofi/GNOME)"
echo " Or run directly with: ./run.sh"
echo "=========================================================="
