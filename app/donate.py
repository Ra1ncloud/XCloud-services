"""Окно «Поддержать проект»: перевод на кошелёк ЮMoney."""
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel

from .i18n import tr
from .widgets import label, button

YOOMONEY_WALLET = "4100119654214309"
YOOMONEY_URL = f"https://yoomoney.ru/to/{YOOMONEY_WALLET}"
EVM_WALLET = "0x15f18447f7D528c73795d2fd91A3dE6956FF0182"   # MetaMask


class DonateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Поддержать проект"))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(10)
        lay.addWidget(label(tr("Поддержать проект"), "h2"))
        lay.addWidget(label(tr("ZapretCloud бесплатный. Если программа вам помогает — можно поддержать разработку "
                               "любой суммой. Спасибо! ♥"), "muted", wrap=True))
        try:
            from .pages.vpn_page import qr_pixmap
            pm = qr_pixmap(YOOMONEY_URL, 220)
        except Exception:
            pm = None
        if pm:
            q = QLabel()
            q.setPixmap(pm)
            q.setAlignment(Qt.AlignmentFlag.AlignCenter)
            q.setStyleSheet("background:white; border-radius:10px; padding:8px;")
            lay.addWidget(q, 0, Qt.AlignmentFlag.AlignHCenter)
            lay.addWidget(label(tr("Отсканируйте камерой телефона или нажмите кнопку ниже"), "small", wrap=True))
        w = QHBoxLayout()
        w.addWidget(label(tr("Кошелёк ЮMoney:") + f"  <b>{YOOMONEY_WALLET}</b>"), 1)
        b_copy = button(tr("Копировать"), "copy")
        b_copy.clicked.connect(lambda: (QGuiApplication.clipboard().setText(YOOMONEY_WALLET),
                                        b_copy.setText(tr("Скопировано"))))
        w.addWidget(b_copy)
        lay.addLayout(w)

        lay.addSpacing(6)
        lay.addWidget(label("<b>" + tr("Криптовалюта (MetaMask)") + "</b>"))
        lay.addWidget(label(tr("USDT, USDC, ETH, BNB и другие токены в сетях Ethereum, BNB Chain, Polygon, Arbitrum, Base. "
                               "Проверьте сеть перед отправкой."), "small", wrap=True))
        cw = QHBoxLayout()
        addr = label(EVM_WALLET, None)
        addr.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        addr.setStyleSheet("font-family: Consolas, monospace;")
        cw.addWidget(addr, 1)
        b_ccopy = button(tr("Копировать"), "copy")
        b_ccopy.clicked.connect(lambda: (QGuiApplication.clipboard().setText(EVM_WALLET),
                                         b_ccopy.setText(tr("Скопировано"))))
        cw.addWidget(b_ccopy)
        b_cqr = button("QR", "layers")
        b_cqr.clicked.connect(self._crypto_qr)
        cw.addWidget(b_cqr)
        lay.addLayout(cw)

        h = QHBoxLayout()
        h.addStretch(1)
        c = button(tr("Закрыть"))
        c.clicked.connect(self.reject)
        h.addWidget(c)
        go = button(tr("Перевести через ЮMoney"), "heart", "primary")
        go.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(YOOMONEY_URL)))
        h.addWidget(go)
        lay.addLayout(h)
        self.setMinimumWidth(480)

    def _crypto_qr(self):
        from .pages.vpn_page import QrDialog
        QrDialog(tr("Криптовалюта (MetaMask)"), EVM_WALLET,
                 tr("Отсканируйте в MetaMask или другом кошельке. Проверьте сеть перед отправкой."),
                 self, copy_text=EVM_WALLET).exec()
