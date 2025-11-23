# desktop/client.py
import os
# Force software OpenGL (helps avoid QPaintDevice crashes)
os.environ.setdefault("QT_OPENGL", "software")

import sys
from PyQt5.QtWidgets import QApplication

from main_window import LoginWidget, MainWindow
from auth import load_cached_token

def main():
    app = QApplication(sys.argv)

    # ALWAYS SHOW LOGIN FIRST (no auto-login)
    def on_login(user):
        login_widget.close()
        mw = MainWindow(user)
        mw.show()

    login_widget = LoginWidget(on_login)
    login_widget.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
