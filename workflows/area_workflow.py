"""
エリア選択ワークフロー
都道府県の選択や管理を行うワークフローを提供するクラス
"""

from qgis.core import QgsMessageLog, Qgis

from ..real_estate_lib.area.area_settings import (
    PREFECTURE_LIST,
    REAL_ESTATE_API_KEY,
)
from ..real_estate_lib.connect import (
    AREA_LIST_API_ENDPOINT,
    PLUGIN_NAME,
    RESPONSE_ENCODING,
)
from ..real_estate_lib.area.area_algorithm import AreaAlgorithm


class AreaWorkflow:
    """エリア選択・管理のワークフロークラス"""

    def __init__(self, iface):
        self.iface = iface
        self.area_algorithm = AreaAlgorithm(iface)

    def load_prefecture_dropdown(self, dockwidget) -> bool:
        """都道府県プルダウンを初期化
        Args:
            dockwidget: DockWidgetインスタンス
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            dockwidget.set_prefecture_combobox(PREFECTURE_LIST)

            return True

        except Exception as e:
            QgsMessageLog.logMessage(
                f"都道府県リストの読み込み中にエラーが発生: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return False

    def load_municipality_dropdown(self, dockwidget, prefecture_code: str) -> bool:
        """市区町村プルダウンを更新
        Args:
            dockwidget: DockWidgetインスタンス
            prefecture_code (str): 選択された都道府県コード
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            municipalities = self.area_algorithm.get_municipalities(
                prefecture_code=prefecture_code,
                api_key=REAL_ESTATE_API_KEY,
                base_url=AREA_LIST_API_ENDPOINT,
                response_encoding=RESPONSE_ENCODING,
            )

            if not municipalities:
                raise Exception(
                    f"市区町村データが取得できませんでした（都道府県コード: {prefecture_code}）"
                )

            dockwidget.set_municipality_combobox(municipalities)
            return True
        except Exception as e:
            QgsMessageLog.logMessage(
                f"市区町村読み込み中にエラーが発生: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            dockwidget.set_municipality_combobox([])
            return False
