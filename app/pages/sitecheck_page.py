"""Вкладка «Проверка сайта»: почему сайт не открывается и добавление в «Свои сайты»."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QCheckBox

from ..core import run_async
from ..i18n import tr
from ..icons import icon
from .. import sites as S
from .. import sitecheck
from ..widgets import Card, label, button, page_header, T

VERDICT = {
    "ok": ("#22C55E", "Сайт открывается", "Блокировки не обнаружено."),
    "dns": ("#F59E0B", "Блокировка через DNS",
            "Провайдер подменяет адрес сайта. Включите DoH на вкладке DNS — обычно этого достаточно."),
    "ip": ("#EF4444", "Блокировка по IP-адресу",
           "Подключение к серверу не устанавливается. Добавьте сайт в «Свои сайты» с галочкой «добавлять IP»."),
    "dpi": ("#EF4444", "Блокировка DPI (по имени сайта)",
            "Провайдер обрывает защищённое соединение. Добавьте сайт в «Свои сайты» — пресет начнёт обходить блокировку."),
    "http": ("#F59E0B", "Сайт отвечает с ошибкой",
             "Соединение есть, но сервер не ответил нормально. Возможна блокировка или сайт временно не работает."),
    "down": ("#9CA3AF", "Сайт не найден", "Домен не существует или нет интернета. Проверьте адрес."),
    "bad": ("#9CA3AF", "Неверный адрес", "Введите адрес сайта, например example.com"),
}


class SiteCheckPage(QWidget):
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.last = None
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 24)
        root.setSpacing(14)
        root.addWidget(page_header(tr("Проверка сайта"), tr("Узнайте, почему сайт не открывается, и включите для него обход")))

        c = Card(pad=18, spacing=10, horizontal=True)
        self.inp = QLineEdit()
        self.inp.setPlaceholderText(tr("Адрес сайта, например rutracker.org или https://site.com/page"))
        self.inp.addAction(icon("globe", T().muted_hex, 16), QLineEdit.ActionPosition.LeadingPosition)
        self.inp.returnPressed.connect(self.run)
        self.btn = button(tr("Проверить"), "search", "primary")
        self.btn.clicked.connect(self.run)
        c.lay.addWidget(self.inp, 1)
        c.lay.addWidget(self.btn)
        root.addWidget(c)

        self.res = Card(pad=18, spacing=10)
        self.v_title = label("", "h2")
        self.v_text = label("", "muted", wrap=True)
        self.ctx = label("", "small", wrap=True)
        self.steps = label("", wrap=True)
        self.steps.setTextFormat(Qt.TextFormat.RichText)
        self.res.lay.addWidget(self.v_title)
        self.res.lay.addWidget(self.v_text)
        self.res.lay.addWidget(self.steps)
        self.res.lay.addWidget(self.ctx)
        root.addWidget(self.res)
        self.res.hide()

        self.add = Card(pad=18, spacing=10)
        self.add.lay.addWidget(label(tr("Добавить в «Свои сайты»"), "h2"))
        h = QHBoxLayout()
        self.preset = QComboBox()
        self.preset.setMinimumWidth(320)
        h.addWidget(label(tr("Пресет")))
        h.addWidget(self.preset, 1)
        self.with_ip = QCheckBox(tr("Также добавить IP-адреса (ipset)"))
        h.addWidget(self.with_ip)
        self.b_add = button(tr("Добавить и применить"), "plus", "primary")
        self.b_add.clicked.connect(self.add_site)
        h.addWidget(self.b_add)
        self.add.lay.addLayout(h)
        root.addWidget(self.add)
        self.add.hide()

        self.vpnc = Card(pad=18, spacing=10, horizontal=True)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(label(tr("Не помогло? Откройте через VPN"), "h2"))
        self.vpn_txt = label(tr("Сайт всегда будет идти через ваш VPN-сервер, остальные — как раньше, через zapret."),
                             "muted", wrap=True)
        col.addWidget(self.vpn_txt)
        self.vpnc.lay.addLayout(col, 1)
        self.b_vpn = button(tr("Открывать через VPN"), "shield")
        self.b_vpn.clicked.connect(self.via_vpn)
        self.vpnc.lay.addWidget(self.b_vpn)
        root.addWidget(self.vpnc)
        self.vpnc.hide()
        root.addStretch(1)
        core.presets_changed.connect(self.fill_presets)
        self.fill_presets()

    def fill_presets(self):
        cur = self.preset.currentData()
        self.preset.clear()
        a = self.core.active()
        from ..settings import settings
        first = a.id if a else settings.get("last_preset")
        ps = sorted(self.core.presets, key=lambda p: (p.id != first, not self.core.is_fav(p), p.name.lower()))
        for p in ps:
            self.preset.addItem(p.name + ("  ●" if a and a.id == p.id else ""), p.id)
        i = self.preset.findData(cur)
        self.preset.setCurrentIndex(max(0, i))

    def run(self):
        url = self.inp.text().strip()
        if not url:
            return
        self.btn.setEnabled(False)
        self.btn.setText(tr("Проверяю…"))
        a = self.core.active()
        self.ctx_text = (f"{tr('Проверено с активным пресетом')}: {a.name}" if a else tr("Проверено без обхода (пресет не запущен)"))
        run_async(sitecheck.check, url, done=self.show_result,
                  fail=lambda e: (self.btn.setEnabled(True), self.btn.setText(tr("Проверить")), self.core.toast.emit(e, "error")))

    def show_result(self, r):
        self.btn.setEnabled(True)
        self.btn.setText(tr("Проверить"))
        self.last = r
        color, title, text = VERDICT.get(r["verdict"], VERDICT["bad"])
        host = S.display(r["host"]) if r["host"] else ""
        self.v_title.setText(f"<span style='color:{color}'>●</span> {tr(title)}" + (f" — {host}" if host else ""))
        self.v_text.setText(tr(text))
        rows = []
        for name, ok, detail in r["steps"]:
            c = "#22C55E" if ok else "#EF4444"
            rows.append(f"<tr><td style='color:{c}; padding-right:8px'>{'✓' if ok else '×'}</td>"
                        f"<td style='padding-right:16px'><b>{name}</b></td><td>{detail}</td></tr>")
        self.steps.setText(f"<table cellspacing='4'>{''.join(rows)}</table>")
        self.ctx.setText(self.ctx_text)
        self.res.show()
        can_add = bool(r["host"]) and r["verdict"] not in ("down", "bad")
        self.add.setVisible(can_add)
        self.vpnc.setVisible(bool(r["host"]) and r["verdict"] in ("dns", "ip", "dpi", "http"))
        self.b_vpn.setEnabled(True)
        self.b_vpn.setText(tr("Открывать через VPN"))
        self.with_ip.setChecked(r["verdict"] == "ip")
        self.fill_presets()

    def via_vpn(self):
        r = self.last
        if not r or not r.get("host"):
            return
        v = self.core.vpn
        from ..vpn.manager import base_domain
        host = base_domain(r["host"]) if not S.is_ip(r["host"]) else r["host"]
        v.add_domain(host)
        self.b_vpn.setEnabled(False)
        self.b_vpn.setText(tr("Добавлено"))
        if not v.installed() or not v.store.server():
            self.core.toast.emit(tr("Сайт добавлен в список VPN. Осталось добавить сервер на вкладке VPN"), "info")
            self.core.navigate.emit("vpn")
        elif v.state != "on":
            self.core.toast.emit(f"{S.display(host)} → VPN. " + tr("Включаю VPN…"), "info")
            v.start()
        else:
            self.core.toast.emit(f"{S.display(host)} → VPN", "ok")

    def add_site(self):
        r = self.last
        p = self.core.by_id(self.preset.currentData())
        if not r or not p:
            return
        e = self.core.sites.get(p.id)
        host = r["host"]
        if host not in e["domains"]:
            e["domains"].append(host)
        if self.with_ip.isChecked():
            e["with_ip"] = True
            if r.get("ips") and not S.is_ip(host):
                e["ips"][host] = r["ips"]
        self.core.sites.put(p.id, e)
        self.core.presets_changed.emit()
        self.core.toast.emit(f"{S.display(host)} → {p.name}", "ok")
        self.core.activate(p, quiet=True)   # запуск/перезапуск пресета с новым сайтом
