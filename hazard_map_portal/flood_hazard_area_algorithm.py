"""
都市計画区域データの取得機能モジュール
"""

from typing import Optional

from qgis.core import (
    QgsRasterLayer,
)

from .connect import FLOOD_HZARD_AREA_API_ENDPOINT, ZOOM9_SCALE_THRESHOLD


class FloodHazardAreaAlgorithm:
    """洪水浸水想定区域データ取得クラス"""

    def __init__(self, iface):
        self.iface = iface

    def create_FloodHazardArea_layer(self) -> Optional[QgsRasterLayer]:
        """
        洪水浸水想定区域データをAPIから取得する
        Args:
            api_key (str): APIキー
        Returns:
            QgsRasterLayer : 追加に成功した場合はレイヤーオブジェクト
        """
        # ラスターレイヤーのURLを作成
        get_flood_hazard_area_url = (
            f"type=xyz"
            f"&url={FLOOD_HZARD_AREA_API_ENDPOINT}/{{z}}/{{x}}/{{y}}.png"
            f"&zmax=18"
            f"&zmin=5"
        )
        layer_name = "洪水浸水想定区域"

        flood_hazard_area_layer = QgsRasterLayer(
            get_flood_hazard_area_url, layer_name, "wms"
        )

        # ズームレベル９以下では表示しない
        flood_hazard_area_layer.setScaleBasedVisibility(True)
        flood_hazard_area_layer.setMinimumScale(ZOOM9_SCALE_THRESHOLD)

        return flood_hazard_area_layer
