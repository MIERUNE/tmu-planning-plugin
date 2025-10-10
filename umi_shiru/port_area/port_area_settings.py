"""
港湾区域データ固有の設定
"""

from typing import Any, Dict

from ..common.layer_settings import UmiShiruLayerSettings


class PortAreaLayerSettings(UmiShiruLayerSettings):
    """
    港湾区域レイヤーの設定クラス
    """

    def get_style_config(self) -> Dict[str, Any]:
        """
        港湾区域レイヤーのスタイル設定を返す
        Returns:
            Dict[str, Any]: スタイル設定辞書
        """
        return {
            "color": "#9966CC",
            "width": 0.1,
            "opacity": 0.8,
        }

    def get_default_layer_name(self) -> str:
        """
        港湾区域のデフォルトレイヤー名を返す
        Returns:
            str: レイヤー名
        """
        return "港湾区域"
