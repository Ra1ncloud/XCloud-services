"""Мини-виджет: компактное плавающее окно со статусом и кнопкой вкл/выкл.
Обновляется раз в 2 секунды и только когда виден; сам в сеть не ходит (берёт данные сторожа)."""
from PyQt6.QtCore import Qt, QRectF, QTimer, QPoint
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QGuiApplication, QFontMetrics
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QMenu

from .i18n import tr
from .settings import settings
from .widgets import Dot, label, button, T


class MiniWidget(QWidget):
    def __init__(self, core, window):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.core, self.win = core, window
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(290, 62)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 8, 10, 8)
        outer.setSpacing(6)
        lay = QHBoxLayout()
        lay.setSpacing(10)
        outer.addLayout(lay)
        self.dot = Dot("#9CA3AF", 10)
        lay.addWidget(self.dot)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.name = label("", None)
        self.name.setStyleSheet("font-weight:600;")
        self.sub = label("", "small")
        col.addWidget(self.name)
        col.addWidget(self.sub)
        lay.addLayout(col, 1)
        self.btn = button("", "power", "icon")
        self.btn.setFixedSize(34, 34)
        self.btn.setToolTip(tr("Включить / выключить обход"))
        self.btn.clicked.connect(self.toggle)
        lay.addWidget(self.btn)
        # строка VPN
        self.vrow = QWidget()
        vl = QHBoxLayout(self.vrow)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(10)
        self.vdot = Dot("#9CA3AF", 10)
        vl.addWidget(self.vdot)
        vcol = QVBoxLayout()
        vcol.setSpacing(0)
        self.vname = label("", None)
        self.vname.setStyleSheet("font-weight:600;")
        self.vsub = label("", "small")
        vcol.addWidget(self.vname)
        vcol.addWidget(self.vsub)
        vl.addLayout(vcol, 1)
        self.vbtn = button("", "shield", "icon")
        self.vbtn.setFixedSize(34, 34)
        self.vbtn.setToolTip(tr("Включить / выключить VPN"))
        self.vbtn.clicked.connect(lambda: core.vpn.toggle())
        vl.addWidget(self.vbtn)
        outer.addWidget(self.vrow)
        core.vpn.state_changed.connect(self.refresh)
        core.vpn.stats.connect(self.refresh)
        self._drag = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        core.state_changed.connect(self.refresh)
        core.watch_changed.connect(self.refresh)
        pos = settings.get("mini_pos")
        scr = QGuiApplication.primaryScreen().availableGeometry()
        if pos and scr.adjusted(-200, -40, 0, 0).contains(QPoint(*pos)):
            self.move(*pos)
        else:
            self.move(scr.right() - self.width() - 20, scr.top() + 60)

    def toggle(self):
        if self.core.active() or self.core.external:
            self.core.stop()
        else:
            p = self.core.by_id(settings.get("last_preset"))
            if p:
                self.core.activate(p)
            else:
                self.win.show_normal()

    def refresh(self):
        if not self.isVisible():
            return
        c = self.core
        a = c.active()
        fm = QFontMetrics(self.name.font())
        if c.starting:
            self.dot.set_color("#F59E0B")
            name, sub = tr("Запускается…"), ""
        elif a:
            up = c.runner.uptime()
            last = c.watchdog.last
            sub = f"{up // 3600:02d}:{up % 3600 // 60:02d}:{up % 60:02d}"
            if last and settings.get("watchdog"):
                sub += f"  ·  {last['ok']}/{last['total']}"
                if last.get("ms"):
                    sub += f"  ·  {last['ms']} {tr('мс')}"
            bad = bool(last and last["ok"] < last["total"])
            self.dot.set_color("#F59E0B" if bad else "#22C55E")
            name = a.name
        elif c.busy:
            self.dot.set_color("#F59E0B")
            name, sub = tr("Автоподбор") + "…", ""
        else:
            self.dot.set_color("#9CA3AF")
            v = c.vpn
            name = tr("zapret выключен") if v.installed() and v.store.server() else tr("Обход выключен")
            sub = tr("включите кнопкой справа")
        self.name.setText(fm.elidedText(name, Qt.TextElideMode.ElideRight, 180))
        self.sub.setText(sub)
        col = "#22C55E" if a else T().muted_hex
        self.btn.setStyleSheet(f"QPushButton{{border-radius:17px; border:1px solid {col};}}")
        if a:
            self.name.setText(fm.elidedText("zapret · " + name, Qt.TextElideMode.ElideRight, 190))
        self._refresh_vpn(bool(a))

    def _refresh_vpn(self, zapret_on):
        v = self.core.vpn
        show = v.installed() and bool(v.store.server())
        if show != self.vrow.isVisible() or self.height() != (112 if show else 62):
            self.vrow.setVisible(show)
            self.setFixedSize(290, 112 if show else 62)
        if not show:
            return
        fm = QFontMetrics(self.vsub.font())
        on = v.state == "on"
        if v.state in ("starting", "stopping"):
            self.vdot.set_color("#F59E0B")
            self.vname.setText(tr("VPN: подключение…") if v.state == "starting" else tr("VPN: отключение…"))
            sub = ""
        elif on:
            self.vdot.set_color("#22C55E")
            down = v.speed[1]
            spd = f"↓ {down / 1048576:.1f} {tr('МБ')}/{tr('с')}" if down >= 104858 else f"↓ {down // 1024} {tr('КБ')}/{tr('с')}"
            if v.route == "all":
                self.vname.setText(tr("VPN: весь трафик") + f"  ·  {spd}")
                sub = (tr("через VPN") + ": " + ", ".join(list(v.now_vpn)[:4])) if v.now_vpn else tr("всё идёт через VPN")
            else:
                self.vname.setText(("zapret + VPN" if zapret_on else "VPN") + f"  ·  {spd}")
                sub = (tr("через VPN") + ": " + ", ".join(list(v.now_vpn)[:4])) if v.now_vpn \
                    else tr("сейчас всё идёт через zapret") if zapret_on else tr("сейчас сайты идут напрямую")
        else:
            self.vdot.set_color("#9CA3AF")
            self.vname.setText(tr("VPN выключен"))
            sub = v.store.server()["name"]
        self.vsub.setText(fm.elidedText(sub, Qt.TextElideMode.ElideRight, 200))
        self.vsub.setToolTip(", ".join(v.now_vpn) if on and v.now_vpn else "")
        vc = "#22C55E" if on else T().muted_hex
        self.vbtn.setStyleSheet(f"QPushButton{{border-radius:17px; border:1px solid {vc};}}")

    def showEvent(self, e):
        super().showEvent(e)
        self._timer.start(2000)
        self.refresh()

    def hideEvent(self, e):
        super().hideEvent(e)
        self._timer.stop()

    def paintEvent(self, e):
        t = T()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 16, 16)
        bg = QColor("#1A1A26" if t.dark else "#FFFFFF")
        bg.setAlphaF(0.93)
        p.fillPath(path, bg)
        p.setPen(QColor(255, 255, 255, 35) if t.dark else QColor(0, 0, 0, 35))
        p.drawPath(path)

    # перетаскивание
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        if self._drag is not None:
            self._drag = None
            settings.set("mini_pos", [self.x(), self.y()])

    def mouseDoubleClickEvent(self, e):
        self.win.show_normal()

    def contextMenuEvent(self, e):
        m = QMenu(self)
        m.addAction(tr("Открыть ZapretCloud"), self.win.show_normal)
        m.addAction(tr("Скрыть виджет"), lambda: self.win.set_mini(False))
        m.exec(e.globalPos())
