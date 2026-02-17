import os

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsMessageLog,
    QgsProject,
    QgsRectangle,
)
from qgis.gui import QgsMessageBarItem
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .features.administrative_area.administrative_area_workflow import (
    AdministrativeAreaWorkflow,
)
from .features.basemap.basemap_workflow import BasemapWorkflow
from .features.estat.population_mesh_workflow import PopulationMeshWorkflow
from .features.hazard_map_portal.flood_hazard_area_algorithm import (
    FloodHazardAreaAlgorithm,
)
from .features.hazard_map_portal.hazard_map_workflow import HazardMapWorkflow
from .features.real_estate_lib.algorithms.did_algorithm import DidAreaAlgorithm
from .features.real_estate_lib.algorithms.district_plan_algorithm import (
    DistrictPlanAlgorithm,
)
from .features.real_estate_lib.algorithms.high_utilization_zone_algorithm import (
    HighUtilizationZoneAlgorithm,
)
from .features.real_estate_lib.algorithms.location_normalization_plan_algorithm import (
    LocationNormalizationPlanAlgorithm,
)
from .features.real_estate_lib.algorithms.nature_reserve_algorithm import (
    NatureReserveAlgorithm,
)
from .features.real_estate_lib.algorithms.urban_planning_algorithm import (
    UrbanPlanningAlgorithm,
)
from .features.real_estate_lib.algorithms.zoning_district_algorithm import (
    ZoningDistrictAlgorithm,
)
from .features.real_estate_lib.workflows.area_workflow import AreaWorkflow
from .features.real_estate_lib.workflows.land_use_layer_workflow import LayerWorkflow
from .features.umi_shiru.workflows.coastline_workflow import CoastlineWorkflow
from .features.umi_shiru.workflows.fishing_port_workflow import FishingPortWorkflow
from .features.umi_shiru.workflows.port_area_workflow import PortAreaWorkflow
from .ui.apikey_dialog import ApikeyDialog
from .ui.dockwidget import GreenInfraPlanningDockwidget
from .utils.estat.client import AdministrativeAreaClient
from .utils.settings import CITY_DEFAULT_BOUNDS

