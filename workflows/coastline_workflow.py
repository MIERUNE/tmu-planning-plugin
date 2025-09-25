from qgis.core import Qgis, QgsMessageLog, QgsProject

from ..marine_gis.coastline.coastline_algorithm import CoastlineAlgorithm
from ..marine_gis.coastline.coastline_settings import DEFAULT_BOUNDS
from ..marine_gis.connect import PLUGIN_NAME
from .base_workflow import BaseWorkflow


class CoastlineWorkflow(BaseWorkflow):
    """海岸線データ取得・可視化ワークフロー"""

    def __init__(self, iface):
        super().__init__(iface)
        self.algorithm = CoastlineAlgorithm(iface)

    def execute(self, bounds=None) -> bool:
        """
        ワークフローを実行し、海岸線レイヤーをQGISに追加する
        Args:
            bounds (dict, optional): 取得範囲の境界。Noneの場合はデフォルト範囲を使用
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 1. パラメータの準備
            if bounds is None:
                bounds = DEFAULT_BOUNDS

            QgsMessageLog.logMessage(
                "海岸線データを取得します...", PLUGIN_NAME, level=Qgis.Info
            )

            # 2. データ取得
            geojson_data = self.algorithm.fetch_coastline_data(bounds)
            if not geojson_data:
                message = "海岸線データが見つかりませんでした。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("情報", message, level=Qgis.Info)
                return False

            # 3. レイヤー作成
            layer = self.algorithm.create_coastline_layer(geojson_data)

            # 4. QGISプロジェクトに追加
            QgsProject.instance().addMapLayer(layer)

            # 5. UI更新
            self.iface.mapCanvas().refresh()

            QgsMessageLog.logMessage(
                "海岸線レイヤーが正常に追加されました", PLUGIN_NAME, level=Qgis.Success
            )
            return True

        except Exception as e:
            error_message = f"海岸線の可視化中にエラーが発生: {str(e)}"
            QgsMessageLog.logMessage(error_message, PLUGIN_NAME, level=Qgis.Critical)
            self.iface.messageBar().pushMessage(
                "エラー", error_message, level=Qgis.Critical
            )
            return False
