from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
    QgsVectorLayer,
)

from ..real_estate_lib.connect import PLUGIN_NAME
from ..real_estate_lib.urban_planning.urban_planning_algorithm import (
    UrbanPlanningAlgorithm,
)


class UrbanPlanningWorkflow:
    """都市計画区域の可視化ワークフロークラス"""

    def __init__(self, iface):
        self.iface = iface
        # 先ほど作成したアルゴリズムクラスのインスタンスを生成
        self.algorithm = UrbanPlanningAlgorithm(iface)

    def execute(self, api_key: str) -> bool:
        """
        ワークフローを実行し、都市計画区域をQGISに可視化する
        Args:
            api_key (str): APIキー
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            QgsMessageLog.logMessage(
                "都市計画区域データを取得します...", PLUGIN_NAME, level=Qgis.Info
            )
            geojson_data = self.algorithm.get_urban_planning_area(api_key)

            # データが空なら処理を中断
            if not geojson_data or geojson_data.isEmpty():
                message = "都市計画区域データが見つかりませんでした。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("情報", message, level=Qgis.Info)
                return False

            geojson_string = geojson_data.data().decode("utf-8")

            layer_name = "都市計画区域"
            layer = QgsVectorLayer(geojson_string, layer_name, "ogr")

            QgsProject.instance().addMapLayer(layer)
            QgsMessageLog.logMessage(
                f"'{layer.name()}' レイヤーを追加しました。",
                PLUGIN_NAME,
                level=Qgis.Success,
            )

            return True

            # features = QgsJsonUtils.stringToFeatures(geojson_string)
            # if not features:
            #     QgsMessageLog.logMessage(
            #         "GeoJSONからフィーチャーへの変換に失敗しました。",
            #         PLUGIN_NAME,
            #         level=Qgis.Critical,
            #     )
            #     return False

            # # CRSは不動産情報ライブラリの仕様に合わせて JGD2011 (EPSG:6668) を指定
            # layer_name = "都市計画区域"
            # layer = QgsVectorLayer("Polygon?crs=EPSG:6668", layer_name, "memory")
            # provider = layer.dataProvider()

            # provider.addAttributes(features[0].fields())
            # layer.updateFields()

            # provider.addFeatures(features)
            # layer.updateExtents()

            # QgsProject.instance().addMapLayer(layer)
            # QgsMessageLog.logMessage(
            #     f"'{layer.name()}' レイヤーを追加しました。",
            #     PLUGIN_NAME,
            #     level=Qgis.Success,
            # )

            # return True

        except Exception as e:
            QgsMessageLog.logMessage(
                f"都市計画区域の可視化中にエラーが発生: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return False
