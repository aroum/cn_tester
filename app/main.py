import ctypes
import os
import sys
import traceback

from PySide6.QtWidgets import QApplication

# Be resilient to different run contexts (package vs script)
try:
    from app.ui import MainWindow
except Exception:
    try:
        from ui import MainWindow  # fallback when running from within the 'app' folder
    except Exception:
        # Show an error box to make failures visible when launching the EXE
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                "Failed to import UI modules.\n" + traceback.format_exc(),
                "C!N Tester GUI",
                0x10,
            )
        except Exception:
            pass
        raise


def main():
    try:
        app = QApplication(sys.argv)
        w = MainWindow()
        w.show()

        sys.exit(app.exec())
        # app.setQuitOnLastWindowClosed(False)
        # tray = QSystemTrayIcon()
        # if getattr(sys, '_MEIPASS', False):
        #     icon_path = os.path.join(sys._MEIPASS, 'icon', 'icon.png')
        # else:
        #     icon_path = os.path.join(os.path.dirname(__file__), 'icon', 'icon.png')
        # tray.setIcon(QIcon(icon_path))
        # tray.setVisible(True)
        #
        # menu = QMenu()
        # action = QAction("A menu item")
        # menu.addAction(action)
        #
        # # Add a Quit option to the menu.
        # quit = QAction("Quit")
        # quit.triggered.connect(app.quit)
        # menu.addAction(quit)
        #
        # # Add the menu to the tray
        # tray.setContextMenu(menu)
    except Exception:
        # Log unexpected startup errors next to the executable and show a message box
        log_path = os.path.join(os.path.dirname(sys.argv[0]), "app_error.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(traceback.format_exc())
        except Exception:
            pass
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                "An unhandled error occurred while starting.\nLog: " + log_path + "\n\n" + traceback.format_exc(),
                "C!N Tester GUI",
                0x10,
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()