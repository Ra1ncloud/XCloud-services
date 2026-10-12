from pathlib import Path
import sys
import ctypes
import ctypes.wintypes

from PyQt6.QtCore import Qt, QPoint, QRectF, QSize, QTimer, QProcess, QEvent
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QAction, QLinearGradient
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame, QStackedWidget, QButtonGroup,
                             QSystemTrayIcon, QMenu, QApplication, QSizeGrip, QLabel)

from .core import Core
from .i18n import tr
from .icons import icon, app_icon, pixmap
from .paths import APP_NAME
from .settings import settings
from .theme import Theme
from .widgets import THEME, Toast, label, button, refresh_icons, T
from . import winutil
from .pages.home import HomePage
from .pages.autotune import AutotunePage
from .pages.diagnostics import DiagnosticsPage
from .pages.editor import EditorPage
from .pages.dns_page import DnsPage
from .pages.files import FilesPage
from .pages.settings_page import SettingsPage
from .pages.sitecheck_page import SiteCheckPage
from .pages.vpn_page import VpnPage

NAV = [("home", "Главная", "home"), ("autotune", "Автоподбор", "zap"), ("diag", "Диагностика", "activity"),
       ("sitecheck", "Проверка сайта", "search"),
       ("editor", "Редактор", "edit"), ("dns", "DNS", "globe"), ("files", "Файлы", "folder"),
       ("settings", "Настройки", "sliders")]
RADIUS = 12


class TitleBar(QFrame):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setFixedHeight(44)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 8, 0)
        lay.setSpacing(4)
        self.logo = QLabel()
        self.logo.setPixmap(app_icon(settings.get("accent")).pixmap(20, 20))
        lay.addWidget(self.logo)
        lay.addSpacing(6)
        self.title = label(APP_NAME)
        self.title.setStyleSheet("font-weight:600;")
        lay.addWidget(self.title)
        lay.addStretch(1)
        self.b_min = button("", "minus", "title")
        self.b_max = button("", "square", "title")
        self.b_close = button("", "x", "close")
        for b in (self.b_min, self.b_max, self.b_close):
            b.setIconSize(QSize(14, 14))
            lay.addWidget(b)
        self.b_min.clicked.connect(win.showMinimized)
        self.b_max.clicked.connect(win.toggle_max)
        self.b_close.clicked.connect(win.close)
        self._drag = None

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            wh = self.win.windowHandle()
            if wh and wh.startSystemMove():
                return
            self._drag = e.globalPosition().toPoint() - self.win.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and not self.win.isMaximized():
            self.win.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def mouseDoubleClickEvent(self, e):
        self.win.toggle_max()


