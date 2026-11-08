"""
RGB Lighting & Side-Glow Effects Control Panel.
Select from 16 hardware lighting effects, customize speed, brightness, and colors.
"""

from typing import Tuple
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QSlider, QComboBox, QCheckBox, QFrame,
    QColorDialog, QScrollArea, QListView
)

from core.hid_controller import RGB_EFFECTS, MK75HardwareController
from ui.icons import get_icon
from ui.theme import (
    BG_CARD, BORDER_COLOR, ACCENT_PRIMARY, ACCENT_SKY,
    ACCENT_EMERALD, TEXT_PRIMARY, TEXT_MUTED
)

# Vibrant preset palettes
PRESET_COLORS = [
    ("Indigo", "#6366F1"),
    ("Sky Blue", "#38BDF8"),
    ("Emerald", "#10B981"),
    ("Amber", "#F59E0B"),
    ("Rose", "#EF4444"),
    ("Purple", "#A855F7"),
    ("Teal", "#14B8A6"),
    ("Pure White", "#FFFFFF"),
]

class LightingView(QWidget):
    """View to configure RGB lighting effects, brightness, and side strips."""

    lighting_applied = Signal(dict)

    def __init__(self, profile_manager, hid_controller: MK75HardwareController, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.hid = hid_controller
        self.selected_color = QColor(99, 102, 241)

        self._build_ui()
        self._load_from_profile()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Title
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Lighting")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Configure hardware lighting effects, brightness, animation speed, and accent colors.")
        subtitle.setObjectName("SubtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        main_layout.addLayout(title_box)

        # Card Container
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(18)

        # 0. Master Backlight Power Switch Bar
        power_box = QHBoxLayout()
        power_box.setSpacing(12)
        power_title_box = QVBoxLayout()
        power_title_box.setSpacing(2)
        power_title = QLabel("Backlight Power")
        power_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #FFFFFF;")
        self.power_status_desc = QLabel("Keyboard LEDs and illumination active")
        self.power_status_desc.setStyleSheet("font-size: 12px; color: #9CA3AF;")
        power_title_box.addWidget(power_title)
        power_title_box.addWidget(self.power_status_desc)
        power_box.addLayout(power_title_box, 1)

        self.power_toggle_btn = QPushButton("Backlight: ON")
        self.power_toggle_btn.setCheckable(True)
        self.power_toggle_btn.setChecked(True)
        self.power_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.power_toggle_btn.setMinimumHeight(36)
        self.power_toggle_btn.setStyleSheet(
            "QPushButton { background-color: #162620; color: #10B981; border: 1px solid #1E4D38; "
            "font-size: 12px; font-weight: 600; padding: 6px 16px; border-radius: 6px; } "
            "QPushButton:hover { background-color: #1F362D; } "
            "QPushButton:!checked { background-color: #251B1F; color: #F87171; border: 1px solid #4D1E28; } "
            "QPushButton:!checked:hover { background-color: #332027; }"
        )
        self.power_toggle_btn.clicked.connect(self._toggle_backlight_power)
        power_box.addWidget(self.power_toggle_btn)
        card_layout.addLayout(power_box)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #262B3B; max-height: 1px;")
        card_layout.addWidget(divider)

        # Controls Container (can be enabled / disabled when backlight is toggled)
        self.controls_widget = QWidget()
        controls_layout = QVBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(16)

        # 1. Effects Selector
        fx_layout = QHBoxLayout()
        fx_label = QLabel("Lighting Effect (16 Modes):")
        fx_label.setStyleSheet("font-weight: 600;")
        self.fx_combo = QComboBox()
        self.fx_combo.setView(QListView())
        for fx in RGB_EFFECTS:
            self.fx_combo.addItem(f"{fx['id']}: {fx['name']}", fx["id"])
        self.fx_combo.currentIndexChanged.connect(self._on_effect_changed)
        fx_layout.addWidget(fx_label)
        fx_layout.addWidget(self.fx_combo, 1)
        controls_layout.addLayout(fx_layout)

        # Effect Description
        self.fx_desc = QLabel("")
        self.fx_desc.setStyleSheet("color: #9CA3AF; font-style: italic;")
        controls_layout.addWidget(self.fx_desc)

        # 2. Sliders Grid (Brightness & Speed)
        slider_grid = QGridLayout()
        slider_grid.setSpacing(14)

        # Brightness
        slider_grid.addWidget(QLabel("Brightness:"), 0, 0)
        self.bright_slider = QSlider(Qt.Horizontal)
        self.bright_slider.setRange(0, 4)
        self.bright_slider.setValue(3)
        self.bright_label = QLabel("Level 3 / 4")
        self.bright_slider.valueChanged.connect(lambda v: self.bright_label.setText(f"Level {v} / 4"))
        slider_grid.addWidget(self.bright_slider, 0, 1)
        slider_grid.addWidget(self.bright_label, 0, 2)

        # Speed
        slider_grid.addWidget(QLabel("Animation Speed:"), 1, 0)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(0, 4)
        self.speed_slider.setValue(2)
        self.speed_label = QLabel("Level 2 / 4")
        self.speed_slider.valueChanged.connect(lambda v: self.speed_label.setText(f"Level {v} / 4"))
        slider_grid.addWidget(self.speed_slider, 1, 1)
        slider_grid.addWidget(self.speed_label, 1, 2)

        controls_layout.addLayout(slider_grid)

        # 3. Color Swatch & Palette Presets
        color_section = QVBoxLayout()
        color_section.addWidget(QLabel("Primary RGB Color:"))

        palette_layout = QHBoxLayout()
        palette_layout.setSpacing(8)

        # Current active color swatch button
        self.color_swatch = QPushButton()
        self.color_swatch.setFixedSize(36, 36)
        self.color_swatch.setToolTip("Click to choose custom RGB color")
        self.color_swatch.clicked.connect(self._open_color_picker)
        palette_layout.addWidget(self.color_swatch)

        # Quick preset color circles
        for name, hex_col in PRESET_COLORS:
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setToolTip(name)
            btn.setStyleSheet(f"background-color: {hex_col}; border-radius: 14px; border: 1px solid #384058;")
            btn.clicked.connect(lambda _, h=hex_col: self._set_color_hex(h))
            palette_layout.addWidget(btn)

        palette_layout.addStretch()

        self.custom_color_btn = QPushButton("Custom Color...")
        self.custom_color_btn.clicked.connect(self._open_color_picker)
        palette_layout.addWidget(self.custom_color_btn)

        color_section.addLayout(palette_layout)
        controls_layout.addLayout(color_section)

        # 4. Side-Glow Toggle
        side_layout = QHBoxLayout()
        self.side_glow_check = QCheckBox("Enable Chassis Side RGB Glow Strips")
        self.side_glow_check.setChecked(True)
        side_layout.addWidget(self.side_glow_check)
        side_layout.addStretch()
        controls_layout.addLayout(side_layout)

        card_layout.addWidget(self.controls_widget)
        main_layout.addWidget(card)

        # Bottom Actions
        action_layout = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #10B981; font-weight: 500;")
        action_layout.addWidget(self.status_label)

        action_layout.addStretch()

        self.turn_off_btn = QPushButton("Turn Off Backlight")
        self.turn_off_btn.setIcon(get_icon("moon", normal_color="#F87171", size=14))
        self.turn_off_btn.setObjectName("DangerButton")
        self.turn_off_btn.setMinimumHeight(38)
        self.turn_off_btn.clicked.connect(self._turn_off_backlight)
        action_layout.addWidget(self.turn_off_btn)

        self.apply_btn = QPushButton("Apply to Keyboard")
        self.apply_btn.setIcon(get_icon("check", normal_color="#FFFFFF", size=14))
        self.apply_btn.setObjectName("PrimaryButton")
        self.apply_btn.setMinimumHeight(38)
        self.apply_btn.clicked.connect(self._apply_lighting)
        action_layout.addWidget(self.apply_btn)

        main_layout.addLayout(action_layout)
        main_layout.addStretch()

    def _load_from_profile(self):
        cfg = self.profile_manager.get_lighting()
        backlight_on = cfg.get("backlight_enabled", True)
        self.power_toggle_btn.blockSignals(True)
        self.power_toggle_btn.setChecked(backlight_on)
        self.power_toggle_btn.setText("Backlight: ON" if backlight_on else "Backlight: OFF")
        self.power_toggle_btn.blockSignals(False)
        self.power_status_desc.setText(
            "Keyboard LEDs and illumination active" if backlight_on else "Keyboard LEDs and illumination turned off"
        )
        self.controls_widget.setEnabled(backlight_on)

        effect_id = cfg.get("effect_id", 3)
        for i in range(self.fx_combo.count()):
            if self.fx_combo.itemData(i) == effect_id:
                self.fx_combo.setCurrentIndex(i)
                break

        self.bright_slider.setValue(cfg.get("brightness", 3))
        self.speed_slider.setValue(cfg.get("speed", 2))
        self.side_glow_check.setChecked(cfg.get("side_glow_enabled", True))

        rgb = cfg.get("color", [99, 102, 241])
        self.selected_color = QColor(rgb[0], rgb[1], rgb[2])
        self._update_swatch()
        self._on_effect_changed()

    def _toggle_backlight_power(self):
        if self.power_toggle_btn.isChecked():
            self._turn_on_backlight()
        else:
            self._turn_off_backlight()

    def _turn_off_backlight(self):
        self.power_toggle_btn.blockSignals(True)
        self.power_toggle_btn.setChecked(False)
        self.power_toggle_btn.setText("Backlight: OFF")
        self.power_toggle_btn.blockSignals(False)
        self.power_status_desc.setText("Keyboard LEDs and illumination turned off")
        self.controls_widget.setEnabled(False)

        self.profile_manager.update_lighting(backlight_enabled=False)
        ok = self.hid.turn_off_backlight()
        if ok:
            self.status_label.setText("Backlight turned off.")
            self.status_label.setStyleSheet("color: #F87171; font-weight: 500;")
        else:
            self.status_label.setText("Saved to profile. (Turned off)")
            self.status_label.setStyleSheet("color: #F59E0B; font-weight: 500;")

        self.lighting_applied.emit(self.profile_manager.get_lighting())

    def _turn_on_backlight(self):
        self.power_toggle_btn.blockSignals(True)
        self.power_toggle_btn.setChecked(True)
        self.power_toggle_btn.setText("Backlight: ON")
        self.power_toggle_btn.blockSignals(False)
        self.power_status_desc.setText("Keyboard LEDs and illumination active")
        self.controls_widget.setEnabled(True)

        self.profile_manager.update_lighting(backlight_enabled=True)
        self._apply_lighting()

    def _on_effect_changed(self):
        fx_id = self.fx_combo.currentData()
        fx_info = next((f for f in RGB_EFFECTS if f["id"] == fx_id), None)
        if fx_info:
            self.fx_desc.setText(fx_info["description"])

    def _set_color_hex(self, hex_val: str):
        self.selected_color = QColor(hex_val)
        self._update_swatch()

    def _open_color_picker(self):
        color = QColorDialog.getColor(self.selected_color, self, "Select MK75 RGB Color")
        if color.isValid():
            self.selected_color = color
            self._update_swatch()

    def _update_swatch(self):
        hex_c = self.selected_color.name()
        self.color_swatch.setStyleSheet(
            f"background-color: {hex_c}; border-radius: 6px; border: 2px solid #FFFFFF;"
        )

    def _apply_lighting(self):
        effect_id = self.fx_combo.currentData()
        brightness = self.bright_slider.value()
        speed = self.speed_slider.value()
        side_glow = self.side_glow_check.isChecked()
        r = self.selected_color.red()
        g = self.selected_color.green()
        b = self.selected_color.blue()

        self.power_toggle_btn.blockSignals(True)
        self.power_toggle_btn.setChecked(True)
        self.power_toggle_btn.setText("Backlight: ON")
        self.power_toggle_btn.blockSignals(False)
        self.power_status_desc.setText("Keyboard LEDs and illumination active")
        self.controls_widget.setEnabled(True)

        # Update profile
        self.profile_manager.update_lighting(
            backlight_enabled=True,
            effect_id=effect_id,
            effect_name=self.fx_combo.currentText().split(": ")[1],
            brightness=brightness,
            speed=speed,
            color=[r, g, b],
            side_glow_enabled=side_glow
        )

        # Transmit via hardware controller
        ok = self.hid.set_lighting_effect(
            effect_id=effect_id,
            brightness=brightness,
            speed=speed,
            rgb=(r, g, b),
            side_glow=side_glow
        )

        if ok:
            self.status_label.setText("Lighting settings applied to keyboard.")
            self.status_label.setStyleSheet("color: #10B981; font-weight: 500;")
        else:
            self.status_label.setText("Saved to profile. Reconnect keyboard to commit.")
            self.status_label.setStyleSheet("color: #F59E0B; font-weight: 500;")

        self.lighting_applied.emit(self.profile_manager.get_lighting())
