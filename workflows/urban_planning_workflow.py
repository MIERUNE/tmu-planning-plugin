import json

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

            tiles_to_fetch = [
                {"z": 13, "x": 7272, "y": 3225},
                {"z": 13, "x": 7273, "y": 3225},
                {"z": 13, "x": 7272, "y": 3226},
                {"z": 13, "x": 7273, "y": 3226},
            ]

            all_geojson_features = []

            for tile_info in tiles_to_fetch:
                z = tile_info["z"]
                x = tile_info["x"]
                y = tile_info["y"]

                geojson_data = self.algorithm.get_urban_planning_area(api_key, z, x, y)

                if not geojson_data or geojson_data.isEmpty():
                    QgsMessageLog.logMessage(
                        f"タイル(z={z}, x={x}, y={y})のGeoJSONデータが見つかりませんでした。スキップします。",
                        PLUGIN_NAME,
                        level=Qgis.Warning,
                    )
                    continue

                geojson_string = geojson_data.data().decode("utf-8")

                try:
                    geojson_object = json.loads(geojson_string)

                    if "features" in geojson_object and isinstance(
                        geojson_object["features"], list
                    ):
                        all_geojson_features.extend(geojson_object["features"])
                    else:
                        QgsMessageLog.logMessage(
                            f"タイル(z={z}, x={x}, y={y})から有効なGeoJSONフィーチャを抽出できませんでした。データ形式を確認してください。",
                            PLUGIN_NAME,
                            level=Qgis.Warning,
                        )

                except json.JSONDecodeError:
                    QgsMessageLog.logMessage(
                        f"タイル(z={z}, x={x}, y={y})のレスポンスが不正なJSON形式です。",
                        PLUGIN_NAME,
                        level=Qgis.Critical,
                    )
                    self.iface.messageBar().pushMessage(
                        "エラー",
                        "APIからのレスポンスが不正なJSON形式です。APIの仕様を確認してください。",
                        level=Qgis.Critical,
                    )
                    return False
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f"GeoJSONデータの処理中に予期せぬエラーが発生: {e}",
                        PLUGIN_NAME,
                        level=Qgis.Critical,
                    )
                    return False

            if not all_geojson_features:
                message = "都市計画区域GeoJSONデータが1件も見つかりませんでした。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("情報", message, level=Qgis.Info)
                return False

            combined_geojson = {
                "type": "FeatureCollection",
                "features": all_geojson_features,
            }
            combined_geojson_string = json.dumps(combined_geojson)

            layer_name = "都市計画区域・区域区分"

            layer = QgsVectorLayer(combined_geojson_string, layer_name, "ogr")

            if not layer.isValid():
                QgsMessageLog.logMessage(
                    "結合されたGeoJSONデータからQGISレイヤーの作成に失敗しました。GeoJSONの構造を確認してください。",
                    PLUGIN_NAME,
                    level=Qgis.Critical,
                )
                self.iface.messageBar().pushMessage(
                    "エラー",
                    "都市計画区域・区域区分レイヤー作成に失敗しました。",
                    level=Qgis.Critical,
                )
                return False

            # === デバッグ出力の追加 ===
            QgsMessageLog.logMessage(
                f"QgsProject instance: {QgsProject.instance()}",
                PLUGIN_NAME,
                level=Qgis.Info,
            )
            if hasattr(QgsProject.instance(), "rootGroup"):
                QgsMessageLog.logMessage(
                    "QgsProject.instance() has rootGroup attribute.",
                    PLUGIN_NAME,
                    level=Qgis.Info,
                )
                QgsMessageLog.logMessage(
                    f"QgsProject root group: {QgsProject.instance().rootGroup()}",
                    PLUGIN_NAME,
                    level=Qgis.Info,
                )
                QgsProject.instance().rootGroup().addLayer(layer)
            else:
                QgsMessageLog.logMessage(
                    "CRITICAL: QgsProject.instance() does NOT have rootGroup attribute! (QGIS 3.x expected)",
                    PLUGIN_NAME,
                    level=Qgis.Critical,
                )
                # 万が一 rootGroup がない場合のフォールバック（ただしQGIS 3.xではこれは発生しないはず）
                QgsProject.instance().addMapLayer(layer)
            # === デバッグ出力の追加ここまで ===

            QgsMessageLog.logMessage(
                f"'{layer.name()}' レイヤーを追加しました。",
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
            self.iface.messageBar().pushMessage(
                "エラー",
                f"都市計画区域の可視化中にエラーが発生しました: {str(e)}",
                level=Qgis.Critical,
            )
            return False
