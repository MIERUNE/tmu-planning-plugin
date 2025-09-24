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
        # パラメーターをエンコード
        params = {"response_format": "pbf", "z": "{z}", "x": "{x}", "y": "{y}"}
        encoded_params = urllib.parse.urlencode(params, safe="{}")
        
        # QGIS用にエンコード
        encoded_for_qgis = encoded_params.replace('=', '%3D').replace('&', '%26')
        encoded_tile_url = f"{URBAN_PLANNING_AREA_API_ENDPOINT}?{encoded_for_qgis}"
       
        # ベクトルタイルレイヤーのURLを作成
        get_real_estate_url = (
            f"type=xyz"
            f"&url={encoded_tile_url}"
            f"&zmax=15"
            f"&zmin=11"
            f"&http-header:Ocp-Apim-Subscription-Key={api_key}"
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
