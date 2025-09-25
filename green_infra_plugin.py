import os

from qgis.core import Qgis, QgsMessageLog
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .ui.apikey_dialog import ApikeyDialog
from .ui.dockwidget import GreenInfraPlanningDockwidget
from .workflows.area_workflow import AreaWorkflow
from .workflows.basemap_workflow import BasemapWorkflow
from .workflows.layer_workflow import LayerWorkflow
from .real_estate_lib.urban_planning.urban_planning_algorithm import UrbanPlanningAlgorithm
from .real_estate_lib.urban_planning.zoning_district import ZoningDistrictAlgorithm

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

        api_key = ApikeyDialog.get_real_estate_api_key()

        if not api_key:
            # ログにエラーメッセージを記録
            message = "APIキーが未設定のため、処理を中断します。"
            QgsMessageLog.logMessage(
                message,
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            self.iface.messageBar().pushMessage(
                "API接続エラー",
                "APIキーが設定されていません。",
                level=Qgis.Critical,
            )
            return

        # Phase 1: ベースマップレイヤーの可視化
        self.basemap_workflow.execute(self.dockwidget.get_selected_basemaps())

        # Phase 2:都市計画区域の可視化
        if self.dockwidget.checkBox_urban_area.isChecked():
            # Workflowを実行
            self.layer_workflow.execute(
                self.urban_planning_algorithm,
                api_key=api_key,
            )
        if self.dockwidget.checkBox_use_district.isChecked():
            # Workflowを実行
            self.layer_workflow.execute(
                self.zoning_district_algorithm,
                api_key=api_key,
            )
        # Phase 3:

    def on_prefecture_changed(self):
        """都道府県選択変更時の処理"""
        if not self.dockwidget:
            return

        api_key = ApikeyDialog.get_real_estate_api_key()
        selected_code = self.dockwidget.comboBox_prefecture.currentData()

        self.area_workflow.load_municipality_dropdown(
            self.dockwidget, api_key, selected_code
        )
