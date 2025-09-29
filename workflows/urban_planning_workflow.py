from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsMessageLog,
    QgsProject,
    QgsRectangle,
)

from ..lib.area.fetch_municipality_polygon import fetch_and_calculate_bbox
from ..lib.area.tile_utils import calculate_tile_coords
from ..real_estate_lib.connect import PLUGIN_NAME
from ..real_estate_lib.urban_planning.urban_planning_algorithm import (
    UrbanPlanningAlgorithm,
)


class UrbanPlanningWorkflow:
    """都市計画区域データ取得・可視化ワークフロー"""

    def __init__(self, iface):
        self.iface = iface
        self.algorithm = UrbanPlanningAlgorithm(iface)

    def execute(self, api_key: str, municipality_code: str) -> bool:
        """
        ワークフローを実行し、都市計画区域タイルレイヤーをQGISに追加する
        Args:
            api_key (str): APIキー
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 市区町村コードから行政区域のBBOXを取得
            QgsMessageLog.logMessage(
                f"BBOX取得開始 (Code: {municipality_code})",
                PLUGIN_NAME,
                level=Qgis.Info,
            )
            bbox = fetch_and_calculate_bbox(municipality_code)
            if not bbox:
                self.iface.messageBar().pushMessage(
                    "エラー",
                    "行政区域のBBOX取得に失敗しました。ログを確認してください。",
                    level=Qgis.Critical,
                )
                return False

            # BBOXからタイル座標を計算
            min_zoom, max_zoom = 11, 15
            tile_list = calculate_tile_coords(bbox, min_zoom, max_zoom)
            QgsMessageLog.logMessage(
                f"計算されたタイル数: {len(tile_list)} (Zoom: {min_zoom}-{max_zoom})",
                PLUGIN_NAME,
                level=Qgis.Info,
            )

            added_layer = self.algorithm.get_urban_planning_area(api_key)

            # データが空なら処理を中断
            if not added_layer:
                message = "都市計画区域データの追加に失敗しました。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("情報", message, level=Qgis.Warning)
                return False

            QgsProject.instance().addMapLayer(added_layer)
            QgsMessageLog.logMessage(
                f"'{added_layer.name()}'都市計画区域レイヤーの追加に成功しました。",
                PLUGIN_NAME,
                level=Qgis.Success,
            )

            # 地図の表示範囲を取得したBBOXにズーム
            crs = QgsCoordinateReferenceSystem("EPSG:6668")
            map_extent = QgsRectangle(
                bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]
            )
            self.iface.mapCanvas().setDestinationCrs(crs)
            self.iface.mapCanvas().setExtent(map_extent)
            self.iface.mapCanvas().refresh()

            return True

        except Exception as e:
            QgsMessageLog.logMessage(
                f"都市計画区域の可視化中にエラーが発生: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return False
