import os
from typing import Optional

from qgis.gui import QgsColorButton
from qgis.PyQt import uic
from qgis.PyQt.QtGui import QColor, QPixmap
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
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
        self.checkBox_class3: QCheckBox = self.checkBox_class3
        self.checkBox_class5: QCheckBox = self.checkBox_class5
        self.toolButton_basemap_info: QToolButton = self.toolButton_basemap_info
        self.checkBox_water: QCheckBox = self.checkBox_water
        self.checkBox_highway: QCheckBox = self.checkBox_highway
        self.checkBox_major_road: QCheckBox = self.checkBox_major_road
        self.checkBox_building: QCheckBox = self.checkBox_building
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
        self.checkBox_nature_reserve: QCheckBox = self.checkBox_nature_reserve
        self.checkBox_did: QCheckBox = self.checkBox_did
        self.checkBox_high_level_use_districts: QCheckBox = (
            self.checkBox_high_level_use_districts
        )
        self.checkBox_population_mesh: QCheckBox = self.checkBox_population_mesh
        self.radioButton_population_mesh_3rd: QRadioButton = (
            self.radioButton_population_mesh_3rd
        )
        self.radioButton_population_mesh_4th: QRadioButton = (
            self.radioButton_population_mesh_4th
        )
        self.checkBox_hazard: QCheckBox = self.checkBox_hazard

        self._set_population_mesh_controls()

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

    def create_legends(self, class3: dict, class5: dict):
        """全凡例を生成"""
        self._create_legend(
            layout=self.horizontalLayout_class3_legend,
            styles=class3,
            labels={"1": "1：都市型", "2": "2：農地緑地型", "3": "3：森林型"},
        )
        self._create_legend(
            layout=self.verticalLayout_class5_legend_container,
            styles=class5,
            labels={
                "1": "1：森林型",
                "2": "2：都市型",
                "3": "3：農地緑地型",
                "4": "4：森林型やや都市より",
                "5": "5：農地緑地型やや都市より",
            },
            items_per_row=3,
        )

    def _create_legend(
        self,
        layout,
        styles: dict,
        labels: dict,
        items_per_row: Optional[int] = None,
    ):
        """凡例を動的に生成"""
        # 既存の凡例アイテムをクリア
        while layout.count():
            item = layout.takeAt(0)
            if item.layout():
                row = item.layout()
                while row.count():
                    child = row.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                row.setParent(None)
                row.deleteLater()
            elif item.widget():
                item.widget().deleteLater()

        if items_per_row:
            row_layout = QHBoxLayout()
            layout.addLayout(row_layout)
        else:
            row_layout = layout

        # stylesの内容に基づいて凡例アイテムを生成
        for i, (value, style) in enumerate(styles.items()):
            if items_per_row and i > 0 and i % items_per_row == 0:
                row_layout.addStretch()
                row_layout = QHBoxLayout()
                layout.addLayout(row_layout)

            color_label = QLabel()
            pixmap = QPixmap(16, 16)
            rgba = style["color"].split(",")
            pixmap.fill(QColor(int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3])))
            color_label.setPixmap(pixmap)
            text_label = QLabel(labels.get(value, value))

            row_layout.addWidget(color_label)
            row_layout.addWidget(text_label)

        row_layout.addStretch()

    def _set_population_mesh_controls(self):
        """人口メッシュ関連のコントロールを初期化"""
        # 初期状態: チェックボックスが未チェックなのでラジオボタンを無効化
        self._toggle_mesh_radio_buttons(self.checkBox_population_mesh.isChecked())

        # チェックボックスの状態変化をラジオボタンに連動
        self.checkBox_population_mesh.toggled.connect(self._toggle_mesh_radio_buttons)

    def _toggle_mesh_radio_buttons(self, checked):
        """
        人口メッシュチェックボックスの状態に応じてラジオボタンをグレーアウト制御

        Args:
            checked (bool): チェックボックスがチェックされているか
        """
        self.radioButton_population_mesh_3rd.setEnabled(checked)
        self.radioButton_population_mesh_4th.setEnabled(checked)

        # チェックを入れた時、何も選択されていなければデフォルトで3次メッシュを選択
        if checked:
            if (
                not self.radioButton_population_mesh_3rd.isChecked()
                and not self.radioButton_population_mesh_4th.isChecked()
            ):
                self.radioButton_population_mesh_3rd.setChecked(True)
