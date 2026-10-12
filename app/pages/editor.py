import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat, QFont
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPlainTextEdit, QListWidget,
                             QListWidgetItem, QDialog, QFormLayout, QDialogButtonBox, QMessageBox, QRadioButton)

from .. import presets as P
from ..i18n import tr
from ..widgets import Card, label, button, page_header, T
from ..winutil import open_path

TEMPLATE = {
    "winws2": "--lua-init=@lua/zapret-lib.lua\n--lua-init=@lua/zapret-antidpi.lua\n--lua-init=@lua/zapret-auto.lua\n\n"
              "--wf-tcp-out=80,443\n--wf-udp-out=443\n\n--name=YouTube\n--filter-tcp=443\n--hostlist=lists/youtube.txt\n"
              "--lua-desync=multisplit:pos=1,midsld\n",
    "winws1": "--wf-tcp=80,443\n--wf-udp=443\n\n--comment=YouTube\n--filter-tcp=443\n--hostlist=lists/youtube.txt\n"
              "--dpi-desync=multisplit\n--dpi-desync-split-pos=1,midsld\n",
}


class Highlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self.rehash()

    def rehash(self):
        t = T()
        self.f_comment = QTextCharFormat()
        self.f_comment.setForeground(QColor(t.muted_hex))
        self.f_comment.setFontItalic(True)
        self.f_key = QTextCharFormat()
        self.f_key.setForeground(QColor(t.accent_hover if t.dark else t.accent))
        self.f_new = QTextCharFormat()
        self.f_new.setForeground(QColor("#F59E0B"))
        self.f_new.setFontWeight(QFont.Weight.Bold)
        self.f_path = QTextCharFormat()
        self.f_path.setForeground(QColor("#34D399" if t.dark else "#047857"))
        self.rehighlight()

    def highlightBlock(self, text):
        s = text.strip()
        if s.startswith("#"):
            self.setFormat(0, len(text), self.f_comment)
            return
        if s == "--new":
            self.setFormat(0, len(text), self.f_new)
            return
        m = re.match(r"\s*(--[\w-]+)", text)
        if m:
            self.setFormat(m.start(1), len(m.group(1)), self.f_key)
        for pm in re.finditer(r"@?(lists|bin|lua)/[\w.\-]+", text):
            self.setFormat(pm.start(), pm.end() - pm.start(), self.f_path)


class NewDialog(QDialog):
    def __init__(self, parent, base_name=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Новый профиль"))
        self.setMinimumWidth(420)
        f = QFormLayout(self)
        f.setSpacing(10)
        self.name = QLineEdit()
        self.engine = QComboBox()
        self.engine.addItem("Zapret 2 (winws2)", "winws2")
        self.engine.addItem("Zapret 1 (winws)", "winws1")
        self.r_empty = QRadioButton(tr("Пустой"))
        self.r_copy = QRadioButton(tr("Копия выбранного на главной") + (f": {base_name}" if base_name else ""))
        self.r_copy.setEnabled(base_name is not None)
        (self.r_copy if base_name else self.r_empty).setChecked(True)
        f.addRow(tr("Название"), self.name)
        f.addRow(tr("Движок"), self.engine)
        f.addRow(tr("Основа"), self.r_empty)
        f.addRow("", self.r_copy)
        bb = QDialogButtonBox()
        bb.addButton(tr("Создать"), QDialogButtonBox.ButtonRole.AcceptRole)
        bb.addButton(tr("Отмена"), QDialogButtonBox.ButtonRole.RejectRole)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)


