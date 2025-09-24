"""
都市計画区域データの取得機能モジュール
"""

from typing import Optional

from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsVectorTileLayer

from ..connect import PLUGIN_NAME


class UrbanPlanningAlgorithm:
    """都市計画区域データ取得クラス"""

    def __init__(self, iface):
        self.iface = iface

    def get_urban_planning_area(self, api_key: str) -> Optional[QgsVectorTileLayer]:
        """
        指定した市区町村の都市計画区域データをAPIから取得する
        Args:
            api_key (str): APIキー
        Returns:
            QgsVectorTileLayer : 追加に成功した場合はレイヤーオブジェクト
        """
        QgsMessageLog.logMessage(
            f"受け取ったAPIキー: '{api_key}'", PLUGIN_NAME, level=Qgis.Info
        )
        get_real_estate_url = f"type=xyz&url=https://www.reinfolib.mlit.go.jp/ex-api/external/XKT001?response_format%3Dpbf%26z%3D%7Bz%7D%26x%3D%7Bx%7D%26y%3D%7By%7D&zmax=14&zmin=0&http-header:Ocp-Apim-Subscription-Key={api_key}"

        layer_name = "都市計画区域"
        urban_planning_layer = QgsVectorTileLayer(get_real_estate_url, layer_name)

        if not urban_planning_layer.isValid():
            error_message = "ベクトルタイルレイヤーの読み込みに失敗しました。URLまたはAPIキーを確認してください。"
            QgsMessageLog.logMessage(error_message, PLUGIN_NAME, level=Qgis.Critical)
            self.iface.messageBar().pushMessage(
                "エラー", error_message, level=Qgis.Critical
            )
            return None

        # QGISプロジェクトにレイヤーを追加
        QgsProject.instance().addMapLayer(urban_planning_layer)
        QgsMessageLog.logMessage(
            f"レイヤー '{layer_name}' を追加しました。", PLUGIN_NAME, level=Qgis.Info
        )

        return urban_planning_layer
