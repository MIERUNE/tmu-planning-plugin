"""
エリア選択ワークフロー
都道府県の選択や管理を行うワークフローを提供するクラス
"""

from typing import Optional

from qgis.core import QgsMessageLog, Qgis

from ..settings_loader import (
    get_municipalities_by_prefecture,
)
from ..settings import PREFECTURE_LIST

from ...real_estate_lib.connect import (
    AREA_LIST_API_ENDPOINT,
    RESPONSE_ENCODING,
)
from ....utils.settings import PLUGIN_NAME
from ..algorithms.area_algorithm import AreaAlgorithm


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
                level=Qgis.MessageLevel.Critical,
            )
            return False

    def load_municipality_dropdown(
        self, dockwidget, authcfg: Optional[str], prefecture_code: str
    ) -> bool:
        """市区町村プルダウンを更新
        Args:
            dockwidget: DockWidgetインスタンス
            authcfg (Optional[str]): APIキーを付与する認証設定ID（APIHeader）。
                None の場合は API を使わず、同梱の市区町村一覧（JSON）から読み込む
            prefecture_code (str): 都道府県コード
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        # 都道府県未選択の場合は空にして終了
        if not prefecture_code:
            dockwidget.set_municipality_combobox([])
            return True

        try:
            if authcfg:
                municipalities = self.area_algorithm.get_municipalities(
                    prefecture_code=prefecture_code,
                    authcfg=authcfg,
                    base_url=AREA_LIST_API_ENDPOINT,
                    response_encoding=RESPONSE_ENCODING,
                )
            else:
                municipalities = get_municipalities_by_prefecture(prefecture_code)

            dockwidget.set_municipality_combobox(municipalities)
            return True

        except Exception as e:
            # フォールバック: JSONファイルの市区町村リストを使用
            municipalities = get_municipalities_by_prefecture(prefecture_code)
            if not municipalities:
                QgsMessageLog.logMessage(
                    f"APIおよびJSONファイルの両方から市区町村データが取得できませんでした（都道府県: {prefecture_code}）。元のエラー: {str(e)}",
                    PLUGIN_NAME,
                    level=Qgis.MessageLevel.Critical,
                )
                dockwidget.set_municipality_combobox([])
                return False

            dockwidget.set_municipality_combobox(municipalities)
            return True
