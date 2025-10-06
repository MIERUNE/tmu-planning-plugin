import os

from qgis.gui import QgsColorButton
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QPushButton,
    QToolButton,
)

from .apikey_dialog import ApikeyDialog

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
        self.checkBox_coast_line: QCheckBox = self.checkBox_coast_line
        self.checkBox_port_area: QCheckBox = self.checkBox_port_area
        self.checkBox_fishing_port_area: QCheckBox = self.checkBox_fishing_port_area
        self.checkBox_urban_area: QCheckBox = self.checkBox_urban_area
        self.checkBox_use_district: QCheckBox = self.checkBox_use_district
        self.checkBox_district_planning: QCheckBox = self.checkBox_district_planning
        self.checkBox_location_normalization_plan: QCheckBox = (
            self.checkBox_location_normalization_plan
        )
        self.checkBox_population_mesh: QCheckBox = self.checkBox_population_mesh

        self.apikey_keep: QPushButton = self.findChild(QPushButton, "apikey_keep")

        if self.apikey_keep:
            self.apikey_keep.clicked.connect(self.open_apikey_dialog)
        else:
            print(
                "Warning: 'apikey_keep' QPushButton not found or is not a QPushButton."
            )

    def open_apikey_dialog(self):
        """鍵の絵文字を押したらダイアログを開く"""
        dialog = ApikeyDialog(self)
        dialog.exec_()

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

    def set_prefecture_combobox(self, prefectures: list):
        """都道府県のコンボボックスを設定
        Args:
            prefectures (list): 都道府県リスト [(code, name), ...]
        """
        self.comboBox_prefecture.clear()

        # 初期項目を追加
        self.comboBox_prefecture.addItem("都道府県を選択してください", "")

        # 都道府県リストを追加
        for code, name in prefectures:
            self.comboBox_prefecture.addItem(name, code)

    def set_municipality_combobox(self, municipalities: list):
        """市区町村のコンボボックスを設定
        Args:
            municipalities (list): 市区町村リスト [(code, name), ...]
        """
        self.comboBox_municipality.clear()

        # 初期項目を追加
        if municipalities:
            self.comboBox_municipality.addItem("市区町村を選択してください", "")
            # 市区町村リストを追加
            for code, name in municipalities:
                self.comboBox_municipality.addItem(name, code)

        # 未選択状態に設定
        self.comboBox_municipality.setCurrentIndex(0)
