"""Цвета и стили (QSS) для тёмной и светлой темы."""
from PyQt6.QtGui import QColor

ACCENTS = ["#7C5CFF", "#3B82F6", "#14B8A6", "#EC4899", "#F97316", "#22C55E"]
OK, BAD, WARN = "#22C55E", "#EF4444", "#F59E0B"


class Theme:
    def __init__(self, mode="dark", accent="#7C5CFF", opacity=0.8):
        self.mode, self.accent, self.opacity = mode, accent, opacity
        dark = mode == "dark"
        self.dark = dark
        self.bg = QColor(18, 18, 26) if dark else QColor(244, 244, 250)
        self.text = "#F4F4F8" if dark else "#1B1B22"
        self.muted = "rgba(255,255,255,0.60)" if dark else "rgba(20,20,35,0.60)"
        self.muted_hex = "#9A9AA8" if dark else "#6A6A78"
        self.surface = "rgba(255,255,255,0.055)" if dark else "rgba(255,255,255,0.62)"
        self.surface2 = "rgba(255,255,255,0.09)" if dark else "rgba(255,255,255,0.85)"
        self.hover = "rgba(255,255,255,0.12)" if dark else "rgba(0,0,0,0.05)"
        self.border = "rgba(255,255,255,0.10)" if dark else "rgba(0,0,0,0.09)"
        self.input = "rgba(0,0,0,0.25)" if dark else "rgba(255,255,255,0.9)"
        self.sidebar = "rgba(0,0,0,0.18)" if dark else "rgba(255,255,255,0.35)"
        a = QColor(accent)
        self.accent_soft = f"rgba({a.red()},{a.green()},{a.blue()},0.18)"
        self.accent_hover = a.lighter(115).name()
        self.accent_glow = f"rgba({a.red()},{a.green()},{a.blue()},0.22)"
        self.accent_line = f"rgba({a.red()},{a.green()},{a.blue()},0.55)"

    def qss(self) -> str:
        t = self
        from .paths import data_dir
        chk = data_dir() / "tmp" / "check.svg"
        try:
            chk.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" '
                           'stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>')
        except OSError:
            pass
        chk_url = chk.as_posix()
        return f"""
* {{ font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", "Noto Sans", sans-serif; font-size: 14px; color: {t.text}; }}
QWidget#Root {{ background: transparent; }}
QLabel {{ background: transparent; }}
QLabel[role="muted"] {{ color: {t.muted}; }}
QLabel[role="h1"] {{ font-size: 24px; font-weight: 600; }}
QLabel[role="h2"] {{ font-size: 16px; font-weight: 600; }}
QLabel[role="small"] {{ font-size: 12px; color: {t.muted}; }}
QLabel[role="badge"] {{ background: {t.accent_soft}; color: {t.accent_hover if t.dark else t.accent}; border-radius: 6px; padding: 2px 8px; font-size: 12px; font-weight: 600; }}
QFrame#Sidebar {{ background: {t.sidebar}; border-right: 1px solid {t.border}; }}
QFrame[card="true"] {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 12px; }}
QPushButton {{ background: {t.surface2}; border: 1px solid {t.border}; border-radius: 8px; padding: 8px 14px; min-height: 20px; }}
QPushButton:hover {{ background: {t.hover}; }}
QPushButton:pressed {{ background: {t.surface}; }}
QPushButton:disabled {{ color: {t.muted}; background: {t.surface}; }}
QPushButton[kind="primary"] {{ background: {t.accent}; color: white; border: none; font-weight: 600; }}
QPushButton[kind="primary"]:hover {{ background: {t.accent_hover}; }}
QPushButton[kind="primary"]:disabled {{ background: {t.accent_soft}; color: {t.muted}; }}
QPushButton[kind="danger"] {{ background: rgba(239,68,68,0.16); color: {"#FCA5A5" if t.dark else "#B91C1C"}; border: 1px solid rgba(239,68,68,0.35); font-weight: 600; }}
QPushButton[kind="danger"]:hover {{ background: rgba(239,68,68,0.28); }}
QPushButton[kind="danger"]:disabled {{ background: {t.surface}; color: {t.muted}; border: 1px solid {t.border}; }}
QPushButton[kind="nav"] {{ background: transparent; border: none; text-align: left; padding: 10px 14px; border-radius: 8px; color: {t.muted}; font-weight: 500; }}
QPushButton[kind="nav"]:hover {{ background: {t.hover}; color: {t.text}; }}
QPushButton[kind="nav"]:checked {{ background: {t.accent_soft}; color: {t.text}; font-weight: 600; }}
QPushButton[kind="navvpn"] {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t.accent_glow}, stop:1 transparent); border: 1px solid {t.accent_line}; text-align: left; padding: 10px 14px; border-radius: 10px; color: {t.text}; font-weight: 600; }}
QPushButton[kind="navvpn"]:hover {{ background: {t.accent_soft}; border-color: {t.accent}; }}
QPushButton[kind="navvpn"]:checked {{ background: {t.accent}; border-color: {t.accent}; color: #FFFFFF; }}
QPushButton[kind="bigpower"] {{ border-radius: 34px; min-width: 68px; max-width: 68px; min-height: 68px; max-height: 68px; padding: 0; background: {t.surface2}; border: 2px solid {t.border}; }}
QPushButton[kind="bigpower"]:hover {{ border-color: {t.accent}; }}
QPushButton[kind="bigpower"][on="true"] {{ background: rgba(34,197,94,0.18); border: 2px solid #22C55E; }}
QPushButton[kind="title"] {{ background: transparent; border: none; border-radius: 6px; padding: 6px; min-width: 32px; }}
QPushButton[kind="title"]:hover {{ background: {t.hover}; }}
QPushButton[kind="close"] {{ background: transparent; border: none; border-radius: 6px; padding: 6px; min-width: 32px; }}
QPushButton[kind="close"]:hover {{ background: #E81123; }}
QPushButton[kind="icon"] {{ background: transparent; border: none; border-radius: 8px; padding: 4px; }}
QPushButton[kind="icon"]:hover {{ background: {t.hover}; }}
QPushButton[kind="swatch"] {{ border-radius: 14px; min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px; padding: 0; }}
QPushButton[kind="tile"] {{ text-align: left; padding: 14px; background: {t.surface}; border-radius: 12px; }}
QPushButton[kind="tile"]:hover {{ background: {t.hover}; border-color: {t.accent}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {{ background: {t.input}; border: 1px solid {t.border}; border-radius: 8px; padding: 7px 10px; selection-background-color: {t.accent}; }}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {t.accent}; }}
QPlainTextEdit {{ font-family: "Cascadia Mono", "Consolas", "DejaVu Sans Mono", monospace; font-size: 13px; padding: 8px; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{ background: {"#202030" if t.dark else "#FFFFFF"}; border: 1px solid {t.border}; selection-background-color: {t.accent_soft}; outline: 0; padding: 4px; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid {t.muted_hex}; background: {t.input}; }}
QCheckBox::indicator:checked {{ background: {t.accent}; border-color: {t.accent}; image: url("{chk_url}"); }}
QRadioButton {{ spacing: 8px; background: transparent; }}
QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 8px; border: 1px solid {t.muted_hex}; background: {t.input}; }}
QRadioButton::indicator:checked {{ width: 8px; height: 8px; border: 4px solid {t.accent}; background: #FFFFFF; }}
QListView, QTableWidget, QTreeWidget, QListWidget {{ background: transparent; border: none; outline: 0; }}
QListWidget::item {{ padding: 8px 10px; border-radius: 8px; margin: 1px 0; }}
QListWidget#boxlist {{ background: {t.input}; border: 1px solid {t.border}; border-radius: 10px; padding: 4px; }}
QListWidget::item:hover {{ background: {t.hover}; }}
QListWidget::item:selected {{ background: {t.accent_soft}; color: {t.text}; border: 1px solid {t.accent}; }}
QTreeWidget::item {{ padding: 3px 0; }}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0; border: none; }}
QTableWidget {{ gridline-color: transparent; alternate-background-color: {t.surface}; }}
QTableWidget::item {{ padding: 6px; border: none; }}
QTableWidget::item:selected, QTreeWidget::item:selected {{ background: {t.accent_soft}; color: {t.text}; }}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{ background: transparent; border: none; border-bottom: 1px solid {t.border}; padding: 8px 6px; color: {t.muted}; font-weight: 600; }}
QTableCornerButton::section {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {t.hover}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {t.muted_hex}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {t.hover}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QProgressBar {{ background: {t.input}; border: none; border-radius: 4px; height: 8px; text-align: center; font-size: 1px; color: transparent; }}
QProgressBar::chunk {{ background: {t.accent}; border-radius: 4px; }}
QSlider::groove:horizontal {{ height: 6px; background: {t.input}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {t.accent}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: white; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; border: 1px solid {t.border}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QToolTip {{ background: {"#25253A" if t.dark else "#FFFFFF"}; color: {t.text}; border: 1px solid {t.border}; padding: 6px; border-radius: 6px; }}
QMenu {{ background: {"#1E1E2C" if t.dark else "#FFFFFF"}; border: 1px solid {t.border}; padding: 6px; border-radius: 8px; }}
QMenu::item {{ padding: 7px 24px 7px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {t.accent_soft}; }}
QMenu::separator {{ height: 1px; background: {t.border}; margin: 4px 8px; }}
QSplitter::handle {{ background: transparent; }}
QDialog {{ background: {"#1A1A26" if t.dark else "#F6F6FA"}; }}
QMessageBox {{ background: {"#1A1A26" if t.dark else "#F6F6FA"}; }}
"""
