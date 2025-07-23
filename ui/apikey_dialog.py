import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

ui_dialog, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "apikey_keep.ui"))


class ApikeyDialog(QDialog, ui_dialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
