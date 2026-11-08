"""
Interactive 75% Keyboard Visualizer for Lingbao MK75.
Renders 81 keys, multifunction rotary knob, and side-glow RGB strips with precision.
"""

from typing import Optional, Dict, Any, List
import math
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QLinearGradient, QRadialGradient,
    QFont, QPainterPath
)
from PySide6.QtWidgets import QWidget, QSizePolicy

from config.keycodes import LAYOUT_75_PERCENT, KeyDef
from ui.theme import (
    BG_CARD, BG_KEYCAP, BG_KEYCAP_HOV, BG_KEYCAP_ACT,
    BORDER_COLOR, BORDER_FOCUS, ACCENT_PRIMARY, ACCENT_SKY,
    TEXT_PRIMARY, TEXT_MUTED, TEXT_DIM
)

class KeyboardVisualizer(QWidget):
    """Accurate 75% interactive visualizer widget with rotary knob & side glow."""

    key_selected = Signal(object)  # Emits KeyDef

    def __init__(self, profile_manager, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.keys: List[KeyDef] = LAYOUT_75_PERCENT
        self.selected_key_id: Optional[str] = "KNOB_CLICK"
        self.hovered_key_id: Optional[str] = None
        self.pressed_key_ids: set = set()

        # Geometry calculations
        self.max_x = max(k.x + k.w for k in self.keys) + 0.2
        self.max_y = max(k.y + k.h for k in self.keys) + 0.2
        self.unit_size = 46.0  # Base size in px per unit
        self.margin_x = 36.0
        self.margin_y = 28.0

        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumSize(780, 310)

        # Connect to profile changes to redraw badges
        self.profile_manager.add_listener(lambda p: self.update())

    def set_key_pressed(self, key_id: str, is_pressed: bool):
        if is_pressed:
            self.pressed_key_ids.add(key_id)
        else:
            self.pressed_key_ids.discard(key_id)
        self.update()

    def select_key(self, key_id: str):
        self.selected_key_id = key_id
        target = next((k for k in self.keys if k.id == key_id), None)
        if target:
            self.key_selected.emit(target)
        self.update()

    def _calc_layout(self):
        w = self.width() - (self.margin_x * 2)
        h = self.height() - (self.margin_y * 2)
        unit_w = w / self.max_x
        unit_h = h / self.max_y
        self.unit_size = min(unit_w, unit_h, 54.0)

        # Center inside widget
        total_w = self.max_x * self.unit_size
        total_h = self.max_y * self.unit_size
        self.offset_x = (self.width() - total_w) / 2.0
        self.offset_y = (self.height() - total_h) / 2.0

    def paintEvent(self, event):
        self._calc_layout()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # 1. Draw Keyboard Chassis
        self._draw_chassis(painter)

        # 2. Draw Side RGB Glow Strips
        self._draw_side_strips(painter)

        # 3. Draw All 81 Keys & Rotary Knob
        for k in self.keys:
            if k.is_knob:
                self._draw_knob(painter, k)
            else:
                self._draw_key(painter, k)

    def _draw_chassis(self, painter: QPainter):
        total_w = self.max_x * self.unit_size
        total_h = self.max_y * self.unit_size
        pad = 14.0

        deck_rect = QRectF(
            self.offset_x - pad,
            self.offset_y - pad,
            total_w + (pad * 2),
            total_h + (pad * 2)
        )

        # Outer chassis base
        painter.setPen(QPen(QColor(BORDER_COLOR), 1.5))
        painter.setBrush(QBrush(QColor("#12151D")))
        painter.drawRoundedRect(deck_rect, 16.0, 16.0)

        # Inner plate bevel
        plate_rect = QRectF(
            deck_rect.x() + 4,
            deck_rect.y() + 4,
            deck_rect.width() - 8,
            deck_rect.height() - 8
        )
        painter.setPen(QPen(QColor("#1E232F"), 1.0))
        painter.setBrush(QBrush(QColor("#151822")))
        painter.drawRoundedRect(plate_rect, 13.0, 13.0)

    def _draw_side_strips(self, painter: QPainter):
        lighting = self.profile_manager.get_lighting()
        enabled = (
            lighting.get("side_glow_enabled", True) and
            lighting.get("backlight_enabled", True) and
            lighting.get("brightness", 3) > 0 and
            lighting.get("effect_id", 3) != 32
        )
        rgb = lighting.get("color", [99, 102, 241])

        if not enabled:
            strip_color = QColor("#222836")
        else:
            strip_color = QColor(rgb[0], rgb[1], rgb[2])

        total_w = self.max_x * self.unit_size
        total_h = self.max_y * self.unit_size
        strip_w = 4.0
        strip_h = total_h * 0.75
        strip_y = self.offset_y + (total_h - strip_h) / 2.0

        # Left Strip
        left_rect = QRectF(self.offset_x - 12.0, strip_y, strip_w, strip_h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(strip_color))
        painter.drawRoundedRect(left_rect, 2.0, 2.0)

        # Right Strip
        right_rect = QRectF(self.offset_x + total_w + 8.0, strip_y, strip_w, strip_h)
        painter.drawRoundedRect(right_rect, 2.0, 2.0)

    def _draw_key(self, painter: QPainter, k: KeyDef):
        rect = self._get_key_rect(k)
        is_selected = (k.id == self.selected_key_id)
        is_hovered = (k.id == self.hovered_key_id)
        is_pressed = (k.id in self.pressed_key_ids or k.keycode_name in self.pressed_key_ids)
        is_remapped = (self.profile_manager.get_remapping(k.id) is not None)

        # Colors & Gradients
        if is_selected:
            bg_top = QColor("#313652")
            bg_bot = QColor("#262A42")
            border_col = QColor(ACCENT_PRIMARY)
            border_w = 2.0
        elif is_pressed:
            bg_top = QColor(BG_KEYCAP_ACT)
            bg_bot = QColor(BG_KEYCAP_ACT)
            border_col = QColor(ACCENT_SKY)
            border_w = 1.5
        elif is_hovered:
            bg_top = QColor(BG_KEYCAP_HOV)
            bg_bot = QColor("#222736")
            border_col = QColor("#434C63")
            border_w = 1.0
        else:
            bg_top = QColor(BG_KEYCAP)
            bg_bot = QColor("#191C26")
            border_col = QColor(BORDER_COLOR)
            border_w = 1.0

        # Keycap base
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0.0, bg_top)
        grad.setColorAt(1.0, bg_bot)

        painter.setPen(QPen(border_col, border_w))
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(rect, 6.0, 6.0)

        # Remapped badge dot
        if is_remapped:
            remap = self.profile_manager.get_remapping(k.id)
            is_macro = remap and remap.get("type") in ("macro", "shortcut", "command", "text")
            dot_color = QColor(ACCENT_SKY if is_macro else ACCENT_PRIMARY)
            dot_r = 3.0
            dot_rect = QRectF(rect.right() - 8.5, rect.top() + 4.0, dot_r * 2, dot_r * 2)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(dot_color))
            painter.drawEllipse(dot_rect)

        # Labels
        painter.setPen(QColor(TEXT_PRIMARY if not is_hovered and not is_selected else "#FFFFFF"))
        font = painter.font()
        font.setPointSize(9 if k.w <= 1.0 else 8)
        font.setWeight(QFont.DemiBold if (is_selected or k.is_special) else QFont.Normal)
        painter.setFont(font)

        if k.sub_label:
            # Sub-label at top left
            painter.setPen(QColor(TEXT_MUTED))
            sub_rect = QRectF(rect.x() + 5, rect.y() + 3, rect.width() - 10, rect.height() / 2)
            painter.drawText(sub_rect, Qt.AlignLeft | Qt.AlignTop, k.sub_label)

            # Primary label bottom left
            painter.setPen(QColor(TEXT_PRIMARY))
            main_rect = QRectF(rect.x() + 5, rect.y() + rect.height() / 2 - 2, rect.width() - 10, rect.height() / 2)
            painter.drawText(main_rect, Qt.AlignLeft | Qt.AlignVCenter, k.label)
        else:
            # Centered or slightly padded single label
            align = Qt.AlignCenter if k.w <= 2.0 else (Qt.AlignLeft | Qt.AlignVCenter)
            pad_left = 8 if k.w > 2.0 else 0
            label_rect = QRectF(rect.x() + pad_left, rect.y(), rect.width() - pad_left, rect.height())
            painter.drawText(label_rect, align, k.label)

    def _draw_knob(self, painter: QPainter, k: KeyDef):
        """Draws the top-right rotary knob with metallic styling and indicator notch."""
        rect = self._get_key_rect(k)
        is_selected = (k.id == self.selected_key_id or self.selected_key_id in ("KNOB_CW", "KNOB_CCW"))
        is_hovered = (k.id == self.hovered_key_id)
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2.0 - 1.0

        # Outer rim / knurled border
        outer_pen = QPen(QColor(ACCENT_PRIMARY if is_selected else (BORDER_FOCUS if is_hovered else BORDER_COLOR)), 2.0 if is_selected else 1.5)
        painter.setPen(outer_pen)

        # Metallic radial gradient
        rad_grad = QRadialGradient(center, radius)
        rad_grad.setColorAt(0.0, QColor("#3D4559" if is_selected else "#2E3445"))
        rad_grad.setColorAt(0.7, QColor("#222736"))
        rad_grad.setColorAt(1.0, QColor("#171A24"))

        painter.setBrush(QBrush(rad_grad))
        painter.drawEllipse(center, radius, radius)

        # Inner Push Button Disc
        inner_r = radius * 0.65
        inner_grad = QLinearGradient(center.x(), center.y() - inner_r, center.x(), center.y() + inner_r)
        inner_grad.setColorAt(0.0, QColor("#32384B"))
        inner_grad.setColorAt(1.0, QColor("#1D212E"))
        painter.setPen(QPen(QColor("#454E66"), 1.0))
        painter.setBrush(QBrush(inner_grad))
        painter.drawEllipse(center, inner_r, inner_r)

        # Rotary Indicator Notch / Line (Pointing North)
        notch_pen = QPen(QColor(ACCENT_SKY if is_selected else "#A0AEC0"), 2.0)
        painter.setPen(notch_pen)
        painter.drawLine(
            QPointF(center.x(), center.y() - radius + 3),
            QPointF(center.x(), center.y() - inner_r - 1)
        )

        # Center Label
        painter.setPen(QColor("#FFFFFF" if is_selected else TEXT_MUTED))
        font = painter.font()
        font.setPointSize(7)
        font.setWeight(QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(center.x() - inner_r, center.y() - inner_r, inner_r * 2, inner_r * 2),
                         Qt.AlignCenter, "KNOB")

    def _get_key_rect(self, k: KeyDef) -> QRectF:
        gap = 3.0
        x = self.offset_x + (k.x * self.unit_size)
        y = self.offset_y + (k.y * self.unit_size)
        w = (k.w * self.unit_size) - gap
        h = (k.h * self.unit_size) - gap
        return QRectF(x, y, w, h)

    def mouseMoveEvent(self, event):
        pos = event.position()
        old_hovered = self.hovered_key_id
        self.hovered_key_id = None

        for k in self.keys:
            rect = self._get_key_rect(k)
            if rect.contains(pos):
                self.hovered_key_id = k.id
                break

        if self.hovered_key_id != old_hovered:
            self.setCursor(Qt.PointingHandCursor if self.hovered_key_id else Qt.ArrowCursor)
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position()
            for k in self.keys:
                rect = self._get_key_rect(k)
                if rect.contains(pos):
                    self.selected_key_id = k.id
                    self.key_selected.emit(k)
                    self.update()
                    break
