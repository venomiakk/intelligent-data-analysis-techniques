import sys

from PyQt5.QtWidgets import QApplication

from interface import Interface


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Interface()
    sys.exit(app.exec_())