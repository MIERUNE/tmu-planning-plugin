"""
都市計画区域データの取得機能モジュール
"""

from typing import Optional

from qgis.core import (
    Qgis,
    QgsVectorTileLayer,
)
from qgis.gui import QgisInterface

from ....utils.settings import ZOOM9_SCALE_THRESHOLD
from ..client import ReinfolibClient
from ..connect import (
    URBAN_PLANNING_AREA_API_ENDPOINT,
)


class UrbanPlanningAlgorithm:
    """都市計画区域データ取得クラス"""

    def __init__(self, iface: QgisInterface):
        self.iface = iface

    def create_layer(self, authcfg: str) -> Optional[QgsVectorTileLayer]:
        """
        都市計画区域データをAPIから取得する
        Args:
            authcfg (str): APIキーを付与する認証設定ID（APIHeader）
        Returns:
            QgsVectorTileLayer : 追加に成功した場合はレイヤーオブジェクト
        """
        client = ReinfolibClient(authcfg)
        success, status_code = client.check_connection(URBAN_PLANNING_AREA_API_ENDPOINT)
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
            URBAN_PLANNING_AREA_API_ENDPOINT, params, zmin=11, zmax=15
        )

        layer_name = "都市計画区域"
        urban_planning_layer = QgsVectorTileLayer(get_real_estate_url, layer_name)

        # ズームレベル９以下では表示しない
        urban_planning_layer.setScaleBasedVisibility(True)
        urban_planning_layer.setMinimumScale(ZOOM9_SCALE_THRESHOLD)

        return urban_planning_layer