PLUGIN_NAME = "GreenInfraPlannerJP"


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
        self.administrative_area_workflow = AdministrativeAreaWorkflow(iface)
        self.basemap_workflow = BasemapWorkflow(iface)
        self.layer_workflow = LayerWorkflow(iface)
        self.urban_planning_algorithm = UrbanPlanningAlgorithm(iface)
        self.zoning_district_algorithm = ZoningDistrictAlgorithm(iface)
        self.district_plan_algorithm = DistrictPlanAlgorithm(iface)
        self.location_normalization_plan_algorithm = LocationNormalizationPlanAlgorithm(
            iface
        )
        self.nature_reserve_algorithm = NatureReserveAlgorithm(iface)
        self.did_area_algorithm = DidAreaAlgorithm(iface)

        self.high_utilization_zone_algorithm = HighUtilizationZoneAlgorithm(iface)
        self.hazard_map_algorithm = FloodHazardAreaAlgorithm(iface)
        self.coastline_workflow = CoastlineWorkflow(iface)
        self.population_mesh_workflow = PopulationMeshWorkflow(iface)
        self.coastline_workflow = CoastlineWorkflow(iface)
        self.fishing_port_workflow = FishingPortWorkflow(iface)
        self.port_area_workflow = PortAreaWorkflow(iface)
        self.hazard_map_workflow = HazardMapWorkflow(iface)

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
            text="GreenInfraPlannerJP",
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

        if not self.dockwidget.comboBox_municipality.currentData():
            message = "市区町村が選択されていません。市区町村を選択してください。"
            QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
            self.iface.messageBar().pushMessage("警告", message, level=Qgis.Warning)
            return

        # レイヤツリーの選択状態を解除
        self.iface.layerTreeView().setCurrentNode(None)

        real_estate_api_key = ApikeyDialog.get_real_estate_api_key()

        # 読み込み中のメッセージを表示
        waiting_item = QgsMessageBarItem(
            "読み込み中",
            "処理中です...",
            Qgis.Info,
            0,  # duration=0で自動で消えない
        )

        self.iface.messageBar().pushItem(waiting_item)
        QCoreApplication.processEvents()

        # Phase 1: ベースマップレイヤーの可視化
        self.basemap_workflow.execute(self.dockwidget.get_selected_basemaps())

        # Phase 2: 行政区域ポリゴンレイヤーの可視化（ベースマップグループ内に追加）
        basemap_group = self.basemap_workflow.create_group()
        # 行政区域class3レイヤーの可視化
        if self.dockwidget.checkBox_class3.isChecked():
            self.administrative_area_workflow.execute(
                prefecture_name=self.dockwidget.comboBox_prefecture.currentText(),
                class_type="class3",
                group=basemap_group,
            )

        # 行政区域class5レイヤーの可視化
        if self.dockwidget.checkBox_class5.isChecked():
            self.administrative_area_workflow.execute(
                prefecture_name=self.dockwidget.comboBox_prefecture.currentText(),
                class_type="class5",
                group=basemap_group,
            )

        # Phase 3: 不動産情報ライブラリの各種レイヤー可視化
        # 都市計画区域の可視化
        if self.dockwidget.checkBox_urban_area.isChecked():
            if real_estate_api_key:
                # Workflowを実行
                self.layer_workflow.execute(
                    self.urban_planning_algorithm,
                    api_key=real_estate_api_key,
                )
            else:
                message = "不動産情報ライブラリAPIキーが未設定のため、都市計画区域の取得をスキップします。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("警告", message, level=Qgis.Warning)

        # 用途地域の可視化
        if self.dockwidget.checkBox_use_district.isChecked():
            if real_estate_api_key:
                # Workflowを実行
                self.layer_workflow.execute(
                    self.zoning_district_algorithm, api_key=real_estate_api_key
                )
            else:
                message = "不動産情報ライブラリAPIキーが未設定のため、用途地域の取得をスキップします。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("警告", message, level=Qgis.Warning)

        # 地区計画の可視化
        if self.dockwidget.checkBox_district_planning.isChecked():
            if real_estate_api_key:
                # Workflowを実行
                self.layer_workflow.execute(
                    self.district_plan_algorithm, api_key=real_estate_api_key
                )
            else:
                message = "不動産情報ライブラリAPIキーが未設定のため、地区計画の取得をスキップします。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("警告", message, level=Qgis.Warning)

        # 立地適正化計画の可視化
        if self.dockwidget.checkBox_location_normalization_plan.isChecked():
            if real_estate_api_key:
                # Workflowを実行
                self.layer_workflow.execute(
                    self.location_normalization_plan_algorithm,
                    api_key=real_estate_api_key,
                )
            else:
                message = "不動産情報ライブラリAPIキーが未設定のため、立地適正化計画の取得をスキップします。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("警告", message, level=Qgis.Warning)

        # 自然公園地域の可視化
        if self.dockwidget.checkBox_nature_reserve.isChecked():
            if real_estate_api_key:
                # 都道府県コードが１桁の場合0を削除
                prefecture_code = self.dockwidget.comboBox_prefecture.currentData()
                api_prefecture_code = str(int(prefecture_code))

                self.layer_workflow.execute(
                    self.nature_reserve_algorithm,
                    api_key=real_estate_api_key,
                    prefecture_code=api_prefecture_code,
                )
            else:
                message = "不動産情報ライブラリAPIキーが未設定のため、自然公園地域の取得をスキップします。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("警告", message, level=Qgis.Warning)

        # 人口集中地区(DID)の可視化
        if self.dockwidget.checkBox_did.isChecked():
            if real_estate_api_key:
                self.layer_workflow.execute(
                    self.did_area_algorithm,
                    api_key=real_estate_api_key,
                    municipality_code=self.dockwidget.comboBox_municipality.currentData(),
                    municipality_name=self.dockwidget.comboBox_municipality.currentText(),
                )
            else:
                message = "不動産情報ライブラリAPIキーが未設定のため、人口集中地区(DID)の取得をスキップします。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("警告", message, level=Qgis.Warning)

        # 高度利用地区の可視化
        if self.dockwidget.checkBox_high_level_use_districts.isChecked():
            if real_estate_api_key:
                self.layer_workflow.execute(
                    self.high_utilization_zone_algorithm,
                    api_key=real_estate_api_key,
                )
            else:
                message = "不動産情報ライブラリAPIキーが未設定のため、高度利用地区の取得をスキップします。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("警告", message, level=Qgis.Warning)

        # Phase 4: 海岸線データの可視化
        umi_shiru_api_key = ApikeyDialog.get_umi_shiru_api_key()

        # 海岸線データの可視化
        if self.dockwidget.checkBox_coast_line.isChecked():
            self.coastline_workflow.execute(
                api_key=umi_shiru_api_key,
                municipality_code=self.dockwidget.comboBox_municipality.currentData(),
                municipality_name=self.dockwidget.comboBox_municipality.currentText(),
            )
        # 漁港区域データの可視化
        if self.dockwidget.checkBox_fishing_port_area.isChecked():
            self.fishing_port_workflow.execute(
                api_key=umi_shiru_api_key,
                municipality_code=self.dockwidget.comboBox_municipality.currentData(),
                municipality_name=self.dockwidget.comboBox_municipality.currentText(),
            )
        # 港湾区域データの可視化
        if self.dockwidget.checkBox_port_area.isChecked():
            self.port_area_workflow.execute(
                api_key=umi_shiru_api_key,
                municipality_code=self.dockwidget.comboBox_municipality.currentData(),
                municipality_name=self.dockwidget.comboBox_municipality.currentText(),
            )

        # Phase 5: 人口メッシュデータの可視化
        if self.dockwidget.checkBox_population_mesh.isChecked():
            estat_api_key = ApikeyDialog.get_estat_api_key()
            # 3次メッシュ（1km）の処理
            if self.dockwidget.radioButton_population_mesh_3rd.isChecked():
                if estat_api_key:
                    self.population_mesh_workflow.execute(
                        api_key=estat_api_key,
                        municipality_code=self.dockwidget.comboBox_municipality.currentData(),
                        municipality_name=self.dockwidget.comboBox_municipality.currentText(),
                        mesh_type="3rd",  # 3次メッシュ
                    )

                else:
                    message = "e-Stat APIキーが未設定のため、人口メッシュ（3次メッシュ）データの取得をスキップします。"
                    QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                    self.iface.messageBar().pushMessage(
                        "警告", message, level=Qgis.Warning
                    )

            # 4次メッシュ（500m）の処理
            if self.dockwidget.radioButton_population_mesh_4th.isChecked():
                if estat_api_key:
                    self.population_mesh_workflow.execute(
                        api_key=estat_api_key,
                        municipality_code=self.dockwidget.comboBox_municipality.currentData(),
                        municipality_name=self.dockwidget.comboBox_municipality.currentText(),
                        mesh_type="4th",  # 4次メッシュ
                    )
                else:
                    message = "e-Stat APIキーが未設定のため、人口メッシュ（4次メッシュ）データの取得をスキップします。"
                    QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                    self.iface.messageBar().pushMessage(
                        "警告", message, level=Qgis.Warning
                    )

        if self.dockwidget.checkBox_hazard.isChecked():
            self.hazard_map_workflow.execute(
                self.hazard_map_algorithm,
            )

        # Phase 6: 全てのレイヤー読み込み完了後、自治体領域にズームイン
        self.zoom_to_municipality(self.dockwidget.comboBox_municipality.currentData())

        self.iface.messageBar().popWidget(waiting_item)

    def on_prefecture_changed(self):
        """都道府県選択変更時の処理"""
        if not self.dockwidget:
            return

        api_key = ApikeyDialog.get_real_estate_api_key()
        selected_code = self.dockwidget.comboBox_prefecture.currentData()

        self.area_workflow.load_municipality_dropdown(
            self.dockwidget, api_key, selected_code
        )

    def zoom_to_municipality(self, municipality_code):
        """指定された市区町村コードにズーム"""
        # municipality_code が None または空値の場合は早期リターン
        if not municipality_code:
            message = "市区町村コードが指定されていません。"
            QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
            self.iface.messageBar().pushMessage("警告", message, level=Qgis.Warning)
            return
        # 範囲とCRSを取得
        if municipality_code in CITY_DEFAULT_BOUNDS:
            # 政令指定都市の場合はCITY_DEFAULT_BOUNDSからBBOXを取得
            bounds = CITY_DEFAULT_BOUNDS[municipality_code]
            extent = QgsRectangle(
                bounds["min_lon"],
                bounds["min_lat"],
                bounds["max_lon"],
                bounds["max_lat"],
            )
            source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        else:
            # 政令指定都市以外はポリゴンから範囲を取得
            polygon_layer = AdministrativeAreaClient().fetch_municipality_polygon(
                municipality_code
            )
            if polygon_layer is None or not polygon_layer.isValid():
                message = "自治体の行政区域データの取得に失敗しました。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("警告", message, level=Qgis.Warning)
                return
            extent = polygon_layer.extent()
            source_crs = polygon_layer.crs()

        # マップキャンバスのCRSに変換してズーム
        dest_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())
        transformed_extent = transform.transformBoundingBox(extent)

        self.iface.mapCanvas().setExtent(transformed_extent)
        self.iface.mapCanvas().refresh()

        return
