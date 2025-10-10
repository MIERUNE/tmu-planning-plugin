"""
港湾区域データの取得と処理を行うアルゴリズムクラス
"""

from ..common.base_algorithm import UmiShiruBaseAlgorithm
from .port_area_settings import PortAreaLayerSettings


class PortAreaAlgorithm(UmiShiruBaseAlgorithm):
    """
    港湾区域データの取得と処理を行うアルゴリズムクラス
    """

    def __init__(self, iface):
        layer_settings = PortAreaLayerSettings()
        super().__init__(iface, layer_settings)

    # ========================================
    # 基底クラスの抽象メソッド実装
    # ========================================

    def get_data_type_key(self) -> str:
        """
        connect.pyのAPI設定キーを返す
        Returns:
            str: "port_area"
        """
        return "port_area"

    # ========================================
    # 港湾区域データ特有の処理（必要に応じて追加）
    # ========================================
