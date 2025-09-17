# from qgis.core import (
#     Qgis,
#     QgsMessageLog,
#     QgsProject,
# )

# from ..real_estate_lib.connect import PLUGIN_NAME

# class UrbanPlanningWorkflow:
#     """都市計画区域の可視化ワークフロークラス"""

#     def __init__(self, iface):
#         self.iface = iface
#         # 先ほど作成したアルゴリズムクラスのインスタンスを生成
#         self.algorithm = UrbanPlanningAlgorithm(iface)

#     def execute(self, api_key: str) -> bool:
#         """
#         ワークフローを実行し、都市計画区域をQGISに可視化する
#         Args:
#             api_key (str): APIキー
#         Returns:
#             bool: 成功した場合はTrue、失敗した場合はFalse
#         """
#         try:
#             QgsMessageLog.logMessage(
#                 "都市計画区域データを取得します...", PLUGIN_NAME, level=Qgis.Info
#             )
#             geojson_data = self.algorithm.get_urban_planning_area(api_key)

#             # データが空なら処理を中断
#             if not geojson_data or geojson_data.isEmpty():
#                 message = "都市計画区域データが見つかりませんでした。"
#                 QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
#                 self.iface.messageBar().pushMessage("情報", message, level=Qgis.Info)
#                 return False

#             geojson_string = geojson_data.data().decode("utf-8")

#             layer_name = "都市計画区域"
#             layer = QgsVectorLayer(geojson_string, layer_name, "ogr")

#             QgsProject.instance().addMapLayer(layer)
#             QgsMessageLog.logMessage(
#                 f"'{layer.name()}' レイヤーを追加しました。",
#                 PLUGIN_NAME,
#                 level=Qgis.Success,
#             )

#             return True

#         except Exception as e:
#             QgsMessageLog.logMessage(
#                 f"都市計画区域の可視化中にエラーが発生: {str(e)}",
#                 PLUGIN_NAME,
#                 level=Qgis.Critical,
#             )
#             return False

"""
タイルレイヤー用のワークフロー
タイル形式のAPIからデータを読み込み、QGISにレイヤーとして追加する
"""

import json
import os
import math

from PyQt5.QtCore import QByteArray
from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsVectorLayer

from ..real_estate_lib.connect import PLUGIN_NAME
from ..real_estate_lib.urban_planning.urban_planning_algorithm import (
    UrbanPlanningAlgorithm,
)


class UrbanPlanningWorkflow:
    """タイルレイヤーの可視化ワークフロー"""

    def __init__(self, iface):
        self.iface = iface
        self.algorithm = UrbanPlanningAlgorithm(iface)

        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))

        self.MUNICIPAL_BOUNDARY_FILE = os.path.join(
                self.plugin_dir, "../../area/data/N03-20250101_14.geojson"
            )
            
        QgsMessageLog.logMessage(f"ローカル行政区域GeoJSONパス: {self.MUNICIPAL_BOUNDARY_FILE}", PLUGIN_NAME, level=Qgis.Info)
    
    def _load_local_geojson_boundary(self, municipality_code: str) -> QByteArray:
        """
        ローカルのGeoJSONファイルから、指定された市区町村コードの境界データを取得するヘルパーメソッド。
        この実装では、設定されたファイル全体を読み込み、指定されたコードのフィーチャを探します。
        """
        QgsMessageLog.logMessage(f"ローカルファイルから市区町村境界GeoJSONを読み込み中: {self.MUNICIPAL_BOUNDARY_FILE}", PLUGIN_NAME, level=Qgis.Info)

        if not os.path.exists(self.MUNICIPAL_BOUNDARY_FILE):
            QgsMessageLog.logMessage(
                f"エラー: 行政区域GeoJSONファイルが見つかりません: {self.MUNICIPAL_BOUNDARY_FILE}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return QByteArray()
        
        try:
            with open(self.MUNICIPAL_BOUNDARY_FILE, "r", encoding="utf-8") as f:
                full_geojson_data = json.load(f)

            found_feature = None
            if "features" in full_geojson_data and isinstance(full_geojson_data["features"], list):
                for feature in full_geojson_data["features"]:
                    if "properties" in feature and feature["properties"].get("N03_007") == municipality_code:
                        found_feature = feature
                        break

            if found_feature:
                # 見つかったフィーチャのみを含むFeatureCollectionとして返す
                result_geojson = {"type": "FeatureCollection", "features": [found_feature]}
                return QByteArray(json.dumps(result_geojson).encode("utf-8"))
            else:
                QgsMessageLog.logMessage(
                    f"ローカルファイル '{self.MUNICIPAL_BOUNDARY_FILE}' 内で市区町村コード '{municipality_code}' に一致するフィーチャが見つかりませんでした。",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )
                return QByteArray()

        except Exception as e:
            QgsMessageLog.logMessage(
                f"ローカルGeoJSONファイルの読み込みまたはパース中にエラーが発生: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return QByteArray()

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
            # TODO: ここを「指定した自治体に合わせて必要なタイル座標のリスト」を生成するロジックに置き換える
            # 例: 指定されたズームレベルで、ある地理的範囲をカバーするタイルのリストを計算する
            # ここでは便宜的に、少数のタイル座標をハードコードします。
            # 例: 範囲を拡大
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
                    # JSON文字列をPythonオブジェクトにパース
                    geojson_object = json.loads(geojson_string)

                    # GeoJSON FeatureCollectionの "features" リストからフィーチャを抽出
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

            # 取得した全てのフィーチャを結合して単一のGeoJSON FeatureCollectionを構築
            combined_geojson = {
                "type": "FeatureCollection",
                "features": all_geojson_features,
            }
            combined_geojson_string = json.dumps(
                combined_geojson
            )  # QgsVectorLayerに渡すために文字列に戻す

            layer_name = "都市計画区域・区域区分"

            # GeoJSON文字列から直接QgsVectorLayerを作成
            # "ogr" プロバイダがGeoJSON文字列を処理できます。
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

            QgsProject.instance().addMapLayer(layer)

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
