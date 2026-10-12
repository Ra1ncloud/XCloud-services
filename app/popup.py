"""Небольшое всплывающее окно в углу экрана (сторож, обновления)."""
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QGuiApplication
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from .icons import app_icon
from .widgets import label, button, T

_open = []


class Popup(QWidget):
    def __init__(self, title: str, text: str, actions, timeout_ms: int = 0, icon_running=None):
        """actions: [(текст, функция|None, kind)] — после нажатия окно закрывается."""
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(380)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)
        h = QHBoxLayout()
        h.setSpacing(10)
        ic = label()
        ic.setPixmap(app_icon(T().accent, icon_running).pixmap(26, 26))
        h.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
        t = label(title, "h2", wrap=True)
        h.addWidget(t, 1)
        close = button("", "x", "icon")
        close.setFixedSize(26, 26)
        close.clicked.connect(self.close)
        h.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(h)
        body = label(text, wrap=True)
        body.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(body)
        bb = QHBoxLayout()
        bb.addStretch(1)
        for text_, fn, kind in actions:
            b = button(text_, None, kind)
            b.clicked.connect(lambda _=False, fn=fn: self._do(fn))
            bb.addWidget(b)
        lay.addSpacing(4)
        lay.addLayout(bb)
        if timeout_ms:
            QTimer.singleShot(timeout_ms, self.close)

    def _do(self, fn):
        self.close()
        if fn:
            fn()

    def paintEvent(self, e):
        t = T()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 14, 14)
        bg = QColor("#1C1C28" if t.dark else "#FFFFFF")
        bg.setAlphaF(0.97)
        p.fillPath(path, bg)
        p.setPen(QColor(t.accent))
        p.drawPath(path)

    def popup(self):
        for w in list(_open):
            try:
                w.close()
            except RuntimeError:
                pass
        _open.clear()
        _open.append(self)
        self.adjustSize()
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.move(scr.right() - self.width() - 16, scr.bottom() - self.height() - 16)
        self.show()
        self.raise_()

    def closeEvent(self, e):
        if self in _open:
            _open.remove(self)
        super().closeEvent(e)
