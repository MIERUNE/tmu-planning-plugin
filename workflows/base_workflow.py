"""
ワークフロー基底クラス
各機能の処理統合のベースを提供
"""

from abc import ABC, abstractmethod


class BaseWorkflow(ABC):
    """ワークフロー基底クラス"""

    def __init__(self, iface):
        self.iface = iface

    @abstractmethod
    def execute(self, **kwargs) -> bool:
        """ワークフローを実行

        Returns:
            Dict[str, Any]: 実行結果
        """
        pass
