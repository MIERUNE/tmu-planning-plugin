import os

from .apikey_dialog import ApikeyDialog
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QPushButton,
    QToolButton,
)

ui_dockwidget, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "green_infra_planning_dockwidget.ui")
)


class GreenInfraPlanningDockwidget(QDockWidget, ui_dockwidget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # 型定義：UIファイルで定義されていてPythonから操作したいインスタンスはここに定義する
        self.pushButton_execute: QPushButton = self.pushButton_execute
        self.comboBox_prefecture: QComboBox = self.comboBox_prefecture
        self.comboBox_municipality: QComboBox = self.comboBox_municipality
        self.toolButton_basemap_info: QToolButton = self.toolButton_basemap_info
        self.checkBox_land: QCheckBox = self.checkBox_land

        self.apikey_keep: QPushButton = self.findChild(QPushButton, "apikey_keep")

        if self.apikey_keep:
            self.apikey_keep.clicked.connect(self.open_apikey_dialog)
        else:
            print("Warning: 'apikey_keep' QPushButton not found or is not a QPushButton.")

    def open_apikey_dialog(self):
        """鍵の絵文字を押したらダイアログを開く"""
        dialog = ApikeyDialog(self)
        dialog.exec_()
