"""
人口集中地区(DID)データの取得機能モジュール
"""

from typing import Optional

from qgis.core import (
    Qgis,
    QgsFillSymbol,
    QgsMessageLog,
    QgsVectorTileBasicRenderer,
    QgsVectorTileBasicRendererStyle,
    QgsVectorTileLayer,
)
from qgis.gui import QgisInterface

from ....utils.settings import PLUGIN_NAME, ZOOM9_SCALE_THRESHOLD
from ..client import ReinfolibClient
from ..connect import (
    DID_AREA_API_ENDPOINT,
)
from ..settings import DESIGNATED_CITIES_CODES


class DidAreaAlgorithm:
    """人口集中地区(DID)データ取得クラス"""

    LAYER_DISPLAY_NAME = "人口集中地区(DID)"

    def __init__(self, iface: QgisInterface):
        self.iface = iface

    def _get_administrative_area_code(
        self, municipality_code: Optional[str]
    ) -> Optional[str]:
        """
        市区町村コードから適切な行政区域コードを取得する
        政令指定都市の場合は全区のコードをカンマ区切りで返す

        Args:
            municipality_code: 市区町村コード

        Returns:
            行政区域コード（政令指定都市の場合は全区をカンマ区切り）
        """
        if not municipality_code:
            return None

        # 政令指定都市かチェック
        if municipality_code in DESIGNATED_CITIES_CODES:
            # 政令指定都市の場合、全区のコードをカンマ区切りで結合
            ward_codes = DESIGNATED_CITIES_CODES[municipality_code]
            QgsMessageLog.logMessage(
                f"政令指定都市({municipality_code})のため、全区のコードを使用します: {ward_codes}",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Info,
            )
            return ",".join(ward_codes)

        # 通常の市区町村の場合はそのまま返す
        QgsMessageLog.logMessage(
            f"通常の市区町村コードを使用します: {municipality_code}",
            PLUGIN_NAME,
            level=Qgis.MessageLevel.Info,
        )
        return municipality_code

    def create_layer(
        self,
        authcfg: str,
        municipality_code: str,
        municipality_name: str,
    ) -> Optional[QgsVectorTileLayer]:
        """
        人口集中地区(DID)データをAPIから取得する
        Args:
            authcfg (str): APIキーを付与する認証設定ID（APIHeader）
            municipality_code (str): 市区町村コード。
            municipality_name (str): 市区町村名。
        Returns:
            QgsVectorTileLayer : 追加に成功した場合はレイヤーオブジェクト
        """
        client = ReinfolibClient(authcfg)
        success, status_code = client.check_connection(DID_AREA_API_ENDPOINT)
        # 接続チェック
        if not success:
            user_message = "APIサーバーへの接続に失敗しました。"
            self.iface.messageBar().pushMessage(
                "API接続エラー",
                f"{user_message} (HTTP Status: {status_code})",
                level=Qgis.MessageLevel.Critical,
            )
            return None

        # 行政区域コードを取得（政令指定都市の場合は全区のコードを取得）
        administrative_area_code = self._get_administrative_area_code(municipality_code)

        # ベクトルタイルレイヤーのデータソースURIを作成
        params = {
            "response_format": "pbf",
            "z": "{z}",
            "x": "{x}",
            "y": "{y}",
            "administrativeAreaCode": administrative_area_code,
        }
        get_real_estate_url = client.build_vector_tile_uri(
            DID_AREA_API_ENDPOINT, params, zmin=9, zmax=15
        )

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
