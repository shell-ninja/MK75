#!/usr/bin/env python3
"""
Lingbao MK75 Linux Controller
Native, minimal, dark-mode Linux GUI application to control and configure
the Lingbao MK75 mechanical keyboard (81-key, 75% layout, rotary knob, tri-mode).
"""

import sys
import os
import signal
import logging
import argparse

# Ensure Qt Wayland and X11 compatibility
if "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QIcon, QPalette, QColor
from PySide6.QtWidgets import QApplication

from core.profile_manager import ProfileManager
from core.macro_engine import MacroEngine
from core.evdev_remapper import EvdevRemapper
from core.hid_controller import MK75HardwareController
from core.device_detector import MK75Detector
from ui.main_window import MainWindow

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("MK75.Main")

def main():
    parser = argparse.ArgumentParser(description="Lingbao MK75 Linux Controller & Remapper")
    parser.add_argument("--daemon", "-d", action="store_true", help="Run headlessly as background remapping daemon without GUI")
    parser.add_argument("--minimized", "-m", action="store_true", help="Start minimized to system tray")
    parser.add_argument("--rescan", "-r", action="store_true", help="Scan and display detected keyboard nodes and exit")
    parser.add_argument("--config-dir", "-c", type=str, default=None, help="Custom configuration directory")
    args = parser.parse_args()

    if args.rescan:
        info = MK75Detector.scan()
        summary = MK75Detector.get_udev_check_summary(info)
        print("==================================================")
        print(" Lingbao MK75 Hardware & Permission Diagnostics")
        print("==================================================")
        for k, v in summary.items():
            print(f" {k:<20}: {v}")
        print("==================================================")
        sys.exit(0)

    # Enforce single application instance to prevent conflicting kernel grabs
    import fcntl
    lock_dir = args.config_dir or os.path.expanduser("~/.config/lingbao-mk75")
    os.makedirs(lock_dir, exist_ok=True)
    lock_file = open(os.path.join(lock_dir, "mk75.lock"), "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, BlockingIOError):
        logger.warning("Another instance of MK75 is already running. Exiting.")
        sys.exit(0)

    logger.info("Initializing Lingbao MK75 Linux Controller...")

    # Core backends
    profile_manager = ProfileManager(config_dir=args.config_dir)
    macro_engine = MacroEngine()
    hid_controller = MK75HardwareController()
    remapper = EvdevRemapper(profile_manager, macro_engine)

    # Initial hardware discovery & connection
    device_info = MK75Detector.scan()
    logger.info(f"Hardware scan: detected={device_info.detected}, name='{device_info.name}', mode='{device_info.connection_type}'")

    if device_info.detected:
        hid_controller.connect(device_info)
        remapper.start_remapper(device_info)

    # Headless daemon mode
    if args.daemon:
        logger.info("Running in headless daemon mode. Press Ctrl+C to terminate.")
        def daemon_stop(signum, frame):
            logger.info("Stopping daemon...")
            remapper.stop_remapper()
            hid_controller.disconnect()
            sys.exit(0)
        signal.signal(signal.SIGINT, daemon_stop)
        signal.signal(signal.SIGTERM, daemon_stop)
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            daemon_stop(None, None)

    # Qt GUI Mode
    QCoreApplication.setApplicationName("MK75")
    QCoreApplication.setOrganizationName("MK75")

    app = QApplication(sys.argv)
    app.setDesktopFileName("mk75")

    # Enforce deep dark palette across all platform styles and popup delegates
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor("#0B0D13"))
    dark_palette.setColor(QPalette.WindowText, QColor("#F1F3F7"))
    dark_palette.setColor(QPalette.Base, QColor("#131620"))
    dark_palette.setColor(QPalette.AlternateBase, QColor("#171A24"))
    dark_palette.setColor(QPalette.ToolTipBase, QColor("#131620"))
    dark_palette.setColor(QPalette.ToolTipText, QColor("#F1F3F7"))
    dark_palette.setColor(QPalette.Text, QColor("#F1F3F7"))
    dark_palette.setColor(QPalette.Button, QColor("#171A24"))
    dark_palette.setColor(QPalette.ButtonText, QColor("#F1F3F7"))
    dark_palette.setColor(QPalette.BrightText, QColor("#FFFFFF"))
    dark_palette.setColor(QPalette.Highlight, QColor("#6366F1"))
    dark_palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(dark_palette)

    if os.path.exists(os.path.join(os.path.dirname(__file__), "assets", "mk75.png")):
        app.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "assets", "mk75.png")))
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow(
        profile_manager=profile_manager,
        remapper=remapper,
        hid_controller=hid_controller,
        macro_engine=macro_engine
    )

    if not args.minimized:
        window.show()
    else:
        logger.info("Application started minimized to system tray.")

    # Handle Ctrl+C cleanly
    def sigint_handler(signum, frame):
        logger.info("Received interrupt signal. Exiting gracefully...")
        remapper.stop_remapper()
        hid_controller.disconnect()
        app.quit()

    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigint_handler)

    # Timer to allow Python to process POSIX signals
    from PySide6.QtCore import QTimer
    sig_timer = QTimer()
    sig_timer.timeout.connect(lambda: None)
    sig_timer.start(500)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
