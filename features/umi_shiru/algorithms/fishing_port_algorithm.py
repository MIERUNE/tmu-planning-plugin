"""
漁港区域データの取得と処理を行うアルゴリズムクラス
"""

from .base_algorithm import UmiShiruBaseAlgorithm
from ..settings.fishing_port_settings import FishingPortLayerSettings


class FishingPortAlgorithm(UmiShiruBaseAlgorithm):
    """
    漁港区域データの取得と処理を行うアルゴリズムクラス
    """

    def __init__(self, iface):
        layer_settings = FishingPortLayerSettings()
        super().__init__(iface, layer_settings)

    # ========================================
    # 実装必須の抽象メソッド
    # ========================================

    def get_data_type_key(self) -> str:
        """
        API設定で使用するデータタイプキーを返す
        Returns:
            str: データタイプキー（"fishing_port"）
        """
        return "fishing_port"

    # ========================================
    # 漁港区域データ特有の処理（必要に応じて追加）
    # ========================================