class EditorPage(QWidget):
    def __init__(self, core, get_home_selected):
        super().__init__()
        self.core = core
        self.get_home_selected = get_home_selected
        self.cur = None          # Preset (пользовательский) или None
        self.engine = "winws2"
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 24)
        root.setSpacing(14)
        hdr = QHBoxLayout()
        hdr.addWidget(page_header(tr("Профили"), tr("Встроенные пресеты нельзя изменять — создайте копию.")), 1)
        b_new = button(tr("Новый профиль"), "plus", "primary")
        b_new.clicked.connect(self.new_profile)
        hdr.addWidget(b_new, 0, Qt.AlignmentFlag.AlignBottom)
        root.addLayout(hdr)

        body = QHBoxLayout()
        body.setSpacing(14)
        # список своих профилей
        left = Card(pad=10)
        left.setFixedWidth(200)
        left.lay.addWidget(label(tr("Мои профили"), "small"))
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self.on_pick)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setTextElideMode(Qt.TextElideMode.ElideRight)
        left.lay.addWidget(self.list, 1)
        self.empty = label(tr("Нет своих профилей. Нажмите «Новый профиль»."), "muted", wrap=True)
        left.lay.addWidget(self.empty)
        body.addWidget(left)

        # редактор
        mid = Card(pad=14)
        form = QHBoxLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText(tr("Название"))
        self.desc = QLineEdit()
        self.desc.setPlaceholderText(tr("Описание"))
        self.eng_lbl = label("", "badge")
        form.addWidget(self.name, 1)
        form.addWidget(self.desc, 1)
        form.addWidget(self.eng_lbl)
        mid.lay.addLayout(form)
        self.text = QPlainTextEdit()
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.text.setTabStopDistance(24)
        self.hl = Highlighter(self.text.document())
        mid.lay.addWidget(self.text, 1)
        brow = QHBoxLayout()
        self.b_del = button("", "trash", "danger", tip=tr("Удалить"))
        self.b_open = button("", "file", tip=tr("Открыть файл"))
        self.b_save = button(tr("Сохранить"), "save")
        self.b_run = button(tr("Активировать"), "play", "primary", tip=tr("Сохранить и активировать"))
        self.b_del.clicked.connect(self.delete)
        self.b_open.clicked.connect(lambda: self.cur and open_path(self.cur.path))
        self.b_save.clicked.connect(lambda: self.save(False))
        self.b_run.clicked.connect(lambda: self.save(True))
        for b in (self.b_save, self.b_run):
            b.setMinimumWidth(b.sizeHint().width() + 24)
        brow.addWidget(self.b_del)
        brow.addWidget(self.b_open)
        brow.addStretch(1)
        brow.addWidget(self.b_save)
        brow.addWidget(self.b_run)
        mid.lay.addLayout(brow)
        body.addWidget(mid, 1)

        # конструктор
        tools = Card(pad=14)
        tools.setFixedWidth(250)
        tools.lay.addWidget(label(tr("Вставить стратегию"), "h2"))
        self.cat = QComboBox()
        self.strat = QComboBox()
        self.strat.setMaxVisibleItems(18)
        self.cat.currentIndexChanged.connect(self.fill_strats)
        self.strat_preview = QPlainTextEdit()
        self.strat_preview.setReadOnly(True)
        self.strat_preview.setFixedHeight(110)
        self.strat.currentIndexChanged.connect(lambda: self.strat_preview.setPlainText(self.strat.currentData() or ""))
        b_ins = button(tr("Вставить"), "plus")
        b_ins.clicked.connect(lambda: self.insert(self.strat.currentData()))
        tools.lay.addWidget(label(tr("Категория"), "small"))
        tools.lay.addWidget(self.cat)
        tools.lay.addWidget(self.strat)
        tools.lay.addWidget(self.strat_preview)
        tools.lay.addWidget(b_ins)
        tools.lay.addSpacing(10)
        tools.lay.addWidget(label(tr("Вставить список"), "h2"))
        self.lists = QComboBox()
        self.lists.setMaxVisibleItems(18)
        tools.lay.addWidget(self.lists)
        lr = QHBoxLayout()
        b_h = button(tr("как hostlist"))
        b_i = button(tr("как ipset"))
        b_h.clicked.connect(lambda: self.insert(f"--hostlist=lists/{self.lists.currentText()}"))
        b_i.clicked.connect(lambda: self.insert(f"--ipset=lists/{self.lists.currentText()}"))
        lr.addWidget(b_h)
        lr.addWidget(b_i)
        tools.lay.addLayout(lr)
        tools.lay.addSpacing(10)
        b_newblk = button(tr("Новый блок (--new)"), "layers")
        b_newblk.clicked.connect(lambda: self.insert("\n--new\n"))
        tools.lay.addWidget(b_newblk)
        tools.lay.addStretch(1)
        body.addWidget(tools)
        root.addLayout(body, 1)

        core.presets_changed.connect(self.reload)
        core.theme_changed.connect(self.hl.rehash)
        core.edit_preset.connect(self.copy_from)
        self.catalogs = {}
        self.reload()
        self.set_engine("winws2")
        self.set_enabled(False)

    # ---------------------------------------------------------------
    def set_enabled(self, on):
        for w in (self.name, self.desc, self.text, self.b_del, self.b_open, self.b_save, self.b_run):
            w.setEnabled(on)

    def set_engine(self, eng):
        self.engine = eng
        self.eng_lbl.setText(P.ENGINE_LABEL[eng])
        if eng not in self.catalogs and self.core.root:
            self.catalogs[eng] = P.load_catalog(self.core.root, eng)
        self.cat.blockSignals(True)
        self.cat.clear()
        for k in self.catalogs.get(eng, {}):
            self.cat.addItem(k, k)
        self.cat.blockSignals(False)
        self.fill_strats()
        self.lists.clear()
        if self.core.root:
            self.lists.addItems(P.list_files(self.core.root))

    def fill_strats(self):
        self.strat.clear()
        for name, body in self.catalogs.get(self.engine, {}).get(self.cat.currentData(), []):
            self.strat.addItem(name, body)

    def reload(self):
        cur_path = self.cur.path if self.cur else None
        self.list.blockSignals(True)
        self.list.clear()
        sel = None
        for p in self.core.presets:
            if p.builtin:
                continue
            it = QListWidgetItem(p.name)
            it.setToolTip(f"{P.ENGINE_LABEL[p.engine]} · {p.path.name}")
            it.setData(Qt.ItemDataRole.UserRole, p)
            self.list.addItem(it)
            if cur_path and p.path == cur_path:
                sel = it
        self.list.blockSignals(False)
        self.empty.setVisible(self.list.count() == 0)
        if sel:
            self.list.setCurrentItem(sel)

    def on_pick(self, it, _prev=None):
        if not it:
            return
        p = it.data(Qt.ItemDataRole.UserRole)
        self.cur = p
        self.set_engine(p.engine)
        self.name.setText(p.name)
        self.desc.setText(p.description)
        self.text.setPlainText(P.strip_header(p.read()))
        self.set_enabled(True)

    def insert(self, s):
        if not s or not self.text.isEnabled():
            return
        c = self.text.textCursor()
        if c.positionInBlock() > 0:
            c.movePosition(c.MoveOperation.EndOfBlock)
            c.insertText("\n")
        c.insertText(s.rstrip("\n") + "\n")
        self.text.setTextCursor(c)
        self.text.setFocus()

    def new_profile(self, base=None):
        base = base or self.get_home_selected()
        d = NewDialog(self, base.name if base else None)
        if base:
            d.engine.setCurrentIndex(d.engine.findData(base.engine))
            d.name.setText(base.name + " (" + tr("копия") + ")")
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        name = d.name.text().strip()
        if not name:
            self.core.toast.emit(tr("Введите название"), "error")
            return
        eng = d.engine.currentData()
        if d.r_copy.isChecked() and base:
            body = P.strip_header(base.read())
            desc = base.description
            eng = base.engine
        else:
            body, desc = TEMPLATE[eng], ""
        path = P.save_user_preset(self.core.user_dir, eng, name, body, desc)
        self.cur = P.Preset(name, eng, path, False, desc)
        self.core.reload_presets()

    def copy_from(self, preset):
        self.core.navigate.emit("editor")
        self.new_profile(preset)

    def save(self, run=False):
        if not self.cur:
            return
        name = self.name.text().strip()
        if not name:
            self.core.toast.emit(tr("Введите название"), "error")
            return
        path = P.save_user_preset(self.core.user_dir, self.cur.engine, name, self.text.toPlainText(),
                                  self.desc.text().strip(), self.cur.color, old_path=self.cur.path)
        old_id = self.cur.id
        self.cur = P.Preset(name, self.cur.engine, path, False, self.desc.text().strip())
        self.core.sites.rename(old_id, self.cur.id)
        self.core.reload_presets()
        self.core.toast.emit(tr("Сохранено"), "ok")
        if run:
            p = next((x for x in self.core.presets if x.path == path), None)
            if p:
                self.core.activate(p)

    def delete(self):
        if not self.cur:
            return
        r = QMessageBox.question(self, tr("Удалить"), f"{tr('Удалить пресет?')}\n{self.cur.name}")
        if r != QMessageBox.StandardButton.Yes:
            return
        try:
            self.cur.path.unlink()
        except OSError as e:
            self.core.toast.emit(str(e), "error")
        self.cur = None
        self.name.clear()
        self.desc.clear()
        self.text.clear()
        self.set_enabled(False)
        self.core.reload_presets()
        self.core.toast.emit(tr("Пресет удалён"), "ok")
