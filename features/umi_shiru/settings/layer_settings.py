"""
海しるAPIデータ用レイヤー設定の基底クラス
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class UmiShiruLayerSettings(ABC):
    """
    海しるAPIデータのレイヤー設定基底クラス
    各データタイプ（海岸線、漁港区域等）で継承して使用
    """

    @abstractmethod
    def get_style_config(self) -> Dict[str, Any]:
        """
        レイヤーのスタイル設定を返す
        Returns:
            Dict[str, Any]: スタイル設定辞書
                - color: 色（文字列）
                - width: 線幅（数値）
                - opacity: 透明度（0.0-1.0）
        """
        pass

    @abstractmethod
    def get_default_layer_name(self) -> str:
        """
        デフォルトのレイヤー名を返す
        Returns:
            str: レイヤー名
        """
        pass