class MainWindow(QWidget):
    def __init__(self, core: Core, autostart=False):
        super().__init__()
        self.core = core
        self.quitting = False
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("Root")
        self.resize(1240, 780)
        self.setMinimumSize(1060, 660)
        THEME["t"] = Theme(settings.get("theme"), settings.get("accent"), settings.get("opacity"))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.titlebar = TitleBar(self)
        outer.addWidget(self.titlebar)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)

        # боковое меню
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(210)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(10, 8, 10, 12)
        sl.setSpacing(4)
        self.nav = QButtonGroup(self)
        self.nav.setExclusive(True)
        self.nav_btns = {}
        for key, text, ic in NAV:
            b = button(tr(text), ic, "nav")
            b.setCheckable(True)
            b.setIconSize(QSize(18, 18))
            b.toggled.connect(lambda on, k=key: on and self.go(k))
            self.nav.addButton(b)
            self.nav_btns[key] = b
            if key == "settings":
                sl.addSpacing(10)
                vb = button("VPN", "shield", "navvpn")
                vb.setCheckable(True)
                vb.setIconSize(QSize(18, 18))
                vb.toggled.connect(lambda on: on and self.go("vpn"))
                self.nav.addButton(vb)
                self.nav_btns["vpn"] = vb
                sl.addWidget(vb)
                sl.addStretch(1)
                self.side_status = label("", "small", wrap=True)
                sl.addWidget(self.side_status)
                sl.addSpacing(6)
            sl.addWidget(b)
        body.addWidget(side)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        self.home = HomePage(core)
        self.pages = {
            "home": self.home,
            "autotune": AutotunePage(core),
            "diag": DiagnosticsPage(core),
            "sitecheck": SiteCheckPage(core),
            "editor": EditorPage(core, self.home.cur),
            "dns": DnsPage(core),
            "files": FilesPage(core),
            "settings": SettingsPage(core, self),
            "vpn": VpnPage(core, self),
        }
        for p in self.pages.values():
            self.stack.addWidget(p)

        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(16, 16)
        self.toast = Toast(self)
        core.toast.connect(self.toast.show_msg)
        core.navigate.connect(lambda k: self.nav_btns[k].setChecked(True))
        core.state_changed.connect(self.on_state)
        core.conflicts_found.connect(self.on_conflicts)
        core.watchdog_alert.connect(self.on_watch_alert)
        core.updates_found.connect(self.on_updates)
        core.app_update_ready.connect(self.install_app_update)
        core.vpn.state_changed.connect(self.on_state)
        core.vpn.learned.connect(self.on_vpn_learned)
        self.mini = None

        self.tray = None
        self.setup_tray()
        self.apply_theme()
        self.nav_btns["home"].setChecked(True)
        self.on_state()
        if settings.get("mini_widget"):
            QTimer.singleShot(300, lambda: self.set_mini(True))
        if not winutil.is_admin():
            QTimer.singleShot(800, lambda: core.toast.emit(
                tr("Нет прав администратора — запуск winws и смена DNS работать не будут."), "error"))

    # ---------------------------------------------------------------
    def go(self, key):
        self.stack.setCurrentWidget(self.pages[key])
        refresh_icons(self.titlebar.parentWidget())

    def toggle_max(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def apply_theme(self):
        t = Theme(settings.get("theme"), settings.get("accent"), settings.get("opacity"))
        THEME["t"] = t
        QApplication.instance().setStyleSheet(t.qss())
        refresh_icons(self)
        self.titlebar.logo.setPixmap(app_icon(t.accent).pixmap(20, 20))
        self.core.theme_changed.emit()
        self.apply_background()
        if self.tray:
            self.on_state()

    def apply_background(self):
        t = THEME["t"]
        t.opacity = settings.get("opacity")
        eff = settings.get("effect")
        if winutil.IS_WIN and self.isVisible():
            c = t.bg
            winutil.set_window_effect(int(self.winId()), eff, (c.red(), c.green(), c.blue()),
                                      int(255 * min(1.0, t.opacity * 0.6)))
        self.update()

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self.apply_background)

    def nativeEvent(self, event_type, message):
        # Акрил в Windows сильно тормозит при перетаскивании окна (известная проблема DWM).
        # На время перемещения/изменения размера переключаемся на лёгкое размытие.
        if winutil.IS_WIN and settings.get("effect") == "acrylic":
            try:
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == 0x0231:      # WM_ENTERSIZEMOVE
                    self._set_effect_now("blur")
                elif msg.message == 0x0232:    # WM_EXITSIZEMOVE
                    self._set_effect_now("acrylic")
            except Exception:
                pass
        return False, 0

    def _set_effect_now(self, eff):
        t = THEME["t"]
        c = t.bg
        winutil.set_window_effect(int(self.winId()), eff, (c.red(), c.green(), c.blue()),
                                  int(255 * min(1.0, t.opacity * 0.6)))

    def paintEvent(self, e):
        t = THEME["t"]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        eff = settings.get("effect")
        alpha = t.opacity if eff != "none" else max(t.opacity, 0.96)
        if not winutil.IS_WIN:
            alpha = max(alpha, 0.0)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        rad = 0 if self.isMaximized() else RADIUS
        path.addRoundedRect(r, rad, rad)
        bg = QColor(t.bg)
        bg.setAlphaF(alpha)
        p.fillPath(path, bg)
        # лёгкий цветной отсвет акцента
        g = QLinearGradient(0, 0, self.width(), self.height())
        a1 = QColor(t.accent)
        a1.setAlphaF(0.10 if t.dark else 0.07)
        a2 = QColor(t.accent)
        a2.setAlphaF(0.0)
        g.setColorAt(0, a1)
        g.setColorAt(0.55, a2)
        p.fillPath(path, g)
        pen = QColor(255, 255, 255, 30) if t.dark else QColor(0, 0, 0, 30)
        p.setPen(pen)
        p.drawPath(path)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.grip.move(self.width() - 16, self.height() - 16)
        if self.toast.isVisible():
            self.toast.reposition()

    def changeEvent(self, e):
        if e.type() == QEvent.Type.WindowStateChange:
            self.titlebar.b_max.setProperty("ico", "copy" if self.isMaximized() else "square")
            refresh_icons(self.titlebar)
            self.update()
        super().changeEvent(e)

    # ---------------------------------------------------------------
    def on_state(self):
        a = self.core.active()
        t = THEME["t"]
        if a:
            st = f"<span style='color:#22C55E'>●</span> zapret: {a.name}"
        elif self.core.busy:
            st = f"<span style='color:#F59E0B'>●</span> {tr('Автоподбор')}…"
        else:
            st = f"<span style='color:{t.muted_hex}'>●</span> zapret: {tr('остановлен')}"
        v = self.core.vpn
        vcol = {"on": "#22C55E", "starting": "#F59E0B", "stopping": "#F59E0B"}.get(v.state, t.muted_hex)
        vtxt = {"on": tr("подключён"), "starting": tr("подключение…"), "stopping": tr("отключение…")}.get(v.state, tr("выключен"))
        st += f"<br><span style='color:{vcol}'>●</span> VPN: {vtxt}"
        self.side_status.setText(st)
        vb = self.nav_btns["vpn"]
        vb.setProperty("vpn_on", v.state == "on")
        vb.setText("VPN" + ("  ·  " + tr("вкл") if v.state == "on" else ""))
        refresh_icons(vb.parentWidget())
        ic = app_icon(t.accent, running=bool(a))
        self.setWindowIcon(ic)
        if self.tray:
            self.tray.setIcon(ic)
            self.tray.setToolTip(f"{APP_NAME} — {a.name if a else tr('Остановлен')}")
            self.build_tray_menu()

    def setup_tray(self):
        if not settings.get("tray") or not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(app_icon(settings.get("accent"), False), self)
        self.tray.activated.connect(lambda r: r in (QSystemTrayIcon.ActivationReason.Trigger,
                                                   QSystemTrayIcon.ActivationReason.DoubleClick) and self.show_normal())
        self.tray_menu = QMenu()
        self.tray.setContextMenu(self.tray_menu)
        self.build_tray_menu()
        self.tray.show()

    def build_tray_menu(self):
        if not self.tray:
            return
        m = self.tray_menu
        m.clear()
        a = self.core.active()
        m.addAction(tr("Показать"), self.show_normal)
        m.addSeparator()
        st = m.addAction(f"● {a.name}" if a else tr("Остановлен"))
        st.setEnabled(False)
        favs = [p for p in self.core.presets if self.core.is_fav(p)]
        last = self.core.by_id(settings.get("last_preset"))
        if last and last not in favs:
            favs.insert(0, last)
        if favs:
            sub = m.addMenu(tr("Избранные"))
            for p in favs[:15]:
                act = sub.addAction(p.name, lambda p=p: self.core.activate(p))
                act.setCheckable(True)
                act.setChecked(bool(a and a.id == p.id))
        m.addAction(tr("Остановить winws"), self.core.stop).setEnabled(bool(a))
        m.addSeparator()
        v = self.core.vpn
        va = m.addAction("VPN", v.toggle)
        va.setCheckable(True)
        va.setChecked(v.state in ("on", "starting"))
        va.setEnabled(v.installed() and bool(v.store.server()) and v.state in ("on", "off"))
        m.addAction(tr("Проверка сайта"), lambda: (self.show_normal(), self.nav_btns["sitecheck"].setChecked(True)))
        mw = m.addAction(tr("Мини-виджет"), lambda: self.set_mini(not settings.get("mini_widget")))
        mw.setCheckable(True)
        mw.setChecked(bool(settings.get("mini_widget")))
        m.addSeparator()
        m.addAction(tr("Выход"), self.quit_app)

    # ---- мини-виджет ----
    def set_mini(self, on: bool):
        settings.set("mini_widget", bool(on))
        if on:
            if self.mini is None:
                from .mini import MiniWidget
                self.mini = MiniWidget(self.core, self)
            self.mini.show()
        elif self.mini is not None:
            self.mini.hide()
        sp = self.pages.get("settings")
        if sp is not None and sp.mini.isChecked() != bool(on):
            sp.mini.blockSignals(True)
            sp.mini.setChecked(bool(on))
            sp.mini.blockSignals(False)
        self.build_tray_menu()

    # ---- мастер ----
    def run_wizard(self):
        from .wizard import Wizard
        w = Wizard(self.core, self)
        w.exec()
        if w.lang_changed:
            self.restart()
            return
        self.after_wizard(w)

    def after_wizard(self, w):
        self.set_mini(bool(settings.get("mini_widget")))
        self.core.apply_watchdog_settings()
        if w.run_autotune:
            self.show_normal()
            self.nav_btns["autotune"].setChecked(True)
            QTimer.singleShot(400, self.pages["autotune"].start)

    # ---- конфликты ----
    def on_conflicts(self, preset, items):
        from .conflict_dialog import ConflictDialog
        if not self.isVisible():
            self.show_normal()
        d = ConflictDialog(items, self)
        r = d.exec()
        if r == ConflictDialog.STOP:
            self.core.stop_conflicts_and_activate(preset, items)
        elif r == ConflictDialog.IGNORE:
            self.core.activate(preset, skip_conflicts=True)

    # ---- сторож ----
    def on_watch_alert(self, r):
        from .popup import Popup
        failed = ", ".join(r.get("failed", [])[:4])
        sug = r.get("suggest")
        head = tr("Похоже, обход перестал работать") if not r.get("first") else tr("Пресет не открывает ваши сервисы")
        text = f"{tr('Не открываются')}: <b>{failed}</b><br>"
        acts = []
        if sug:
            p, score = sug
            text += f"{tr('Предлагаем переключиться на')} «<b>{p.name}</b>» ({score}% {tr('у вашего провайдера')})."
            acts.append((tr("Применить"), lambda p=p: self.core.activate(p), "primary"))
        else:
            text += tr("Других проверенных пресетов пока нет — запустите автоподбор.")
            acts.append((tr("Автоподбор"), lambda: (self.show_normal(), self.nav_btns["autotune"].setChecked(True)), "primary"))
        acts.insert(0, (tr("Отказаться"), lambda: self.core.watchdog.snooze(60), None))
        Popup(head, text, acts, icon_running=True).popup()
        if self.tray and not self.isVisible():
            self.tray.showMessage(APP_NAME, f"{head}: {failed}", app_icon(T().accent, True), 4000)

    # ---- обновления ----
    def on_updates(self, items):
        from .popup import Popup
        lines = "<br>".join(f"• {tr(i['title'])}: {i.get('current') or '?'} → <b>{i['version']}</b>" for i in items)

        def later():
            skip = dict(settings.get("update_skip") or {})
            for i in items:
                skip[i["comp"]] = i["version"]
            settings.set("update_skip", skip)

        def now():
            self.show_normal()
            self.nav_btns["settings"].setChecked(True)
            self.pages["settings"].apply_updates(items)
        title = tr("Доступна новая версия ZapretCloud") if any(i["comp"] == "app" for i in items) \
            else tr("Доступно обновление движка")
        Popup(title, lines,
              [(tr("Пропустить"), later, None), (tr("Позже"), None, None), (tr("Обновить"), now, "primary")]).popup()

    def install_app_update(self, path):
        from . import updater
        try:
            updater.run_installer(Path(path))
        except OSError as e:
            self.core.toast.emit(f"{tr('Не удалось запустить установщик')}: {e}", "error")
            return
        self.quit_app()

    def on_vpn_learned(self, domain):
        msg = f"{domain} — {tr('не открывался через zapret, теперь идёт через VPN')}"
        self.core.toast.emit(msg, "info")
        if self.tray and not self.isVisible():
            self.tray.showMessage("ZapretCloud VPN", msg, app_icon(T().accent, True), 3000)

    def show_normal(self):
        self.show()
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, e):
        if not self.quitting and self.tray and settings.get("close_to_tray"):
            e.ignore()
            self.hide()
            if not settings.get("tray_hint_shown"):
                self.tray.showMessage(APP_NAME, tr("Программа свёрнута в трей"), app_icon(T().accent), 2500)
                settings.set("tray_hint_shown", True)
            return
        self.quit_app()

    def quit_app(self):
        self.quitting = True
        if self.mini is not None:
            self.mini.hide()
        if self.core.runner:
            self.core.runner.stop(full=False)
        self.core.vpn.shutdown()
        if self.tray:
            self.tray.hide()
        QApplication.instance().quit()

    def restart(self):
        exe, args = winutil.launch_command(["--restart"])
        self.quitting = True
        self.core.vpn.shutdown()
        if self.tray:
            self.tray.hide()
        QProcess.startDetached(exe, args)
        QApplication.instance().quit()
