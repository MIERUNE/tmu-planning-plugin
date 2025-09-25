from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
)

from ..real_estate_lib.connect import PLUGIN_NAME
from ..real_estate_lib.urban_planning.urban_planning_algorithm import (
    UrbanPlanningAlgorithm,
)


class UrbanPlanningWorkflow:
    """都市計画区域データ取得・可視化ワークフロー"""

    def __init__(self, iface):
        self.iface = iface
        self.algorithm = UrbanPlanningAlgorithm(iface)

    def execute(self, api_key: str) -> bool:
        """
        ワークフローを実行し、都市計画区域タイルレイヤーをQGISに追加する
        Args:
            api_key (str): APIキー
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            QgsMessageLog.logMessage(
                "都市計画区域データを取得します...", PLUGIN_NAME, level=Qgis.Info
            )
            added_layer = self.algorithm.get_urban_planning_area(api_key)

            # データが空なら処理を中断
            if not added_layer:
                message = "都市計画区域データの追加に失敗しました。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("情報", message, level=Qgis.Info)
                return False

            # geojson_string = geojson_data.data().decode("utf-8")

            # layer_name = "都市計画区域"
            # layer = QgsVectorLayer(geojson_string, layer_name, "ogr")

            QgsProject.instance().addMapLayer(added_layer)
            QgsMessageLog.logMessage(
                f"'{added_layer.name()}'都市計画区域レイヤーの追加に成功しました。",
                PLUGIN_NAME,
                level=Qgis.Success,
            )

            return True

        except Exception as e:
            QgsMessageLog.logMessage(
                f"都市計画区域の可視化中にエラーが発生: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return False
