"""
自然公園地域データの取得機能モジュール
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
    NATURE_RESERVE_AREA_API_ENDPOINT,
)
from ..settings import PREFECTURE_LIST


class NatureReserveAlgorithm:
    """自然公園地域データ取得クラス"""

    def __init__(self, iface: QgisInterface):
        self.iface = iface

    def _get_prefecture_name(self, prefecture_code: str) -> Optional[str]:
        """都道府県コードから都道府県名を取得"""
        prefecture_dict = dict(PREFECTURE_LIST)

        return prefecture_dict.get(prefecture_code, None)

    def create_layer(
        self, authcfg: str, prefecture_code: Optional[str] = None
    ) -> Optional[QgsVectorTileLayer]:
        """
        自然公園地域データをAPIから取得する
        Args:
            authcfg (str): APIキーを付与する認証設定ID（APIHeader）
            prefecture_code (Optional[str], optional): 都道府県コード。
        Returns:
            QgsVectorTileLayer : 追加に成功した場合はレイヤーオブジェクト
        """
        client = ReinfolibClient(authcfg)
        success, status_code = client.check_connection(NATURE_RESERVE_AREA_API_ENDPOINT)
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
        params = {
            "response_format": "pbf",
            "z": "{z}",
            "x": "{x}",
            "y": "{y}",
            "prefectureCode": prefecture_code,
        }
        get_real_estate_url = client.build_vector_tile_uri(
            NATURE_RESERVE_AREA_API_ENDPOINT, params, zmin=9, zmax=15
        )

        prefecture_name = self._get_prefecture_name(prefecture_code)

        # 都道府県名が取得できた場合はレイヤー名に付加する
        if prefecture_name:
            layer_name = f"自然公園地域_{prefecture_name}"
        else:
            layer_name = "自然公園地域"
        nature_reserve_layer = QgsVectorTileLayer(get_real_estate_url, layer_name)

        # ズームレベル９以下では表示しない
        nature_reserve_layer.setScaleBasedVisibility(True)
        nature_reserve_layer.setMinimumScale(ZOOM9_SCALE_THRESHOLD)

        # スタイルの設定
        renderer = QgsVectorTileBasicRenderer()
        polygon_style = QgsVectorTileBasicRendererStyle()
        polygon_style.setStyleName("Polygons")
        polygon_style.setEnabled(True)

        polygon_style.setGeometryType(Qgis.GeometryType.Polygon)

        # シンボルを作成
        polygon_symbol = QgsFillSymbol.createSimple(
            {
                "color": "130,220,130,180",
                "outline_color": "84,139,84,255",
                "outline_width": "0.26",
            }
        )
        polygon_style.setSymbol(polygon_symbol)
        renderer.setStyles([polygon_style])
        nature_reserve_layer.setRenderer(renderer)

        nature_reserve_layer.triggerRepaint()

        return nature_reserve_layer
