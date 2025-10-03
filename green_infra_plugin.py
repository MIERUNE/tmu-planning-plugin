import os

from qgis.core import Qgis, QgsMessageLog
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .real_estate_lib.land_use.location_normalization_plan_algorithm import (
    LocationNormalizationPlanAlgorithm,
)
from .real_estate_lib.land_use.urban_planning_algorithm import UrbanPlanningAlgorithm
from .real_estate_lib.land_use.zoning_district_algorithm import ZoningDistrictAlgorithm
from .real_estate_lib.land_use.nature_reserve_algorithm import NatureReserveAlgorithm
from .ui.apikey_dialog import ApikeyDialog
from .ui.dockwidget import GreenInfraPlanningDockwidget
from .workflows.area_workflow import AreaWorkflow
from .workflows.basemap_workflow import BasemapWorkflow
from .workflows.coastline_workflow import CoastlineWorkflow
from .workflows.land_use_layer_workflow import LayerWorkflow

PLUGIN_NAME = "Green Infra Plugin"


class GreenInfraPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.win = self.iface.mainWindow()
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = PLUGIN_NAME
        self.toolbar = self.iface.addToolBar(PLUGIN_NAME)
        self.toolbar.setObjectName(PLUGIN_NAME)
        self.dockwidget = None
        self.area_workflow = AreaWorkflow(iface)
        self.basemap_workflow = BasemapWorkflow(iface)
        self.layer_workflow = LayerWorkflow(iface)
        self.urban_planning_algorithm = UrbanPlanningAlgorithm(iface)
        self.zoning_district_algorithm = ZoningDistrictAlgorithm(iface)
        self.location_normalization_plan_algorithm = LocationNormalizationPlanAlgorithm(
            iface
        )
        self.nature_reserve_algorithm = NatureReserveAlgorithm(iface)
        self.coastline_workflow = CoastlineWorkflow(iface)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.toolbar.addAction(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        # メニュー設定
        self.add_action(
            icon_path=os.path.join(self.plugin_dir, "imgs", "icon.svg"),
            text="土地利用計画支援",
            callback=self.show_dock_widget,
            parent=self.win,
        )

    def unload(self):
        # DockWidgetが存在する場合は削除
        if self.dockwidget:
            self.iface.removeDockWidget(self.dockwidget)
            self.dockwidget = None

        for action in self.actions:
            self.iface.removePluginMenu(PLUGIN_NAME, action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def show_dock_widget(self):
        # DockWidgetが作成されていない場合のみ作成
        if self.dockwidget is None:
            self.dockwidget = GreenInfraPlanningDockwidget()
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)

            # 都道府県リストを読み込み
            self.area_workflow.load_prefecture_dropdown(self.dockwidget)

            # 都道府県選択変更イベントを接続
            self.dockwidget.comboBox_prefecture.currentIndexChanged.connect(
                self.on_prefecture_changed
            )

            # 実行ボタンにイベントを接続
            self.dockwidget.pushButton_execute.clicked.connect(
                self.execute_data_visualization
            )

        self.dockwidget.show()

    def execute_data_visualization(self):
        """データ取得・可視化実行処理"""
        if not self.dockwidget:
            return

        real_estate_api_key = ApikeyDialog.get_real_estate_api_key()

        # Phase 1: ベースマップレイヤーの可視化
        self.basemap_workflow.execute(self.dockwidget.get_selected_basemaps())

        if real_estate_api_key:
            # 都市計画区域の可視化
            if self.dockwidget.checkBox_urban_area.isChecked():
                self.layer_workflow.execute(
                    self.urban_planning_algorithm,
                    api_key=real_estate_api_key,
                )

            # 用途地域の可視化
            if self.dockwidget.checkBox_use_district.isChecked():
                self.layer_workflow.execute(
                    self.zoning_district_algorithm, 
                    api_key=real_estate_api_key
                )

            # 立地適正化計画の可視化
            if self.dockwidget.checkBox_location_normalization_plan.isChecked():
                self.layer_workflow.execute(
                    self.location_normalization_plan_algorithm,
                    api_key=real_estate_api_key,
                )

            # 自然公園地域の可視化
            if self.dockwidget.checkBox_nature_reserve.isChecked():
                self.layer_workflow.execute(
                    self.nature_reserve_algorithm,
                    api_key=real_estate_api_key,
                    prefecture_code=self.dockwidget.comboBox_prefecture.currentData(),

                )
        else:
            message = (
                "不動産情報ライブラリAPIキーが未設定のため、関連処理をスキップします。"
            )
            QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
            self.iface.messageBar().pushMessage(
                "不動産APIキー未設定",
                message,
                level=Qgis.Warning,
            )

        # Phase 3: 海岸線データの可視化
        umi_shiru_api_key = ApikeyDialog.get_umi_shiru_api_key()

        # 海岸線データの可視化
        if self.dockwidget.checkBox_coast_line.isChecked():
            self.coastline_workflow.execute(
                api_key=umi_shiru_api_key,
                municipality_code=self.dockwidget.comboBox_municipality.currentData(),
                municipality_name=self.dockwidget.comboBox_municipality.currentText(),
            )
        # 漁港区域の可視化
        # 港湾区域の可視化

    def on_prefecture_changed(self):
        """都道府県選択変更時の処理"""
        if not self.dockwidget:
            return

        api_key = ApikeyDialog.get_real_estate_api_key()
        selected_code = self.dockwidget.comboBox_prefecture.currentData()

        self.area_workflow.load_municipality_dropdown(
            self.dockwidget, api_key, selected_code
        )
