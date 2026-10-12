"""Вкладка «VPN»: свой сервер (VLESS/Reality и др.), умная связка с zapret, программы, раздача на телефон."""
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QGuiApplication, QImage, QPixmap, QColor
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QCheckBox, QListWidget,
                             QListWidgetItem, QScrollArea, QProgressBar, QSpinBox, QFileDialog, QDialog,
                             QLabel, QMessageBox, QGridLayout)

from ..core import run_async
from ..i18n import tr
from ..settings import settings
from ..vpn import config as C
from ..vpn.manager import lan_ips
from ..widgets import Card, label, button, page_header, refresh_icons, T


def fmt_bytes(n: float) -> str:
    n = float(n or 0)
    for u in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if n < 1024 or u == "ТБ":
            return (f"{n:.0f} {tr(u)}" if u in ("Б", "КБ") else f"{n:.1f} {tr(u)}")
        n /= 1024
    return str(n)


def qr_pixmap(text: str, size: int = 300) -> QPixmap | None:
    try:
        import segno
    except ImportError:
        return None
    q = segno.make(text, error="m")
    rows = list(q.matrix_iter(border=3))
    n = len(rows)
    img = QImage(n, n, QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    for y, row in enumerate(rows):
        for x, v in enumerate(row):
            if v:
                img.setPixel(x, y, 0xFF000000)
    k = max(2, size // n)
    pm = QPixmap.fromImage(img.scaled(n * k, n * k, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.FastTransformation))
    return pm


class QrDialog(QDialog):
    def __init__(self, title, text, hint, parent=None, copy_text=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(10)
        lay.addWidget(label(title, "h2"))
        lay.addWidget(label(hint, "muted", wrap=True))
        pm = qr_pixmap(text, 300)
        q = QLabel()
        q.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if pm:
            q.setPixmap(pm)
            q.setStyleSheet("background:white; border-radius:10px; padding:8px;")
        else:
            q.setText(tr("Не удалось построить QR-код"))
        lay.addWidget(q, 0, Qt.AlignmentFlag.AlignHCenter)
        h = QHBoxLayout()
        h.addStretch(1)
        if copy_text:
            b = button(tr("Копировать ссылку"), "copy")
            b.clicked.connect(lambda: (QGuiApplication.clipboard().setText(copy_text), b.setText(tr("Скопировано"))))
            h.addWidget(b)
        c = button(tr("Закрыть"), None, "primary")
        c.clicked.connect(self.accept)
        h.addWidget(c)
        lay.addLayout(h)
        self.setMinimumWidth(420)


def _list(h=170):
    lw = QListWidget()
    lw.setObjectName("boxlist")
    lw.setMinimumHeight(h)
    lw.setMaximumHeight(h)
    return lw


class VpnPage(QWidget):
    def __init__(self, core, window):
        super().__init__()
        self.core, self.win = core, window
        self.vpn = core.vpn
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
        root.addWidget(page_header("VPN", tr("Ваш сервер подключается только там, где zapret не справляется — "
                                              "остальное работает напрямую, без потери скорости")))

        # ---- статус ----
        st = Card(pad=18, spacing=16, horizontal=True)
        self.power = button("", "power", "bigpower")
        self.power.setIconSize(QSize(28, 28))
        self.power.clicked.connect(self.toggle)
        st.lay.addWidget(self.power)
        col = QVBoxLayout()
        col.setSpacing(3)
        self.s_title = label("", "h2")
        self.s_sub = label("", "muted", wrap=True)
        self.s_stats = label("", "small", wrap=True)
        self.s_stats.setTextFormat(Qt.TextFormat.RichText)
        col.addWidget(self.s_title)
        col.addWidget(self.s_sub)
        col.addWidget(self.s_stats)
        st.lay.addLayout(col, 1)
        rc = QVBoxLayout()
        self.b_delay = button(tr("Проверить задержку"), "activity")
        self.b_delay.clicked.connect(self.measure)
        self.b_qr = button(tr("QR для телефона"), "layers")
        self.b_qr.clicked.connect(self.show_qr)
        self.b_fix = button(tr("Починить VPN"), "refresh")
        self.b_fix.setToolTip(tr("Если VPN не включается или завис: перезапустить его и убрать зависшие процессы"))
        self.b_fix.clicked.connect(self.vpn.repair)
        rc.addWidget(self.b_delay)
        rc.addWidget(self.b_qr)
        rc.addWidget(self.b_fix)
        st.lay.addLayout(rc)
        root.addWidget(st)

        # установка компонента
        self.inst = Card(pad=18, spacing=10)
        self.inst.lay.addWidget(label(tr("Нужен компонент VPN"), "h2"))
        self.inst.lay.addWidget(label(tr("VPN работает на ядре sing-box (бесплатное, с открытым кодом). Оно скачается "
                                         "один раз с GitHub — около 33 МБ."), "muted", wrap=True))
        h = QHBoxLayout()
        self.inst_bar = QProgressBar()
        self.inst_bar.setRange(0, 1000)
        self.inst_bar.setTextVisible(False)
        self.inst_bar.setFixedHeight(6)
        self.inst_bar.hide()
        self.b_inst = button(tr("Скачать компонент"), "save", "primary")
        self.b_inst.clicked.connect(self.install)
        h.addWidget(self.inst_bar, 1)
        h.addStretch(0)
        h.addWidget(self.b_inst)
        self.inst.lay.addLayout(h)
        root.addWidget(self.inst)
        self.vpn.install_progress.connect(lambda f: self.inst_bar.setValue(int(f * 1000)))

        # ---- серверы ----
        sc = Card(pad=18, spacing=10)
        sc.lay.addWidget(label(tr("Серверы"), "h2"))
        h = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText(tr("Вставьте ссылку vless://, vpn:// или ссылку на подписку"))
        self.inp.returnPressed.connect(self.add_input)
        b_paste = button(tr("Из буфера"), "copy")
        b_paste.clicked.connect(self.paste)
        self.b_add = button(tr("Добавить"), "plus", "primary")
        self.b_add.clicked.connect(self.add_input)
        h.addWidget(self.inp, 1)
        h.addWidget(b_paste)
        h.addWidget(self.b_add)
        sc.lay.addLayout(h)
        self.add_msg = label("", "small", wrap=True)
        self.add_msg.hide()
        sc.lay.addWidget(self.add_msg)
        self.srv_list = _list(180)
        self.srv_list.itemDoubleClicked.connect(lambda it: self.vpn.select(it.data(Qt.ItemDataRole.UserRole)))
        sc.lay.addWidget(self.srv_list)
        h = QHBoxLayout()
        b_sel = button(tr("Использовать"), "check")
        b_sel.clicked.connect(self.select_cur)
        b_ping = button(tr("Пинг"), "activity")
        b_ping.clicked.connect(lambda: self.vpn.ping_all())
        b_qr = button(tr("QR-код"), "layers")
        b_qr.clicked.connect(lambda: self.show_qr(self.cur_server_id()))
        b_del = button(tr("Удалить"), "trash", "danger")
        b_del.clicked.connect(self.del_server)
        for b in (b_sel, b_ping, b_qr):
            h.addWidget(b)
        h.addStretch(1)
        h.addWidget(b_del)
        sc.lay.addLayout(h)
        self.subs_box = QVBoxLayout()
        self.subs_box.setSpacing(6)
        sc.lay.addLayout(self.subs_box)
        root.addWidget(sc)

        # ---- режим ----
        mc = Card(pad=18, spacing=12)
        mc.lay.addWidget(label(tr("Режим работы"), "h2"))
        self.mode = QComboBox()
        self.mode.addItem(tr("TUN — весь трафик компьютера (игры, Discord, все программы)"), "tun")
        self.mode.addItem(tr("Системный прокси — браузеры и программы с поддержкой прокси"), "proxy")
        self.mode.setCurrentIndex(max(0, self.mode.findData(settings.get("vpn_mode"))))
        self.mode.currentIndexChanged.connect(lambda: self._set("vpn_mode", self.mode.currentData(), True))
        mc.lay.addLayout(self._row(tr("Как подключать"), self.mode))
        self.route = QComboBox()
        self.route.addItem(tr("Умная — zapret, а VPN только там, где zapret не справился"), "smart")
        self.route.addItem(tr("Только сайты из списка"), "list")
        self.route.addItem(tr("Всё через VPN"), "all")
        self.route.setCurrentIndex(max(0, self.route.findData(settings.get("vpn_route"))))
        self.route.currentIndexChanged.connect(lambda: self._set("vpn_route", self.route.currentData(), True))
        mc.lay.addLayout(self._row(tr("Что пускать через VPN"), self.route))
        self.learn = QCheckBox(tr("Автоматически переводить на VPN сайты, которые не открываются через zapret"))
        self.learn.setChecked(bool(settings.get("vpn_learn")))
        self.learn.toggled.connect(lambda v: self._set("vpn_learn", v, True))
        self.ru = QCheckBox(tr("Российские сайты всегда напрямую"))
        self.ru.setChecked(bool(settings.get("vpn_ru_direct")))
        self.ru.toggled.connect(lambda v: (settings.set("vpn_ru_direct", v), self.vpn.lists_updated()))
        self.auto = QCheckBox(tr("Включать VPN при запуске программы"))
        self.auto.setChecked(bool(settings.get("vpn_autostart")))
        self.auto.toggled.connect(lambda v: settings.set("vpn_autostart", v))
        for w in (self.learn, self.ru, self.auto):
            mc.lay.addWidget(w)
        self.mode_hint = label("", "small", wrap=True)
        mc.lay.addWidget(self.mode_hint)
        root.addWidget(mc)

        # ---- сайты ----
        lc = Card(pad=18, spacing=10)
        lc.lay.addWidget(label(tr("Всегда через VPN"), "h2"))
        lc.lay.addWidget(label(tr("Отметьте готовые наборы — это сервисы, которые сами закрыты для России или блокируются "
                                  "по IP (zapret им не поможет). Ниже можно добавить свои сайты."), "muted", wrap=True))
        g = QGridLayout()
        g.setHorizontalSpacing(18)
        self.pack_cb = {}
        for i, (k, (title, _d)) in enumerate(C.PACKS.items()):
            cb = QCheckBox(tr(title))
            cb.setChecked(k in self.vpn.store.packs)
            cb.toggled.connect(lambda v, k=k: self.set_pack(k, v))
            self.pack_cb[k] = cb
            g.addWidget(cb, i // 2, i % 2)
        lc.lay.addLayout(g)
        lc.lay.addSpacing(4)
        lc.lay.addWidget(label(tr("Свои сайты через VPN"), None))
        self.l_vpn, self.i_vpn = self._domain_col(lc.lay, False)
        h = QHBoxLayout()
        self.auto_lbl = label("", "small", wrap=True)
        b_forget = button(tr("Сбросить выученные"), "refresh")
        b_forget.setToolTip(tr("Убрать сайты, которые программа перевела на VPN автоматически"))
        b_forget.clicked.connect(self.vpn.forget_auto)
        h.addWidget(self.auto_lbl, 1)
        h.addWidget(b_forget)
        lc.lay.addLayout(h)
        root.addWidget(lc)

        xc = Card(pad=18, spacing=10)
        xc.lay.addWidget(label(tr("Исключения — никогда через VPN"), "h2"))
        xc.lay.addWidget(label(tr("Эти сайты всегда идут напрямую через zapret — даже в режиме «Всё через VPN» и даже если "
                                  "программа хотела перевести их на VPN. Например: банк, госуслуги или игра, которой VPN мешает. "
                                  "Обычно этот список можно оставить пустым."), "muted", wrap=True))
        self.l_dir, self.i_dir = self._domain_col(xc.lay, True)
        root.addWidget(xc)

        # ---- программы ----
        ac = Card(pad=18, spacing=10)
        ac.lay.addWidget(label(tr("Программы"), "h2"))
        ac.lay.addWidget(label(tr("Выбранная программа всегда идёт через VPN или всегда напрямую — независимо от сайтов. "
                                  "Например: Telegram или игра через VPN, торрент-клиент напрямую. Лучше всего работает "
                                  "в режиме TUN."), "muted", wrap=True))
        self.app_list = _list(120)
        ac.lay.addWidget(self.app_list)
        h = QHBoxLayout()
        b1 = button(tr("Добавить программу…"), "plus")
        b1.clicked.connect(self.add_app)
        b2 = button(tr("VPN / напрямую"), "refresh")
        b2.clicked.connect(self.flip_app)
        b3 = button(tr("Удалить"), "trash", "danger")
        b3.clicked.connect(self.del_app)
        h.addWidget(b1)
        h.addWidget(b2)
        h.addStretch(1)
        h.addWidget(b3)
        ac.lay.addLayout(h)
        root.addWidget(ac)

        # ---- телефон ----
        pc = Card(pad=18, spacing=10)
        pc.lay.addWidget(label(tr("Раздача на телефон"), "h2"))
        pc.lay.addWidget(label(tr("Телефон или другое устройство в той же Wi-Fi сети будет работать через этот компьютер: "
                                  "где справляется zapret — через zapret, где нет — через VPN."), "muted", wrap=True))
        h = QHBoxLayout()
        self.lan = QCheckBox(tr("Раздавать в домашнюю сеть"))
        self.lan.setChecked(bool(settings.get("vpn_lan")))
        self.lan.toggled.connect(lambda v: (self._set("vpn_lan", v, True), self.b_tgqr.setEnabled(v)))
        self.port = QSpinBox()
        self.port.setRange(1025, 65000)
        self.port.setValue(int(settings.get("vpn_port") or 10808))
        self.port.setPrefix(tr("порт") + " ")
        self.port.editingFinished.connect(lambda: self._set("vpn_port", self.port.value(), True))
        h.addWidget(self.lan, 1)
        h.addWidget(self.port)
        pc.lay.addLayout(h)
        self.lan_info = label("", wrap=True)
        self.lan_info.setTextFormat(Qt.TextFormat.RichText)
        self.lan_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        pc.lay.addWidget(self.lan_info)
        h = QHBoxLayout()
        self.b_tgqr = button(tr("QR для Telegram на телефоне"), "layers")
        self.b_tgqr.clicked.connect(self.show_tg_qr)
        h.addWidget(self.b_tgqr)
        h.addStretch(1)
        pc.lay.addLayout(h)
        root.addWidget(pc)
        root.addStretch(1)

        self.vpn.state_changed.connect(self.refresh_state)
        self.vpn.servers_changed.connect(self.fill_servers)
        self.vpn.lists_changed.connect(self.fill_lists)
        self.vpn.stats.connect(self.refresh_stats)
        self.delay = None
        self.fill_servers()
        self.fill_lists()
        self.fill_apps()
        self.refresh_state()

    # ---------- helpers ----------
    def _row(self, text, w):
        w.setMinimumWidth(460)
        h = QHBoxLayout()
        h.addWidget(label(text), 1)
        h.addWidget(w)
        return h

    def _domain_col(self, parent, direct):
        lw = _list(140)
        parent.addWidget(lw)
        h = QHBoxLayout()
        inp = QLineEdit()
        inp.setPlaceholderText(tr("Адрес сайта, например example.com"))
        add = button(tr("Добавить"), "plus")
        rm = button(tr("Удалить выбранный"), "trash")
        add.clicked.connect(lambda: self.add_domain(inp, direct))
        inp.returnPressed.connect(lambda: self.add_domain(inp, direct))
        rm.clicked.connect(lambda: self.del_domain(lw, direct))
        h.addWidget(inp, 1)
        h.addWidget(add)
        h.addWidget(rm)
        parent.addLayout(h)
        return lw, inp

    def _set(self, key, val, restart=False):
        if settings.get(key) == val:
            return
        settings.set(key, val)
        self.refresh_state()
        if restart and self.vpn.state == "on":
            self.vpn.restart()

    # ---------- статус ----------
    def refresh_state(self):
        v = self.vpn
        inst = v.installed()
        self.inst.setVisible(not inst)
        srv = v.store.server()
        on = v.state == "on"
        self.power.setProperty("on", "true" if on else "false")
        self.power.style().unpolish(self.power)
        self.power.style().polish(self.power)
        refresh_icons(self.power.parentWidget())
        self.power.setEnabled(inst and bool(srv) and v.state not in ("starting", "stopping"))
        self.b_fix.setEnabled(inst and bool(srv) and v.state not in ("starting", "stopping"))
        modes = {"tun": "TUN", "proxy": tr("системный прокси")}
        routes = {"smart": tr("умный режим"), "list": tr("только список"), "all": tr("всё через VPN")}
        if v.state == "starting":
            self.s_title.setText(tr("Подключение…"))
        elif v.state == "stopping":
            self.s_title.setText(tr("Отключение…"))
        elif on:
            self.s_title.setText(f"<span style='color:#22C55E'>●</span> {tr('VPN подключён')}")
        else:
            self.s_title.setText(tr("VPN выключен"))
        if not srv:
            self.s_sub.setText(tr("Добавьте свой сервер ниже — ссылкой vless://, vpn:// или подпиской."))
        else:
            m = v.mode if on else settings.get("vpn_mode")
            r = v.route if on else settings.get("vpn_route")
            self.s_sub.setText(f"{srv['name']}  ·  {srv['proto']}  ·  {modes.get(m, m)}  ·  {routes.get(r, r)}")
        if not on:
            self.s_stats.setText(f"<span style='color:#F87171'>{v.error}</span>" if v.error else "")
        self.b_delay.setEnabled(on)
        self.b_qr.setEnabled(bool(srv))
        self.learn.setEnabled(settings.get("vpn_route") == "smart")
        self.ru.setEnabled(True)
        hint = {"tun": tr("TUN перехватывает весь трафик. zapret при этом продолжает работать — программа "
                          "сама перенастроит его на физическую сеть."),
                "proxy": tr("Системный прокси подхватывают браузеры и большинство программ. Игры и Discord-голос "
                            "могут идти мимо — для них выберите TUN.")}
        self.mode_hint.setText(hint.get(settings.get("vpn_mode"), ""))
        self.refresh_lan()
        self.refresh_stats()

    def refresh_stats(self):
        v = self.vpn
        if v.state != "on":
            return
        up, down = v.speed
        tu, td = v.traffic
        parts = [f"↓ {fmt_bytes(down)}/{tr('с')}  ↑ {fmt_bytes(up)}/{tr('с')}",
                 f"{tr('всего')} ↓ {fmt_bytes(td)} ↑ {fmt_bytes(tu)}"]
        if self.delay is not None:
            parts.append(f"{tr('задержка')} {self.delay} {tr('мс')}" if self.delay >= 0 else tr("задержка: нет ответа"))
        s = "  ·  ".join(parts)
        if v.now_vpn:
            sites = ", ".join(list(v.now_vpn)[:6])
            more = len(v.now_vpn) - 6
            s += f"<br>{tr('Сейчас через VPN')}: <b>{sites}</b>" + (f" {tr('и ещё')} {more}" if more > 0 else "")
        elif v.route != "all":
            s += f"<br>{tr('Сейчас через VPN')}: —"
        self.s_stats.setText(s)

    def toggle(self):
        self.delay = None
        self.vpn.toggle()

    def measure(self):
        self.b_delay.setEnabled(False)

        def done(ms):
            self.delay = ms
            self.b_delay.setEnabled(self.vpn.state == "on")
            self.refresh_stats()
        self.vpn.real_delay(done)

    def install(self):
        self.b_inst.setEnabled(False)
        self.inst_bar.show()

        def ok(_):
            self.inst_bar.hide()
            self.core.toast.emit(tr("Компонент VPN установлен"), "ok")
            self.refresh_state()

        def bad(e):
            self.inst_bar.hide()
            self.b_inst.setEnabled(True)
            self.core.toast.emit(tr("Не удалось скачать компонент") + f": {e}", "error")
        run_async(self.vpn.install, done=ok, fail=bad)

    # ---------- серверы ----------
    def cur_server_id(self):
        it = self.srv_list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else self.vpn.store.selected

    def fill_servers(self):
        st = self.vpn.store
        cur = self.cur_server_id()
        self.srv_list.clear()
        subs = {s["id"]: s for s in st.subs}
        for s in st.servers:
            ping = self.vpn.pings.get(s["id"])
            ptxt = "" if ping is None else (f"{ping} {tr('мс')}" if ping >= 0 else tr("нет ответа"))
            mark = "●  " if s["id"] == st.selected else "    "
            sub = subs.get(s.get("sub"))
            src = f"  ·  {sub.get('name')}" if sub else ""
            it = QListWidgetItem(f"{mark}{s['name']}    {s['proto']} · {s['host']}:{s['port']}{src}    {ptxt}")
            it.setData(Qt.ItemDataRole.UserRole, s["id"])
            if s["id"] == st.selected:
                f = it.font()
                f.setBold(True)
                it.setFont(f)
            if ping is not None:
                it.setForeground(QColor("#22C55E" if 0 <= ping < 150 else "#F59E0B" if ping >= 0 else "#F87171"))
            self.srv_list.addItem(it)
            if s["id"] == cur:
                self.srv_list.setCurrentItem(it)
        if not st.servers:
            it = QListWidgetItem(tr("Серверов пока нет"))
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.srv_list.addItem(it)
        # подписки
        while self.subs_box.count():
            w = self.subs_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        for s in st.subs:
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            info = s.get("info") or {}
            txt = f"<b>{tr('Подписка')} «{s.get('name')}»</b>"
            used = (info.get("upload") or 0) + (info.get("download") or 0)
            if info.get("total"):
                txt += f"  ·  {fmt_bytes(used)} {tr('из')} {fmt_bytes(info['total'])}"
            elif used:
                txt += f"  ·  {tr('использовано')} {fmt_bytes(used)}"
            if info.get("expire"):
                txt += f"  ·  {tr('до')} {time.strftime('%d.%m.%Y', time.localtime(info['expire']))}"
            if s.get("updated"):
                txt += f"  ·  {tr('обновлена')} {time.strftime('%d.%m %H:%M', time.localtime(s['updated']))}"
            lb = label(txt, "small", wrap=True)
            lb.setTextFormat(Qt.TextFormat.RichText)
            b1 = button(tr("Обновить"), "refresh")
            b1.clicked.connect(self.refresh_subs)
            b2 = button("", "trash", "danger", tip=tr("Удалить подписку и её серверы"))
            b2.clicked.connect(lambda _=False, i=s["id"]: self.vpn.remove_sub(i))
            h.addWidget(lb, 1)
            h.addWidget(b1)
            h.addWidget(b2)
            self.subs_box.addWidget(w)
        self.refresh_state()

    def paste(self):
        t = QGuiApplication.clipboard().text().strip()
        if t:
            self.inp.setText(t if len(t) < 3000 else t[:3000])
            self.add_input(text=t)

    def add_input(self, text=None):
        text = (text if isinstance(text, str) else None) or self.inp.text().strip()
        if not text:
            return
        self.b_add.setEnabled(False)
        self.add_msg.show()
        self.add_msg.setText(tr("Загрузка…"))

        def done(n, errors, _msg):
            self.b_add.setEnabled(True)
            if n:
                self.inp.clear()
                msg = f"<span style='color:#22C55E'>✓</span> {tr('Добавлено серверов')}: {n}"
                if errors:
                    msg += f"  ·  {tr('пропущено')}: {len(errors)} ({tr(errors[0])})"
                self.vpn.ping_all()
            else:
                msg = "<span style='color:#F87171'>×</span> " + (tr(errors[0]) if errors else tr("Ссылки не найдены"))
            self.add_msg.setText(msg)
        self.vpn.add_input(text, done)

    def select_cur(self):
        sid = self.cur_server_id()
        if sid:
            self.vpn.select(sid)

    def del_server(self):
        sid = self.cur_server_id()
        s = self.vpn.store.server(sid)
        if s and QMessageBox.question(self, tr("Удалить сервер"), f"{tr('Удалить сервер')} «{s['name']}»?") \
                == QMessageBox.StandardButton.Yes:
            self.vpn.remove_server(sid)

    def refresh_subs(self):
        self.vpn.refresh_subs(done=lambda errs: self.core.toast.emit(
            errs[0] if errs else tr("Подписки обновлены"), "error" if errs else "ok"))

    def show_qr(self, sid=None):
        s = self.vpn.store.server(sid if isinstance(sid, str) else None)
        if not s:
            return
        if s["link"].startswith("singbox:"):
            self.core.toast.emit(tr("Для этого сервера нет ссылки — QR-код недоступен"), "error")
            return
        QrDialog(tr("QR-код сервера"), s["link"],
                 tr("Отсканируйте камерой в Happ, v2RayTun или Streisand на телефоне — сервер добавится сам. "
                    "Не показывайте этот код посторонним: в нём ключ доступа к серверу."), self, copy_text=s["link"]).exec()

    # ---------- списки сайтов ----------
    def set_pack(self, k, on):
        p = self.vpn.store.packs
        if on and k not in p:
            p.append(k)
        elif not on and k in p:
            p.remove(k)
        self.vpn.lists_updated()

    def fill_lists(self):
        st = self.vpn.store
        self.l_vpn.clear()
        for d in sorted(st.domains):
            it = QListWidgetItem(d)
            it.setData(Qt.ItemDataRole.UserRole, ("m", d))
            self.l_vpn.addItem(it)
        for d in sorted(st.auto, key=lambda x: -st.auto[x].get("ts", 0)):
            it = QListWidgetItem(f"{d}    · {tr('авто')}")
            it.setData(Qt.ItemDataRole.UserRole, ("a", d))
            it.setForeground(QColor(T().muted_hex))
            it.setToolTip(tr("Переведён на VPN автоматически") + ": " +
                          time.strftime("%d.%m %H:%M", time.localtime(st.auto[d].get("ts", 0))))
            self.l_vpn.addItem(it)
        self.l_dir.clear()
        for d in sorted(st.direct):
            it = QListWidgetItem(d)
            it.setData(Qt.ItemDataRole.UserRole, ("d", d))
            self.l_dir.addItem(it)
        for lw, empty in ((self.l_vpn, tr("Пока пусто — добавьте сайт ниже")),
                          (self.l_dir, tr("Пусто — исключений нет"))):
            if lw.count() == 0:
                it = QListWidgetItem(empty)
                it.setFlags(Qt.ItemFlag.NoItemFlags)
                it.setForeground(QColor(T().muted_hex))
                lw.addItem(it)
        n = len(st.auto)
        self.auto_lbl.setText(tr("Выучено автоматически") + f": {n}. " +
                              tr("Раз в 6 часов программа перепроверяет их и возвращает на zapret те, что снова "
                                 "открываются напрямую."))

    def add_domain(self, inp, direct):
        if self.vpn.add_domain(inp.text(), direct):
            inp.clear()
        else:
            self.core.toast.emit(tr("Неверный адрес сайта"), "error")

    def del_domain(self, lw, direct):
        it = lw.currentItem()
        if not it:
            return
        if not it.data(Qt.ItemDataRole.UserRole):
            return
        kind, d = it.data(Qt.ItemDataRole.UserRole)
        st = self.vpn.store
        if kind == "a":
            st.auto.pop(d, None)
        elif kind == "m" and d in st.domains:
            st.domains.remove(d)
        elif kind == "d" and d in st.direct:
            st.direct.remove(d)
        self.vpn.lists_updated()

    # ---------- программы ----------
    def fill_apps(self):
        self.app_list.clear()
        for a in self.vpn.store.apps:
            via = tr("через VPN") if a["via"] == "vpn" else tr("напрямую")
            it = QListWidgetItem(f"{a['name']}    — {via}    {a.get('path', '')}")
            it.setData(Qt.ItemDataRole.UserRole, a["name"])
            it.setForeground(QColor("#22C55E" if a["via"] == "vpn" else T().muted_hex))
            self.app_list.addItem(it)
        if not self.vpn.store.apps:
            it = QListWidgetItem(tr("Программ пока нет"))
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.app_list.addItem(it)

    def add_app(self):
        fn, _ = QFileDialog.getOpenFileName(self, tr("Выберите программу"), "C:/", tr("Программы") + " (*.exe)")
        if not fn:
            return
        name = Path(fn).name
        apps = self.vpn.store.apps
        if any(a["name"].lower() == name.lower() for a in apps):
            return
        apps.append({"name": name, "path": fn, "via": "vpn"})
        self.vpn.lists_updated(need_restart=True)
        self.fill_apps()

    def _cur_app(self):
        it = self.app_list.currentItem()
        n = it.data(Qt.ItemDataRole.UserRole) if it else None
        return next((a for a in self.vpn.store.apps if a["name"] == n), None)

    def flip_app(self):
        a = self._cur_app()
        if a:
            a["via"] = "direct" if a["via"] == "vpn" else "vpn"
            self.vpn.lists_updated(need_restart=True)
            self.fill_apps()

    def del_app(self):
        a = self._cur_app()
        if a:
            self.vpn.store.apps.remove(a)
            self.vpn.lists_updated(need_restart=True)
            self.fill_apps()

    # ---------- телефон ----------
    def refresh_lan(self):
        port = int(settings.get("vpn_port") or 10808)
        if hasattr(self, "b_tgqr"):
            self.b_tgqr.setEnabled(bool(settings.get("vpn_lan")))
        if not settings.get("vpn_lan"):
            self.lan_info.setText(f"<span style='color:{T().muted_hex}'>" +
                                  tr("Выключено. Включите галочку, затем на телефоне укажите прокси в настройках Wi-Fi.") +
                                  "</span>")
            return
        ips = lan_ips()
        ip = ips[0] if ips else "?"
        on = self.vpn.state == "on"
        st = (f"<span style='color:#22C55E'>●</span> {tr('Работает')}" if on else
              f"<span style='color:#F59E0B'>●</span> {tr('Заработает после включения VPN')}")
        self.lan_info.setText(
            f"{st}<br><br><b>iPhone:</b> {tr('Настройки → Wi-Fi → (i) у вашей сети → Прокси → Вручную')}<br>"
            f"<b>Android:</b> {tr('Настройки → Wi-Fi → ваша сеть → Изменить → Прокси → Вручную')}<br>"
            f"{tr('Сервер')}: <b style='font-size:16px'>{ip}</b>   {tr('Порт')}: <b style='font-size:16px'>{port}</b><br>"
            f"<b>Telegram:</b> {tr('свой прокси — кнопка «QR для Telegram» ниже, или вручную: Настройки → Данные и память → Прокси → SOCKS5, тот же сервер и порт')}"
            + (f"<br><span style='color:{T().muted_hex}'>{tr('Другие адреса этого ПК')}: {', '.join(ips[1:])}</span>"
               if len(ips) > 1 else "") +
            "<br><span style='color:" + T().muted_hex + f"'>{tr('Доступ разрешён только из домашней сети. Работает, пока ПК включён и VPN подключён.')}</span>")

    def show_tg_qr(self):
        ips = lan_ips()
        if not ips:
            self.core.toast.emit(tr("Не найден адрес компьютера в домашней сети"), "error")
            return
        port = int(settings.get("vpn_port") or 10808)
        link = f"tg://socks?server={ips[0]}&port={port}"
        QrDialog(tr("Telegram через компьютер"), link,
                 tr("Telegram не использует прокси из настроек Wi-Fi, ему нужен свой. Отсканируйте код камерой "
                    "телефона — откроется Telegram и предложит подключить прокси. Работает, пока телефон в домашней "
                    "Wi-Fi сети, а на ПК включён VPN."), self, copy_text=link).exec()

    def showEvent(self, e):
        super().showEvent(e)
        self.refresh_state()
