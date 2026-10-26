"""
高度利用地区データの取得機能モジュール
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
    HEIGHTENED_USE_DISTRICT_API_ENDPOINT,
)


class HighUtilizationZoneAlgorithm:
    """高度利用地区データ取得クラス"""

    LAYER_DISPLAY_NAME = "高度利用地区"

    def __init__(self, iface: QgisInterface):
        self.iface = iface

    def create_layer(self, authcfg: str) -> Optional[QgsVectorTileLayer]:
        """
        高度利用地区データをAPIから取得する
        Args:
            authcfg (str): APIキーを付与する認証設定ID（APIHeader）
        Returns:
            QgsVectorTileLayer : 追加に成功した場合はレイヤーオブジェクト
        """
        client = ReinfolibClient(authcfg)
        success, status_code = client.check_connection(
            HEIGHTENED_USE_DISTRICT_API_ENDPOINT
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
            HEIGHTENED_USE_DISTRICT_API_ENDPOINT, params, zmin=11, zmax=15
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
