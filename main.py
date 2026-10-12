"""ZapretCloud — обход блокировок на основе zapret (winws / winws2)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import winutil  # noqa: E402
from app.migrate import auto_migrate  # noqa: E402

auto_migrate()  # перенос данных из Zapret Studio — до загрузки настроек

from app.settings import settings  # noqa: E402


def cli() -> int | None:
    """Служебные команды (используются установщиком)."""
    if "--set-autostart" in sys.argv:
        ok, _ = winutil.set_autostart(True)
        if ok:
            settings.set("autostart", True)
        return 0 if ok else 1
    if "--remove-autostart" in sys.argv:
        winutil.set_autostart(False)
        settings.set("autostart", False)
        return 0
    if "--vpn-cleanup" in sys.argv:
        # удаление программы: остановить VPN, вернуть системный прокси, убрать правило брандмауэра
        from app.vpn import manager as vm
        try:
            import psutil
            for p in psutil.process_iter(["name"]):
                if (p.info["name"] or "").lower() == "sing-box.exe":
                    p.kill()
        except Exception:
            pass
        vm.restore_system_proxy()
        winutil.run(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={vm.FW_RULE}"], timeout=15)
        return 0
    return None


def main():
    r = cli()
    if r is not None:
        return r
    autostart = "--autostart" in sys.argv
    if winutil.IS_WIN and not winutil.is_admin() and "--no-admin" not in sys.argv:
        if winutil.relaunch_as_admin():
            return 0
        # пользователь отказался от UAC — продолжаем с ограничениями

    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

    from app.i18n import set_lang, tr
    from app.paths import find_root, looks_like_root, APP_NAME

    set_lang(settings.get("language"))
    if winutil.IS_WIN:
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ZapretCloud.App")
        except Exception:
            pass
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Segoe UI", 10))
    from app.widgets import WheelGuard
    app._wheel_guard = WheelGuard(app)
    app.installEventFilter(app._wheel_guard)
    from app.icons import app_icon
    app.setWindowIcon(app_icon())

    # один экземпляр программы
    key = "ZapretCloud-single-instance"
    tries = 40 if "--restart" in sys.argv else 1   # при перезапуске ждём закрытия старой копии
    for i in range(tries):
        sock = QLocalSocket()
        sock.connectToServer(key)
        if not sock.waitForConnected(300):
            break
        if i == tries - 1:
            sock.write(b"show")
            sock.waitForBytesWritten(300)
            return 0
        sock.abort()
        import time
        time.sleep(0.25)
    QLocalServer.removeServer(key)
    server = QLocalServer()
    server.listen(key)

    root = find_root(settings.get("root"))
    if root is None:
        from app.theme import Theme
        app.setStyleSheet(Theme(settings.get("theme")).qss())
        m = QMessageBox()
        m.setWindowTitle(APP_NAME)
        m.setText(tr("Не найдены файлы движка (папка engine)"))
        m.setInformativeText(tr("Переустановите программу или укажите папку с exe\\winws.exe вручную."))
        pick = m.addButton(tr("Указать папку…"), QMessageBox.ButtonRole.AcceptRole)
        m.addButton(tr("Выход"), QMessageBox.ButtonRole.RejectRole)
        m.exec()
        if m.clickedButton() is not pick:
            return 0
        d = QFileDialog.getExistingDirectory(None, tr("Выберите папку Zapret"))
        if not d or not looks_like_root(Path(d)):
            QMessageBox.warning(None, APP_NAME, tr("В папке нет exe\\winws.exe или exe\\winws2.exe"))
            return 0
        root = Path(d)
        settings.set("root", str(root))

    from app.core import Core
    from app.window import MainWindow

    core = Core(root)
    wiz = None
    if not settings.get("wizard_done") and not autostart:
        from app.theme import Theme
        from app.widgets import THEME
        from app.wizard import Wizard
        THEME["t"] = Theme(settings.get("theme"), settings.get("accent"), settings.get("opacity"))
        app.setStyleSheet(THEME["t"].qss())
        wiz = Wizard(core)
        wiz.exec()
    win = MainWindow(core, autostart)

    def on_conn():
        c = server.nextPendingConnection()
        if c:
            c.readyRead.connect(win.show_normal)
    server.newConnection.connect(on_conn)

    if autostart and settings.get("tray") and win.tray:
        pass  # стартуем свёрнутыми в трей
    else:
        win.show()

    if wiz is not None:
        win.after_wizard(wiz)
        if wiz.run_autotune:
            return app.exec()

    core.vpn_startup()
    if settings.get("start_last") and core.runner and not core.runner.alive():
        last = core.by_id(settings.get("last_preset"))
        if last:
            from app.runner import find_winws
            if not find_winws():
                core.activate(last, quiet=not win.isVisible())

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
