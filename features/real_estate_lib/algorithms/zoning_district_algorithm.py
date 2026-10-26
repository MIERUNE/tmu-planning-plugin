"""
用途地域区域データの取得機能モジュール
"""

from typing import Optional

from qgis.core import (
    Qgis,
    QgsFillSymbol,
    QgsVectorTileBasicRenderer,
    QgsVectorTileBasicRendererStyle,
    QgsVectorTileLayer,
)
from qgis.gui import QgisInterface

from ....utils.settings import ZOOM9_SCALE_THRESHOLD
from ..client import ReinfolibClient
from ..connect import (
    ZONING_DISTRICT_AREA_API_ENDPOINT,
)


class ZoningDistrictAlgorithm:
    """用途地域区域データ取得クラス"""

    LAYER_DISPLAY_NAME = "用途地域"

    def __init__(self, iface: QgisInterface):
        self.iface = iface

    def create_layer(self, authcfg: str) -> Optional[QgsVectorTileLayer]:
        """
        用途地域データをAPIから取得する
        Args:
            authcfg (str): APIキーを付与する認証設定ID（APIHeader）
        Returns:
            QgsVectorTileLayer : 追加に成功した場合はレイヤーオブジェクト
        """
        client = ReinfolibClient(authcfg)
        success, status_code = client.check_connection(
            ZONING_DISTRICT_AREA_API_ENDPOINT
        )
        # 接続チェック
        if not success:
            user_message = "APIサーバーへの接続に失敗しました。"
            self.iface.messageBar().pushMessage(
                "API接続エラー",
                f"{user_message} (HTTP Status: {status_code})",
                level=Qgis.MessageLevel.Critical,
            )
            return None

        # ベクトルタイルレイヤーのデータソースURIを作成
        params = {"response_format": "pbf", "z": "{z}", "x": "{x}", "y": "{y}"}
        get_real_estate_url = client.build_vector_tile_uri(
            ZONING_DISTRICT_AREA_API_ENDPOINT, params, zmin=11, zmax=15
        )

        layer_name = "用途地域"
        zoning_district_layer = QgsVectorTileLayer(get_real_estate_url, layer_name)

        # ズームレベル９以下では表示しない
        zoning_district_layer.setScaleBasedVisibility(True)
        zoning_district_layer.setMinimumScale(ZOOM9_SCALE_THRESHOLD)

        # スタイルの設定
        renderer = QgsVectorTileBasicRenderer()
        polygon_style = QgsVectorTileBasicRendererStyle()
        polygon_style.setStyleName("Polygons")
        polygon_style.setEnabled(True)

        polygon_style.setGeometryType(Qgis.GeometryType.Polygon)

        # シンボルを作成
        polygon_symbol = QgsFillSymbol.createSimple(
            {
                "color": "255,255,147,180",
                "outline_color": "221,207,144,255",
                "outline_width": "0.26",
            }
        )
        polygon_style.setSymbol(polygon_symbol)
        renderer.setStyles([polygon_style])
        zoning_district_layer.setRenderer(renderer)

        zoning_district_layer.triggerRepaint()

        return zoning_district_layer
