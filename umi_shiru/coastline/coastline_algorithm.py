"""
海岸線データの取得と処理を行うアルゴリズムクラス
"""

from ..common.base_algorithm import UmiShiruBaseAlgorithm
from .coastline_settings import CoastlineLayerSettings


class CoastlineAlgorithm(UmiShiruBaseAlgorithm):
    """
    海岸線データの取得と処理を行うアルゴリズムクラス
    """

    def __init__(self, iface):
        layer_settings = CoastlineLayerSettings()
        super().__init__(iface, layer_settings)

    # ========================================
    # 基底クラスの抽象メソッド実装
    # ========================================

    def get_data_type_key(self) -> str:
        """
        connect.pyのAPI設定キーを返す
        Returns:
            str: "coastline"
        """
        return "coastline"

    # ========================================
    # 海岸線データ特有の処理（必要に応じて追加）
    # ========================================


