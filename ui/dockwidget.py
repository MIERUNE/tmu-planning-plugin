import os

from qgis.PyQt import uic
# from qgis.PyQt.QtWidgets import QDockWidget, QComboBox, QMessageBox, QPushButton
from qgis.PyQt.QtWidgets import QDockWidget, QPushButton, QComboBox, QCheckBox, QToolButton

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