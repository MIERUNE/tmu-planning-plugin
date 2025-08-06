"""
エリア選択ワークフロー
都道府県の選択や管理を行うワークフローを提供するクラス
"""

from qgis.core import QgsMessageLog, Qgis

from ..area.area_settings import (
    PREFECTURE_LIST,
)


class AreaWorkflow:
    """エリア選択・管理のワークフロークラス"""

    def __init__(self, iface):
        self.iface = iface

    def load_prefecture_dropdown(self, dockwidget):
        """都道府県プルダウンを初期化"""
        try:
            dockwidget.set_prefecture_combobox(PREFECTURE_LIST)

            return True

        except Exception as e:
            QgsMessageLog.logMessage(
                f"都道府県リストの読み込み中にエラーが発生: {str(e)}",
                "Green Infra Plugin",
                level=Qgis.Critical,
            )
            return False
