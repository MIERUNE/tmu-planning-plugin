"""
漁港区域データ固有の設定
"""

from typing import Any, Dict

from ..common.layer_settings import UmiShiruLayerSettings


class FishingPortLayerSettings(UmiShiruLayerSettings):
    """
    漁港区域レイヤーの設定クラス
    """

    def get_style_config(self) -> Dict[str, Any]:
        """
        漁港区域レイヤーのスタイル設定を返す
        Returns:
            Dict[str, Any]: スタイル設定辞書
        """
        return {
            "color": "#FF6600",
            "width": 0.1,
            "opacity": 0.8,
        }

    def get_default_layer_name(self) -> str:
        """
        漁港区域のデフォルトレイヤー名を返す
        Returns:
            str: レイヤー名
        """
        return "漁港区域"
