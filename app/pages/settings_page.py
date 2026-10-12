from PyQt6.QtCore import Qt
from pathlib import Path

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QSlider, QScrollArea,
                             QMessageBox, QFileDialog, QSpinBox, QProgressBar)

from ..core import run_async
from ..i18n import tr
from ..paths import APP_NAME, APP_VERSION
from ..settings import settings
from ..theme import ACCENTS
from ..widgets import Card, label, button, page_header
from .. import winutil


def row(text, w):
    if isinstance(w, QComboBox):
        w.setMinimumWidth(220)
    h = QHBoxLayout()
    h.addWidget(label(text), 1)
    h.addWidget(w)
    return h


class SettingsPage(QWidget):
    def __init__(self, core, window):
        super().__init__()
        self.core, self.win = core, window
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(24, 16, 24, 24)
        root.setSpacing(14)
        sa.setWidget(inner)
        outer.addWidget(sa)
        hdr = QHBoxLayout()
        hdr.addWidget(page_header(tr("Настройки")), 1)
        b_donate = button(tr("Поддержать"), "heart", "primary")
        b_donate.setToolTip(tr("Поддержать разработку ZapretCloud"))
        b_donate.clicked.connect(self.show_donate)
        hdr.addWidget(b_donate, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(hdr)

        # оформление
        c = Card(pad=18, spacing=12)
        c.lay.addWidget(label(tr("Оформление"), "h2"))
        self.theme = QComboBox()
        self.theme.addItem(tr("Тёмная"), "dark")
        self.theme.addItem(tr("Светлая"), "light")
        self.theme.setCurrentIndex(self.theme.findData(settings.get("theme")))
        self.theme.currentIndexChanged.connect(lambda: self._set("theme", self.theme.currentData(), True))
        c.lay.addLayout(row(tr("Тема"), self.theme))
        sw = QHBoxLayout()
        sw.setSpacing(8)
        self.swatches = []
        for a in ACCENTS:
            b = button(kind="swatch")
            b.setProperty("accent", a)
            b.clicked.connect(lambda _=False, a=a: self._set("accent", a, True))
            self.swatches.append(b)
            sw.addWidget(b)
        w = QWidget()
        w.setLayout(sw)
        c.lay.addLayout(row(tr("Акцентный цвет"), w))
        self.effect = QComboBox()
        for k, v in (("acrylic", tr("Акрил")), ("blur", tr("Размытие")), ("none", tr("Без эффекта"))):
            self.effect.addItem(v, k)
        self.effect.setCurrentIndex(self.effect.findData(settings.get("effect")))
        self.effect.currentIndexChanged.connect(lambda: self._set("effect", self.effect.currentData(), True))
        c.lay.addLayout(row(tr("Эффект окна"), self.effect))
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(40, 100)
        self.opacity.setFixedWidth(220)
        self.opacity.setValue(int(settings.get("opacity") * 100))
        self.opacity.valueChanged.connect(lambda v: (settings.set("opacity", v / 100), self.win.apply_background()))
        c.lay.addLayout(row(tr("Прозрачность"), self.opacity))
        self.lang = QComboBox()
        self.lang.addItem("Русский", "ru")
        self.lang.addItem("English", "en")
        self.lang.setCurrentIndex(self.lang.findData(settings.get("language")))
        self.lang.currentIndexChanged.connect(self.change_lang)
        c.lay.addLayout(row(tr("Язык"), self.lang))
        root.addWidget(c)

        # запуск
        c2 = Card(pad=18, spacing=12)
        c2.lay.addWidget(label(tr("Запуск"), "h2"))
        self.auto = QCheckBox(tr("Запускать вместе с Windows"))
        self.auto.setChecked(bool(settings.get("autostart")))
        self.auto.toggled.connect(self.toggle_autostart)
        c2.lay.addWidget(self.auto)
        for key, text in (("start_last", "Активировать последний пресет при запуске"), ("tray", "Значок в трее"),
                          ("close_to_tray", "Сворачивать в трей при закрытии"),
                          ("full_stop", "Полная остановка (выгружать драйвер WinDivert)")):
            cb = QCheckBox(tr(text))
            cb.setChecked(bool(settings.get(key)))
            cb.toggled.connect(lambda v, k=key: self._set(k, v, k == "tray"))
            c2.lay.addWidget(cb)
        root.addWidget(c2)

        # сторож и виджет
        cw = Card(pad=18, spacing=12)
        cw.lay.addWidget(label(tr("Сторож и мини-виджет"), "h2"))
        self.wd = QCheckBox(tr("Сторож: проверять, что обход работает, и предлагать другой пресет"))
        self.wd.setChecked(bool(settings.get("watchdog")))
        self.wd.toggled.connect(lambda v: (settings.set("watchdog", v), core.apply_watchdog_settings()))
        cw.lay.addWidget(self.wd)
        self.wd_int = QSpinBox()
        self.wd_int.setRange(2, 60)
        self.wd_int.setSuffix(" " + tr("мин"))
        self.wd_int.setValue(int(settings.get("watchdog_interval") or 5))
        self.wd_int.valueChanged.connect(lambda v: (settings.set("watchdog_interval", v), core.apply_watchdog_settings()))
        self.wd_int.setFixedWidth(120)
        cw.lay.addLayout(row(tr("Интервал проверки (несколько лёгких запросов, нагрузка минимальна)"), self.wd_int))
        self.mini = QCheckBox(tr("Плавающий мини-виджет со статусом и кнопкой вкл/выкл"))
        self.mini.setChecked(bool(settings.get("mini_widget")))
        self.mini.toggled.connect(lambda v: self.win.set_mini(v))
        cw.lay.addWidget(self.mini)
        root.addWidget(cw)

        # обновления движка
        cu = Card(pad=18, spacing=10)
        cu.lay.addWidget(label(tr("Обновления движка"), "h2"))
        cu.lay.addWidget(label(tr("winws2 и lua — из bol-van/zapret2, winws — из bol-van/zapret, списки сайтов — из Flowseal "
                                  "(только добавление новых адресов). Перед обновлением делается резервная копия."),
                               "muted", wrap=True))
        self.upd_auto = QCheckBox(tr("Проверять обновления автоматически (раз в 24 часа)"))
        self.upd_auto.setChecked(bool(settings.get("auto_update")))
        self.upd_auto.toggled.connect(lambda v: settings.set("auto_update", v))
        cu.lay.addWidget(self.upd_auto)
        self.upd_box = QVBoxLayout()
        self.upd_box.setSpacing(6)
        cu.lay.addLayout(self.upd_box)
        self.upd_status = label("", "small", wrap=True)
        cu.lay.addWidget(self.upd_status)
        self.upd_bar = QProgressBar()
        self.upd_bar.setRange(0, 100)
        self.upd_bar.setTextVisible(False)
        self.upd_bar.setFixedHeight(6)
        self.upd_bar.hide()
        cu.lay.addWidget(self.upd_bar)
        g = QHBoxLayout()
        g.setSpacing(8)
        self.b_check = button(tr("Проверить обновления"), "refresh")
        self.b_check.clicked.connect(self.check_updates)
        self.b_apply = button(tr("Обновить выбранное"), "check", "primary")
        self.b_apply.clicked.connect(self.apply_updates)
        self.b_apply.hide()
        self.b_rb = button(tr("Откатить последнее обновление"), "x")
        self.b_rb.clicked.connect(self.rollback)
        for b in (self.b_check, self.b_apply, self.b_rb):
            g.addWidget(b)
        g.addStretch(1)
        cu.lay.addLayout(g)
        root.addWidget(cu)
        self.upd_items, self.upd_checks = [], {}
        core.update_progress.connect(self._upd_progress)
        core.update_done.connect(self._upd_done)
        self._refresh_rb()

        # профиль
        cp = Card(pad=18, spacing=10)
        cp.lay.addWidget(label(tr("Профиль"), "h2"))
        cp.lay.addWidget(label(tr("Профиль — один файл со всеми настройками, вашими пресетами, своими сайтами и "
                                  "результатами тестов. Его можно сохранить куда угодно и загрузить на этом или другом ПК."),
                               "muted", wrap=True))
        g = QHBoxLayout()
        g.setSpacing(8)
        b1 = button(tr("Сохранить профиль…"), "save", "primary")
        b1.clicked.connect(self.save_profile)
        b2 = button(tr("Загрузить профиль…"), "folder")
        b2.clicked.connect(self.load_profile)
        b3 = button(tr("Сохранить только настройки…"), "file")
        b3.clicked.connect(self.save_settings)
        for b in (b1, b2, b3):
            g.addWidget(b)
        g.addStretch(1)
        cp.lay.addLayout(g)
        g2 = QHBoxLayout()
        b4 = button(tr("Перенести данные из Zapret Studio…"), "copy")
        b4.clicked.connect(self.migrate)
        g2.addWidget(b4)
        g2.addStretch(1)
        cp.lay.addLayout(g2)
        root.addWidget(cp)

        cz = Card(pad=18, spacing=10)
        cz.lay.addWidget(label(tr("Мастер настройки"), "h2"))
        hz = QHBoxLayout()
        hz.addWidget(label(tr("Пройти первоначальную настройку заново: язык, тема, проверка конфликтов, автоподбор."),
                           "muted", wrap=True), 1)
        bz = button(tr("Запустить мастер"), "zap")
        bz.clicked.connect(lambda: self.win.run_wizard())
        hz.addWidget(bz)
        cz.lay.addLayout(hz)
        root.addWidget(cz)

        c3 = Card(pad=18, spacing=6)
        c3.lay.addWidget(label(tr("О программе"), "h2"))
        c3.lay.addWidget(label(f"{APP_NAME} {APP_VERSION}"))
        c3.lay.addWidget(label(tr("Обход блокировок на основе zapret (bol-van): winws / winws2, WinDivert."), "muted", wrap=True))
        root.addWidget(c3)
        root.addStretch(1)
        self.paint_swatches()

    def paint_swatches(self):
        cur = settings.get("accent")
        for b in self.swatches:
            a = b.property("accent")
            b.setStyleSheet(f"background:{a}; border-radius:14px; border:{'3px solid white' if a == cur else '1px solid rgba(0,0,0,0.2)'};")

    def _set(self, k, v, restyle=False):
        settings.set(k, v)
        if restyle:
            self.win.apply_theme()
            self.paint_swatches()

    def toggle_autostart(self, on):
        def done(r):
            ok, out = r
            if ok:
                settings.set("autostart", on)
                self.core.toast.emit(tr("Автозапуск включён") if on else tr("Автозапуск выключен"), "ok")
            else:
                self.auto.blockSignals(True)
                self.auto.setChecked(not on)
                self.auto.blockSignals(False)
                self.core.toast.emit(f"{tr('Не удалось изменить автозапуск')}: {out[-200:]}", "error")
        run_async(winutil.set_autostart, on, done=done)

    # ---- обновления ----
    def _refresh_rb(self):
        from .. import updater
        self.b_rb.setEnabled(updater.last_backup(self.core.data) is not None)

    def check_updates(self):
        self.b_check.setEnabled(False)
        self.upd_status.setText(tr("Проверяю…"))
        self.core.check_updates(done=self.show_updates)

    def show_updates(self, items):
        self.b_check.setEnabled(True)
        while self.upd_box.count():
            w = self.upd_box.takeAt(0).widget()
            if w:
                w.hide()
                w.deleteLater()
        self.upd_items, self.upd_checks = items, {}
        if items and items[0].get("comp") == "error":
            self.upd_status.setText(f"{tr('Не удалось проверить')}: {items[0].get('error', '')[:200]}")
            return
        any_new = False
        for it in items:
            cur = it.get("current") or tr("неизвестно")
            if it.get("error"):
                w = label(f"{tr(it['title'])}: {cur} — <span style='color:#EF4444'>{tr('ошибка')}: {it['error'][:120]}</span>",
                          wrap=True)
                self.upd_box.addWidget(w)
                continue
            if it.get("available"):
                any_new = True
                cb = QCheckBox(f"{tr(it['title'])}: {cur} → {it['version']}")
                cb.setChecked(True)
                self.upd_checks[it["comp"]] = cb
                self.upd_box.addWidget(cb)
            else:
                self.upd_box.addWidget(label(f"<span style='color:#22C55E'>✓</span> {tr(it['title'])}: {cur} — "
                                             f"{tr('актуально')}"))
        self.b_apply.setVisible(any_new)
        self.upd_status.setText(tr("Доступны обновления") if any_new else tr("Всё актуально"))

    def apply_updates(self, items=None):
        sel = items or [i for i in self.upd_items if i["comp"] in self.upd_checks and self.upd_checks[i["comp"]].isChecked()]
        if not sel:
            return
        self.b_apply.setEnabled(False)
        self.b_check.setEnabled(False)
        self.upd_bar.show()
        self.upd_bar.setValue(0)
        self.core.apply_updates(sel)

    def _upd_progress(self, text, f):
        self.upd_status.setText(text)
        self.upd_bar.show()
        self.upd_bar.setValue(int(f * 100))

    def _upd_done(self, ok, msg):
        self.upd_bar.hide()
        self.b_apply.setEnabled(True)
        self.b_check.setEnabled(True)
        self.upd_status.setText(tr("Обновление установлено") if ok and msg == "OK" else msg)
        self.core.toast.emit(tr("Движок обновлён") if ok and msg == "OK" else msg[:300], "ok" if ok else "error")
        self._refresh_rb()
        if ok:
            self.check_updates()

    def rollback(self):
        r = QMessageBox.question(self, tr("Откат"), tr("Вернуть файлы движка, которые были до последнего обновления?"))
        if r == QMessageBox.StandardButton.Yes:
            self.core.rollback_update()

    # ---- профиль ----
    def save_profile(self):
        from .. import profile
        fn, _ = QFileDialog.getSaveFileName(self, tr("Сохранить профиль"), str(Path.home() / "Desktop" / "ZapretCloud.zcprofile"),
                                            f"{tr('Профиль ZapretCloud')} (*.zcprofile)")
        if not fn:
            return
        try:
            out = profile.export_profile(Path(fn))
            self.core.toast.emit(f"{tr('Профиль сохранён')}: {out.name}", "ok")
        except Exception as e:  # noqa
            self.core.toast.emit(str(e), "error")

    def save_settings(self):
        from .. import profile
        fn, _ = QFileDialog.getSaveFileName(self, tr("Сохранить настройки"), str(Path.home() / "Desktop" / "ZapretCloud_settings.json"),
                                            f"{tr('Настройки')} (*.json)")
        if not fn:
            return
        try:
            out = profile.export_settings(Path(fn))
            self.core.toast.emit(f"{tr('Настройки сохранены')}: {out.name}", "ok")
        except Exception as e:  # noqa
            self.core.toast.emit(str(e), "error")

    def load_profile(self):
        from .. import profile
        fn, _ = QFileDialog.getOpenFileName(self, tr("Загрузить профиль"), str(Path.home() / "Desktop"),
                                            f"{tr('Профиль или настройки')} (*.zcprofile *.json)")
        if not fn:
            return
        r = QMessageBox.question(self, tr("Загрузить профиль"),
                                 tr("Текущие настройки будут заменены данными из файла. Продолжить?"))
        if r != QMessageBox.StandardButton.Yes:
            return
        try:
            profile.import_file(Path(fn))
        except Exception:  # noqa
            self.core.toast.emit(tr("Файл не похож на профиль ZapretCloud"), "error")
            return
        self.ask_restart(tr("Профиль загружен. Перезапустить программу, чтобы применить его?"))

    def migrate(self):
        from ..migrate import migrate_from
        d = QFileDialog.getExistingDirectory(self, tr("Папка со старой программой (где лежит ZapretStudio_data)"),
                                             str(Path.home() / "Desktop"))
        if not d:
            return
        if not migrate_from(Path(d)):
            self.core.toast.emit(tr("В папке не найдены данные Zapret Studio"), "error")
            return
        self.ask_restart(tr("Данные перенесены. Перезапустить программу?"))

    def show_donate(self):
        from ..donate import DonateDialog
        DonateDialog(self).exec()

    def ask_restart(self, text):
        m = QMessageBox(self)
        m.setWindowTitle(APP_NAME)
        m.setText(text)
        rb = m.addButton(tr("Перезапустить"), QMessageBox.ButtonRole.AcceptRole)
        m.addButton(tr("Позже"), QMessageBox.ButtonRole.RejectRole)
        m.exec()
        if m.clickedButton() is rb:
            self.win.restart()

    def change_lang(self):
        settings.set("language", self.lang.currentData())
        m = QMessageBox(self)
        m.setWindowTitle(tr("Язык"))
        m.setText(tr("Язык изменится после перезапуска"))
        rb = m.addButton(tr("Перезапустить"), QMessageBox.ButtonRole.AcceptRole)
        m.addButton(tr("Позже"), QMessageBox.ButtonRole.RejectRole)
        m.exec()
        if m.clickedButton() is rb:
            self.win.restart()
