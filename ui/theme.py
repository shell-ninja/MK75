"""
Modern Minimalist Dark Theme for Lingbao MK75 Controller.
Clean, restrained, professional desktop aesthetic inspired by Linear, Wootility, and GNOME Libadwaita.
"""

# Theme Palette Constants
BG_MAIN        = "#0B0D13"  # Deep matte obsidian
BG_SURFACE     = "#131620"  # Card / container surface
BG_CARD        = BG_SURFACE # Alias for backward compatibility
BG_INPUT       = "#191D2A"  # Input field background
BG_KEYCAP      = "#181C26"  # Keycap top surface
BG_KEYCAP_HOV  = "#222736"  # Hovered keycap
BG_KEYCAP_ACT  = "#2C3347"  # Active / pressed keycap

BORDER_COLOR   = "#1E2330"  # Crisp 1px structural border
BORDER_SUBTLE  = "#171A24"
BORDER_FOCUS   = "#6366F1"  # Clean accent border

ACCENT_PRIMARY = "#6366F1"  # Indigo primary accent
ACCENT_HOVER   = "#7578F8"
ACCENT_SKY     = "#38BDF8"  # Subtle cyan
ACCENT_EMERALD = "#10B981"  # Status active
ACCENT_AMBER   = "#F59E0B"  # Warning
ACCENT_ROSE    = "#EF4444"  # Destructive action

TEXT_PRIMARY   = "#F1F3F7"  # Clean primary white
TEXT_SECONDARY = "#9CA3AF"  # Subtitles / labels
TEXT_MUTED     = "#6B7280"  # Placeholders / minor info
TEXT_DIM       = "#4B5563"

GLOBAL_STYLESHEET = f"""
QMainWindow, QDialog {{
    background-color: {BG_MAIN};
    color: {TEXT_PRIMARY};
}}

QWidget {{
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", "Cantarell", sans-serif;
    font-size: 13px;
    color: {TEXT_PRIMARY};
}}

/* Structural Containers */
QFrame#Card {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
}}

QFrame#HeaderBar {{
    background-color: {BG_SURFACE};
    border-bottom: 1px solid {BORDER_COLOR};
    padding: 6px 16px;
}}

QFrame#Sidebar {{
    background-color: {BG_SURFACE};
    border-right: 1px solid {BORDER_COLOR};
}}

/* Navigation List */
QListWidget#SidebarList {{
    background-color: transparent;
    border: none;
    outline: none;
    padding: 6px;
}}

QListWidget#SidebarList::item {{
    padding: 8px 12px;
    margin: 2px 0;
    border-radius: 6px;
    color: {TEXT_SECONDARY};
    font-weight: 500;
}}

QListWidget#SidebarList::item:hover {{
    background-color: #1A1F2C;
    color: {TEXT_PRIMARY};
}}

QListWidget#SidebarList::item:selected {{
    background-color: #212738;
    color: #FFFFFF;
    font-weight: 600;
}}

/* Clean Buttons */
QPushButton {{
    background-color: #1E2332;
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: #252B3D;
    border-color: #2E364C;
}}

QPushButton:pressed {{
    background-color: #181C28;
}}

QPushButton#PrimaryButton {{
    background-color: {ACCENT_PRIMARY};
    color: #FFFFFF;
    border: 1px solid {ACCENT_PRIMARY};
}}

QPushButton#PrimaryButton:hover {{
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}

QPushButton#DangerButton {{
    background-color: #2B161B;
    color: #F87171;
    border: 1px solid #45212A;
}}

QPushButton#DangerButton:hover {{
    background-color: #381C23;
}}

/* Form Inputs */
QLineEdit, QSpinBox, QPlainTextEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 10px;
}}

QLineEdit:focus, QSpinBox:focus, QPlainTextEdit:focus {{
    border: 1px solid {BORDER_FOCUS};
}}

QComboBox {{
    background-color: #171A24;
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 12px;
    combobox-popup: 0;
}}

QComboBox:hover {{
    border-color: #384058;
}}

QComboBox:focus {{
    border: 1px solid {BORDER_FOCUS};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
}}

/* Force popup listview to dark background across all desktop engines */
QComboBox QAbstractItemView,
QComboBox QListView,
QListView {{
    background-color: #131620 !important;
    background: #131620 !important;
    color: #F1F3F7 !important;
    selection-background-color: {ACCENT_PRIMARY} !important;
    selection-color: #FFFFFF !important;
    border: 1px solid #2B3245;
    border-radius: 6px;
    padding: 4px;
    outline: none;
}}

QComboBox QAbstractItemView::item,
QComboBox QListView::item,
QListView::item {{
    min-height: 28px;
    padding: 4px 10px;
    color: #E2E8F0 !important;
    border-radius: 4px;
    background-color: #131620;
}}

QComboBox QAbstractItemView::item:selected,
QComboBox QListView::item:selected,
QListView::item:selected {{
    background-color: {ACCENT_PRIMARY} !important;
    color: #FFFFFF !important;
}}

QComboBox QAbstractItemView::item:hover,
QComboBox QListView::item:hover,
QListView::item:hover {{
    background-color: #212738 !important;
    color: #FFFFFF !important;
}}

QMenu {{
    background-color: #131620;
    color: #F1F3F7;
    border: 1px solid #2B3245;
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 14px;
    border-radius: 4px;
    color: #E2E8F0;
}}

QMenu::item:selected {{
    background-color: {ACCENT_PRIMARY};
    color: #FFFFFF;
}}

/* Sliders */
QSlider::groove:horizontal {{
    height: 4px;
    background: #202636;
    border-radius: 2px;
}}

QSlider::sub-page:horizontal {{
    background: {ACCENT_PRIMARY};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: #FFFFFF;
    border: 1px solid #C7D2FE;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
}}

QScrollBar::handle:vertical {{
    background: #242B3B;
    border-radius: 3px;
}}

/* Clean Labels */
QLabel#TitleLabel {{
    font-size: 16px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

QLabel#SubtitleLabel {{
    font-size: 12px;
    color: {TEXT_SECONDARY};
}}

QLabel#Badge {{
    background-color: #1A1F2C;
    border: 1px solid {BORDER_COLOR};
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    color: {TEXT_SECONDARY};
}}

/* Tab Widget & Tabs */
QTabWidget::pane {{
    background-color: transparent;
    border: none;
}}

QTabBar::tab {{
    background-color: #141722;
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER_COLOR};
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 6px 14px;
    margin-right: 4px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: #1F2535;
    color: #FFFFFF;
    border-color: #2D354A;
    font-weight: 600;
}}

QTabBar::tab:hover:!selected {{
    background-color: #1A1E2B;
    color: {TEXT_PRIMARY};
}}

/* Tables & Grid */
QTableWidget {{
    background-color: #0E1017;
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    gridline-color: #1A1F2C;
    outline: none;
}}

QTableWidget::item {{
    padding: 6px 8px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: #1F2638;
    color: #FFFFFF;
}}

QHeaderView::section {{
    background-color: #141722;
    color: {TEXT_SECONDARY};
    border: none;
    border-right: 1px solid {BORDER_COLOR};
    border-bottom: 1px solid {BORDER_COLOR};
    padding: 6px 8px;
    font-weight: 600;
}}
"""
