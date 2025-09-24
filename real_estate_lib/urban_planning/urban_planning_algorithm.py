"""
都市計画区域データの取得機能モジュール
"""

import urllib.parse
from typing import Optional

from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsVectorTileLayer

from ..connect import PLUGIN_NAME, URBAN_PLANNING_AREA_API_ENDPOINT


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
        # get_real_estate_url = f"type=xyz&url={URBAN_PLANNING_AREA_API_ENDPOINT}?response_format%3Dpbf%26z%3D%7Bz%7D%26x%3D%7Bx%7D%26y%3D%7By%7D&zmax=15&zmin=11&http-header:Ocp-Apim-Subscription-Key={api_key}"
        params = {"response_format": "pbf", "z": "{z}", "x": "{x}", "y": "{y}"}
        encoded_params = urllib.parse.urlencode(params, safe="{}")
        # QgsMessageLog.logMessage(
        #     f"エンコードしたパラメータ: '{encoded_params}'", PLUGIN_NAME, level=Qgis.Info
        # )
        encoded_for_qgis = encoded_params.replace('=', '%3D').replace('&', '%26')
        encoded_tile_url = f"{URBAN_PLANNING_AREA_API_ENDPOINT}?{encoded_for_qgis}"
        # QgsMessageLog.logMessage(
        #     f"エンコードしたURL: '{encoded_tile_url}'", PLUGIN_NAME, level=Qgis.Info
        # )
        get_real_estate_url = (
            f"type=xyz"
            f"&url={encoded_tile_url}"
            f"&zmax=15"
            f"&zmin=11"
            f"&http-header:Ocp-Apim-Subscription-Key={api_key}"
        )
        QgsMessageLog.logMessage(
            f"URLの組み立て: '{get_real_estate_url}'", PLUGIN_NAME, level=Qgis.Info
        )
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
