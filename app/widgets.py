"""Мелкие переиспользуемые виджеты."""
from PyQt6.QtCore import QObject, Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QSize, QPointF
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QWidget,
                             QGraphicsOpacityEffect, QSizePolicy)

from .icons import icon

THEME = {"t": None}   # текущая тема (заполняется окном)


def T():
    return THEME["t"]


def label(text="", role=None, wrap=False):
    lb = QLabel(text)
    if role:
        lb.setProperty("role", role)
    lb.setWordWrap(wrap)
    return lb


def button(text="", ico=None, kind=None, tip=None, color=None):
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    if ico:
        b.setProperty("ico", ico)
        c = color or ("#FFFFFF" if kind == "primary" else (T().text if T() else "#FFFFFF"))
        if kind == "danger":
            c = "#F87171"
        b.setIcon(icon(ico, c, 16))
        b.setIconSize(QSize(16, 16))
    if tip:
        b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def refresh_icons(root: QWidget):
    """Перекрасить иконки кнопок после смены темы."""
    for b in root.findChildren(QPushButton):
        ico = b.property("ico")
        if not ico:
            continue
        kind = b.property("kind")
        if kind == "primary":
            c = "#FFFFFF"
        elif kind == "danger":
            c = "#F87171"
        elif kind == "nav":
            c = T().text if b.isChecked() else T().muted_hex
        elif kind == "navvpn":
            c = "#22C55E" if b.property("vpn_on") and not b.isChecked() else ("#FFFFFF" if b.isChecked() else T().accent)
        elif kind == "bigpower":
            c = "#22C55E" if b.property("on") == "true" else T().muted_hex
        else:
            c = T().text
        b.setIcon(icon(ico, c, b.iconSize().width() or 16))


class Card(QFrame):
    def __init__(self, parent=None, pad=16, spacing=10, horizontal=False):
        super().__init__(parent)
        self.setProperty("card", True)
        self.lay = (QHBoxLayout if horizontal else QVBoxLayout)(self)
        self.lay.setContentsMargins(pad, pad, pad, pad)
        self.lay.setSpacing(spacing)


class Dot(QWidget):
    def __init__(self, color="#9CA3AF", size=10, pulse=False):
        super().__init__()
        self.color = QColor(color)
        self.s = size
        self.setFixedSize(size + 8, size + 8)
        self._phase = 0
        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self.set_pulse(pulse)

    def set_color(self, c):
        self.color = QColor(c)
        self.update()

    def set_pulse(self, on):
        self._pulse = on
        (self._t.start(60) if on and self.isVisible() else self._t.stop())
        self._phase = 0
        self.update()

    # анимация работает только пока точка видна (экономия ресурсов в трее)
    def showEvent(self, e):
        super().showEvent(e)
        if getattr(self, "_pulse", False):
            self._t.start(60)

    def hideEvent(self, e):
        super().hideEvent(e)
        self._t.stop()

    def _tick(self):
        self._phase = (self._phase + 1) % 30
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        c = QPointF(self.rect().center())
        if self._t.isActive():
            k = self._phase / 30
            g = QColor(self.color)
            g.setAlphaF(0.45 * (1 - k))
            p.setBrush(g)
            r = self.s / 2 + 4 * k
            p.drawEllipse(c, r, r)
        p.setBrush(self.color)
        p.drawEllipse(c, self.s / 2, self.s / 2)


class Toast(QFrame):
    """Всплывающее уведомление внизу окна."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("Toast")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        self.dot = Dot(size=8)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setMaximumWidth(520)
        lay.addWidget(self.dot)
        lay.addWidget(self.text, 1)
        self.eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.eff)
        self.anim = QPropertyAnimation(self.eff, b"opacity", self)
        self.anim.setDuration(220)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)
        self.hide()

    def show_msg(self, msg, kind="info"):
        t = T()
        col = {"ok": "#22C55E", "error": "#EF4444"}.get(kind, t.accent)
        self.dot.set_color(col)
        self.setStyleSheet(f"#Toast{{background:{'#262636' if t.dark else '#FFFFFF'};border:1px solid {t.border};"
                           f"border-radius:10px;}}")
        self.text.setText(msg)
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()
        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()
        self.timer.start(4500 if kind == "error" else 2800)

    def reposition(self):
        p = self.parentWidget()
        self.adjustSize()
        self.move((p.width() - self.width()) // 2 + 100, p.height() - self.height() - 24)

    def fade_out(self):
        self.anim.stop()
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self._hide_once)
        self.anim.start()

    def _hide_once(self):
        try:
            self.anim.finished.disconnect(self._hide_once)
        except TypeError:
            pass
        if self.eff.opacity() < 0.05:
            self.hide()


def hline():
    f = QFrame()
    f.setFixedHeight(1)
    f.setStyleSheet(f"background:{T().border};" if T() else "")
    f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return f


def page_header(title, subtitle=None):
    w = QWidget()
    l = QVBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(2)
    l.addWidget(label(title, "h1"))
    if subtitle:
        l.addWidget(label(subtitle, "muted", wrap=True))
    return w


class WheelGuard(QObject):
    """Колесо мыши над закрытым выпадающим списком / счётчиком / ползунком листает страницу,
    а не меняет значение. Значение меняется только если открыть список вручную."""

    def eventFilter(self, obj, ev):
        from PyQt6.QtCore import QEvent
        from PyQt6.QtWidgets import QComboBox, QAbstractSpinBox, QSlider, QAbstractScrollArea, QApplication
        if ev.type() != QEvent.Type.Wheel:
            return False
        w = obj
        while w is not None and not isinstance(w, (QComboBox, QAbstractSpinBox, QSlider)):
            if isinstance(w, QAbstractScrollArea):
                return False          # колесо внутри списка/открытого попапа — как обычно
            w = w.parentWidget() if isinstance(w, QWidget) else None
        if w is None:
            return False
        a = w.parentWidget()
        while a is not None and not isinstance(a, QAbstractScrollArea):
            a = a.parentWidget()
        if a is not None:
            QApplication.sendEvent(a.verticalScrollBar(), ev)
        return True
