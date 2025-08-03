import os

from qgis.gui import QgsColorButton
from qgis.PyQt import uic

# from qgis.PyQt.QtWidgets import QDockWidget, QComboBox, QMessageBox, QPushButton
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
        self.checkBox_water: QCheckBox = self.checkBox_water
        self.checkBox_highway: QCheckBox = self.checkBox_highway
        self.checkBox_major_road: QCheckBox = self.checkBox_major_road
        self.checkBox_building: QCheckBox = self.checkBox_building
        self.colorButton_land: QgsColorButton = self.colorButton_land
        self.colorButton_water: QgsColorButton = self.colorButton_water
        self.colorButton_highway: QgsColorButton = self.colorButton_highway
        self.colorButton_major_road: QgsColorButton = self.colorButton_major_road
        self.colorButton_building: QgsColorButton = self.colorButton_building


    def get_selected_basemaps(self) -> dict:
        """地理院ベクトルタイルの選択された地物と色を取得"""
        selected_features = {}

        # 国土
        if self.checkBox_land.isChecked():
            selected_features["land"] = self.colorButton_land.color()

        # 水域
        if self.checkBox_water.isChecked():
            selected_features["water"] = self.colorButton_water.color()

        # 高速道路
        if self.checkBox_highway.isChecked():
            selected_features["highway"] = self.colorButton_highway.color()

        # 主要道路
        if self.checkBox_major_road.isChecked():
            selected_features["major_road"] = self.colorButton_major_road.color()

        # 建物ポリゴン
        if self.checkBox_building.isChecked():
            selected_features["building"] = self.colorButton_building.color()

        return selected_features