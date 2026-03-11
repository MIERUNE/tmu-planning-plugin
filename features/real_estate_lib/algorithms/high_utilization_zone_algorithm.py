"""
高度利用地区データの取得機能モジュール
"""

import urllib.parse
from typing import Optional

from qgis.core import (
    Qgis,
    QgsFillSymbol,
    QgsMessageLog,
    QgsNetworkAccessManager,
    QgsVectorTileBasicRenderer,
    QgsVectorTileBasicRendererStyle,
    QgsVectorTileLayer,
)
from qgis.PyQt.QtCore import QEventLoop, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from ....utils.settings import PLUGIN_NAME
from ..connect import (
    HEIGHTENED_USE_DISTRICT_API_ENDPOINT,
)
from ....utils.settings import ZOOM9_SCALE_THRESHOLD


class HighUtilizationZoneAlgorithm:
    """高度利用地区データ取得クラス"""

    def __init__(self, iface):
        self.iface = iface

    def _check_api_connection(self, api_key: str) -> tuple[bool, Optional[int]]:
        """
        APIキーの有効性を確認するための事前接続チェック
        Args:
            api_key (str): APIキー
        Returns:
            tuple[bool, Optional[int]]: 接続成功フラグとHTTPステータスコード
        """
        # 接続テストのため一部タイルをリクエスト
        test_url = (
            HEIGHTENED_USE_DISTRICT_API_ENDPOINT
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

        reply.deleteLater()
        return True, http_status

    def create_layer(self, api_key: str) -> Optional[QgsVectorTileLayer]:
        """
        高度利用地区データをAPIから取得する
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
        encoded_tile_url = f"{HEIGHTENED_USE_DISTRICT_API_ENDPOINT}?{encoded_for_qgis}"

        # ベクトルタイルレイヤーのURLを作成
        get_real_estate_url = (
            f"type=xyz"
            f"&url={encoded_tile_url}"
            f"&zmax=15"
            f"&zmin=11"
            f"&http-header:Ocp-Apim-Subscription-Key={api_key}"
        )

        layer_name = "高度利用地区"
        high_utilization_zone_layer = QgsVectorTileLayer(
            get_real_estate_url, layer_name
        )

        # ズームレベル９以下では表示しない
        high_utilization_zone_layer.setScaleBasedVisibility(True)
        high_utilization_zone_layer.setMinimumScale(ZOOM9_SCALE_THRESHOLD)

        # スタイルの設定
        renderer = QgsVectorTileBasicRenderer()
        polygon_style = QgsVectorTileBasicRendererStyle()
        polygon_style.setStyleName("Polygons")
        polygon_style.setEnabled(True)

        polygon_style.setGeometryType(Qgis.GeometryType.Polygon)

        # シンボルを作成
        polygon_symbol = QgsFillSymbol.createSimple(
            {
                "color": "176,224,230,220",
                "outline_color": "80,185,199,255",
                "outline_width": "0.26",
            }
        )

        polygon_style.setSymbol(polygon_symbol)
        renderer.setStyles([polygon_style])
        high_utilization_zone_layer.setRenderer(renderer)

        high_utilization_zone_layer.triggerRepaint()

        return high_utilization_zone_layer
