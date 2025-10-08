"""
人口集中地区(DID)データの取得機能モジュール
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

from ..connect import (
    DID_AREA_API_ENDPOINT,
    PLUGIN_NAME,
    ZOOM9_SCALE_THRESHOLD,
)


class DidAreaAlgorithm:
    """人口集中地区(DID)データ取得クラス"""

    def __init__(self, iface):
        self.iface = iface

    # def _get_prefecture_name(self, prefecture_code: str) -> Optional[str]:
    #     """都道府県コードから都道府県名を取得"""
    #     prefecture_dict = dict(PREFECTURE_LIST)

    #     return prefecture_dict.get(prefecture_code, None)

    def _check_api_connection(self, api_key: str) -> tuple[bool, Optional[int]]:
        """APIキーの有効性を確認するための事前接続チェック"""
        # 接続テストのため一部タイルをリクエスト
        test_url = DID_AREA_API_ENDPOINT + "?response_format=geojson&z=13&x=7272&y=3225"

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

    def create_layer(
        self,
        api_key: str,
        municipality_code: Optional[str] = None,
        municipality_name: Optional[str] = None,
    ) -> Optional[QgsVectorTileLayer]:
        """
        人口集中地区(DID)データをAPIから取得する
        Args:
            api_key (str): APIキー
            municipality_code (Optional[str], optional): 市区町村コード。
            municipality_name (Optional[str], optional): 市区町村名。
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
        if municipality_code == "01100":  # 札幌市全域
            params = {
                "response_format": "pbf",
                "z": "{z}",
                "x": "{x}",
                "y": "{y}",
                "administrativeAreaCode": "01101,01102,01103,01104,01105,01106,01107,01108,01109,01110",
            }
        else:
            params = {
                "response_format": "pbf",
                "z": "{z}",
                "x": "{x}",
                "y": "{y}",
                "administrativeAreaCode": municipality_code,
            }

        encoded_params = urllib.parse.urlencode(params, safe="{}")

        # QGIS用にエンコード
        encoded_for_qgis = encoded_params.replace("=", "%3D").replace("&", "%26")
        encoded_tile_url = f"{DID_AREA_API_ENDPOINT}?{encoded_for_qgis}"

        # ベクトルタイルレイヤーのURLを作成
        get_real_estate_url = (
            f"type=xyz"
            f"&url={encoded_tile_url}"
            f"&zmax=15"
            f"&zmin=9"
            f"&http-header:Ocp-Apim-Subscription-Key={api_key}"
        )

        # prefecture_name = self._get_prefecture_name(prefecture_code)

        # 都道府県名が取得できた場合はレイヤー名に付加する
        if municipality_name:
            layer_name = f"人口集中地区(DID)_{municipality_name}"
        else:
            layer_name = "人口集中地区(DID)"
        did_area_layer = QgsVectorTileLayer(get_real_estate_url, layer_name)

        # ズームレベル９以下では表示しない
        did_area_layer.setScaleBasedVisibility(True)
        did_area_layer.setMinimumScale(ZOOM9_SCALE_THRESHOLD)

        # スタイルの設定
        renderer = QgsVectorTileBasicRenderer()
        polygon_style = QgsVectorTileBasicRendererStyle()
        polygon_style.setStyleName("Polygons")
        polygon_style.setLayerName("hits")
        polygon_style.setEnabled(True)

        polygon_style.setGeometryType(Qgis.GeometryType.Polygon)

        # シンボルを作成
        polygon_symbol = QgsFillSymbol.createSimple(
            {
                "color": "135,54,79,100",
                "outline_color": "124,44,69,255",
                "outline_width": "0.26",
            }
        )

        polygon_style.setSymbol(polygon_symbol)
        renderer.setStyles([polygon_style])
        did_area_layer.setRenderer(renderer)

        did_area_layer.triggerRepaint()

        return did_area_layer
