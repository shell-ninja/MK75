#!/usr/bin/env bash
# run.sh - Helper script to run Lingbao MK75 Linux Controller
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check virtual environment
if [ ! -d "${SCRIPT_DIR}/.venv" ]; then
    echo "[!] Virtual environment not found. Running setup.sh first..."
    "${SCRIPT_DIR}/setup.sh"
fi

# Prefer Wayland if running under Wayland, fallback to xcb
if [ -n "$WAYLAND_DISPLAY" ]; then
    export QT_QPA_PLATFORM="wayland;xcb"
fi

exec "${SCRIPT_DIR}/.venv/bin/python3" "${SCRIPT_DIR}/main.py" "$@"
