"""Мастер первого запуска: язык → тема → проверка конфликтов → параметры → готово."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QStackedWidget, QRadioButton, QCheckBox, QWidget,
                             QButtonGroup, QApplication)

from . import conflicts, i18n
from .core import run_async
from .i18n import tr
from .icons import app_icon
from .paths import APP_NAME
from .settings import settings
from .theme import ACCENTS, Theme
from .widgets import THEME, label, button


class Wizard(QDialog):
    def __init__(self, core, window=None):
        super().__init__(window)
        self.core, self.win = core, window
        self.run_autotune = False
        self.lang_changed = False
        self.setWindowTitle(f"{APP_NAME} — {tr('Мастер настройки')}")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(620, 520)
        self.found = []
        self.build(0)

    # ------------------------------------------------------------ сборка
    def build(self, start):
        if self.layout():
            QWidget().setLayout(self.layout())   # убираем старый layout
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 22)
        lay.setSpacing(12)
        top = QHBoxLayout()
        ic = label()
        ic.setPixmap(app_icon().pixmap(40, 40))
        top.addWidget(ic)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(label(tr("Добро пожаловать в ZapretCloud"), "h1"))
        self.step_lbl = label("", "muted")
        col.addWidget(self.step_lbl)
        top.addLayout(col, 1)
        lay.addLayout(top)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        self.pages = [self.p_lang(), self.p_theme(), self.p_conf(), self.p_opts(), self.p_done()]
        for p in self.pages:
            self.stack.addWidget(p)
        bb = QHBoxLayout()
        self.b_skip = button(tr("Пропустить мастер"))
        self.b_skip.clicked.connect(self.finish_skip)
        bb.addWidget(self.b_skip)
        bb.addStretch(1)
        self.b_back = button(tr("Назад"))
        self.b_back.clicked.connect(lambda: self.go(self.stack.currentIndex() - 1))
        self.b_next = button(tr("Далее"), None, "primary")
        self.b_next.clicked.connect(self.next)
        bb.addWidget(self.b_back)
        bb.addWidget(self.b_next)
        lay.addLayout(bb)
        self.go(start)

    def page(self, title, text=""):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 8, 0, 0)
        l.setSpacing(10)
        l.addWidget(label(title, "h2"))
        if text:
            l.addWidget(label(text, "muted", wrap=True))
        return w, l

    def p_lang(self):
        w, l = self.page(tr("Язык"), "Выберите язык интерфейса / Choose interface language")
        self.lang_g = QButtonGroup(w)
        for code, name in (("ru", "Русский"), ("en", "English")):
            rb = QRadioButton(name)
            rb.setProperty("code", code)
            rb.setChecked(settings.get("language") == code)
            self.lang_g.addButton(rb)
            l.addWidget(rb)
        l.addStretch(1)
        return w

    def p_theme(self):
        w, l = self.page(tr("Оформление"), tr("Тему и цвет можно изменить позже в настройках."))
        self.theme_g = QButtonGroup(w)
        for code, name in (("dark", tr("Тёмная")), ("light", tr("Светлая"))):
            rb = QRadioButton(name)
            rb.setProperty("code", code)
            rb.setChecked(settings.get("theme") == code)
            rb.toggled.connect(lambda on, c=code: on and self.set_theme(theme=c))
            self.theme_g.addButton(rb)
            l.addWidget(rb)
        l.addWidget(label(tr("Акцентный цвет")))
        h = QHBoxLayout()
        self.sw = []
        for a in ACCENTS:
            b = button(kind="swatch")
            b.setProperty("accent", a)
            b.clicked.connect(lambda _=False, a=a: self.set_theme(accent=a))
            self.sw.append(b)
            h.addWidget(b)
        h.addStretch(1)
        l.addLayout(h)
        l.addStretch(1)
        self.paint_sw()
        return w

    def p_conf(self):
        w, l = self.page(tr("Проверка конфликтов"),
                         tr("Другие программы обхода (GoodbyeDPI, другие сборки zapret и т.п.) мешают работе ZapretCloud."))
        self.conf_lbl = label(tr("Проверяю…"), wrap=True)
        l.addWidget(self.conf_lbl)
        h = QHBoxLayout()
        self.b_conf_stop = button(tr("Остановить мешающее"), "power", "danger")
        self.b_conf_stop.clicked.connect(self.stop_conf)
        self.b_conf_stop.hide()
        b = button(tr("Проверить снова"), "refresh")
        b.clicked.connect(self.check_conf)
        h.addWidget(self.b_conf_stop)
        h.addWidget(b)
        h.addStretch(1)
        l.addLayout(h)
        l.addStretch(1)
        return w

    def p_opts(self):
        w, l = self.page(tr("Параметры"), tr("Всё это можно изменить позже в настройках."))
        self.opts = {}
        for key, text in (("autostart", "Запускать вместе с Windows"),
                          ("start_last", "Активировать последний пресет при запуске"),
                          ("watchdog", "Сторож: проверять, что обход работает, и предлагать другой пресет"),
                          ("mini_widget", "Плавающий мини-виджет со статусом и кнопкой вкл/выкл"),
                          ("auto_update", "Проверять обновления автоматически (раз в 24 часа)"),
                          ("tray", "Значок в трее")):
            cb = QCheckBox(tr(text))
            cb.setChecked(bool(settings.get(key)))
            self.opts[key] = cb
            l.addWidget(cb)
        l.addStretch(1)
        return w

    def p_done(self):
        w, l = self.page(tr("Всё готово!"), tr("Осталось подобрать пресет, который лучше всего работает у вашего провайдера. "
                                             "Автоподбор по очереди проверит пресеты на YouTube, Discord, Telegram, играх "
                                             "и ИИ-сервисах — это займёт несколько минут."))
        self.cb_tune = QCheckBox(tr("Запустить автоподбор сейчас"))
        self.cb_tune.setChecked(not self.core.results.data.get(self.core.isp_key))
        l.addWidget(self.cb_tune)
        l.addWidget(label(tr("Подсказка: если какой-то сайт не открывается — вкладка «Проверка сайта» покажет причину "
                             "и добавит сайт в обход в один клик."), "small", wrap=True))
        l.addStretch(1)
        return w

    # ------------------------------------------------------------ логика
    def go(self, i):
        i = max(0, min(i, len(self.pages) - 1))
        self.stack.setCurrentIndex(i)
        self.step_lbl.setText(f"{tr('Шаг')} {i + 1} / {len(self.pages)}")
        self.b_back.setEnabled(i > 0)
        self.b_next.setText(tr("Готово") if i == len(self.pages) - 1 else tr("Далее"))
        if i == 2:
            self.check_conf()

    def next(self):
        i = self.stack.currentIndex()
        if i == 0:
            code = next((b.property("code") for b in self.lang_g.buttons() if b.isChecked()), "ru")
            if code != settings.get("language"):
                settings.set("language", code)
                i18n.set_lang(code)
                self.lang_changed = True
                self.build(1)
                return
        if i == len(self.pages) - 1:
            return self.finish()
        self.go(i + 1)

    def set_theme(self, theme=None, accent=None):
        if theme:
            settings.set("theme", theme)
        if accent:
            settings.set("accent", accent)
        t = Theme(settings.get("theme"), settings.get("accent"), settings.get("opacity"))
        THEME["t"] = t
        if self.win:
            self.win.apply_theme()
        else:
            QApplication.instance().setStyleSheet(t.qss())
        self.paint_sw()

    def paint_sw(self):
        cur = settings.get("accent")
        for b in self.sw:
            a = b.property("accent")
            b.setStyleSheet(f"background:{a}; border-radius:14px; border:{'3px solid white' if a == cur else '1px solid rgba(0,0,0,0.2)'};")

    def check_conf(self):
        self.conf_lbl.setText(tr("Проверяю…"))
        own = [self.core.runner.proc.pid] if self.core.runner and self.core.runner.alive() else []
        run_async(conflicts.detect, own, done=self.show_conf)

    def show_conf(self, found):
        self.found = found
        if not found:
            self.conf_lbl.setText(f"<span style='color:#22C55E'>✓</span> {tr('Мешающих программ не найдено')}")
            self.b_conf_stop.hide()
            return
        rows = [f"<span style='color:{'#EF4444' if f['blocking'] else '#F59E0B'}'>●</span> "
                f"{tr(f['title']) if f['kind'] != 'vpn' else f['title']}" for f in found]
        self.conf_lbl.setText("<br>".join(rows))
        self.b_conf_stop.setVisible(any(f["blocking"] for f in found))

    def stop_conf(self):
        run_async(conflicts.stop, [f for f in self.found if f["blocking"]], done=lambda e: self.check_conf())

    def finish(self):
        for key, cb in self.opts.items():
            v = cb.isChecked()
            if key == "autostart":
                if v != bool(settings.get("autostart")):
                    from . import winutil
                    run_async(winutil.set_autostart, v,
                              done=lambda r, v=v: r[0] and settings.set("autostart", v))
                continue
            settings.set(key, v)
        self.run_autotune = self.cb_tune.isChecked()
        settings.set("wizard_done", True)
        self.accept()

    def finish_skip(self):
        settings.set("wizard_done", True)
        self.reject()
