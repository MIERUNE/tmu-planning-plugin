"""
海岸線データ固有の設定
"""

from typing import Any, Dict

from ..common.layer_settings import UmiShiruLayerSettings


class CoastlineLayerSettings(UmiShiruLayerSettings):
    """
    海岸線レイヤーの設定クラス
    """

    def get_style_config(self) -> Dict[str, Any]:
        """
        海岸線レイヤーのスタイル設定を返す
        Returns:
            Dict[str, Any]: スタイル設定辞書
        """
        return {
            "color": "#0066CC",  # 海岸線の色（青）
            "width": 0.5,  # 線の太さ
            "opacity": 0.8,  # 透明度
        }

    def get_default_layer_name(self) -> str:
        """
        海岸線のデフォルトレイヤー名を返す
        Returns:
            str: レイヤー名
        """
        return "海岸線"
