"""
用途地域区域データの取得機能モジュール
"""

import urllib.parse
from typing import Optional

from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsNetworkAccessManager,
    QgsVectorTileLayer,
)
from qgis.PyQt.QtCore import QEventLoop, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from ..connect import PLUGIN_NAME, ZONING_DISTRICT_AREA_API_ENDPOINT


class ZoningDistrictAlgorithm:
    """用途地域区域データ取得クラス"""

    def __init__(self, iface):
        self.iface = iface

    def _check_api_connection(self, api_key: str) -> tuple[bool, Optional[int]]:
        """APIキーの有効性を確認するための事前接続チェック"""
        # 接続テストとしてズームレベル0のタイルをリクエスト
        test_url = (
            ZONING_DISTRICT_AREA_API_ENDPOINT
            + "?response_format=geojson&z=13&x=7272&y=3225"
        )

        request = QNetworkRequest(QUrl(test_url))
        request.setRawHeader(b"Ocp-Apim-Subscription-Key", api_key.encode("utf-8"))

        nam = QgsNetworkAccessManager.instance()
        reply = nam.get(request)

        loop = QEventLoop()
        reply.finished.connect(loop.quit)
        loop.exec_()

        http_status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)

        if reply.error():
            QgsMessageLog.logMessage(
                f"API接続に失敗しました: {reply.errorString()} (HTTPステータス: {http_status})",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            reply.deleteLater()
            return False, http_status

        QgsMessageLog.logMessage(
            "APIキーの有効性を確認しました (HTTP 200)", PLUGIN_NAME, level=Qgis.Info
        )
        reply.deleteLater()
        return True, http_status

    def create_layer(self, api_key: str) -> Optional[QgsVectorTileLayer]:
        """
        用途地域データをAPIから取得する
        Args:
            api_key (str): APIキー
        Returns:
            QgsVectorTileLayer : 追加に成功した場合はレイヤーオブジェクト
        """
        success, status_code = self._check_api_connection(api_key)
        # 接続チェック
        if not success:
            user_message = "APIサーバーへの接続に失敗しました。"
            self.iface.messageBar().pushMessage(
                "API接続エラー",
                f"{user_message} (HTTP Status: {status_code})",
                level=Qgis.Critical,
            )
            return None

        # パラメーターをエンコード
        params = {"response_format": "pbf", "z": "{z}", "x": "{x}", "y": "{y}"}
        encoded_params = urllib.parse.urlencode(params, safe="{}")

        # QGIS用にエンコード
        encoded_for_qgis = encoded_params.replace("=", "%3D").replace("&", "%26")
        encoded_tile_url = f"{ZONING_DISTRICT_AREA_API_ENDPOINT}?{encoded_for_qgis}"

        # ベクトルタイルレイヤーのURLを作成
        get_real_estate_url = (
            f"type=xyz"
            f"&url={encoded_tile_url}"
            f"&zmax=15"
            f"&zmin=11"
            f"&http-header:Ocp-Apim-Subscription-Key={api_key}"
        )

        layer_name = "用途地域"
        urban_planning_layer = QgsVectorTileLayer(get_real_estate_url, layer_name)

        return urban_planning_layer
