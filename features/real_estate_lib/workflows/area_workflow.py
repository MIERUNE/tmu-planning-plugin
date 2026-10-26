"""
エリア選択ワークフロー
都道府県の選択や管理を行うワークフローを提供するクラス
"""

from qgis.core import QgsMessageLog, Qgis

from ..settings_loader import (
    get_municipalities_by_prefecture,
)
from ..settings import PREFECTURE_LIST

from ...real_estate_lib.connect import (
    AREA_LIST_API_ENDPOINT,
    REINFOLIB_API_KEY_HEADER,
    REINFOLIB_AUTHCFG_NAME,
    RESPONSE_ENCODING,
)
from ....utils.api_keys import get_real_estate_api_key
from ....utils.auth import resolve_api_header_authcfg
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

    def load_municipality_dropdown(self, dockwidget, prefecture_code: str) -> bool:
        """市区町村プルダウンを更新
        APIキー未設定（または認証設定を作成できない）場合は API を使わず、
        同梱の市区町村一覧（JSON）から読み込む
        Args:
            dockwidget: DockWidgetインスタンス
            prefecture_code (str): 都道府県コード
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        # 都道府県未選択の場合は空にして終了
        if not prefecture_code:
            dockwidget.set_municipality_combobox([])
            return True

        try:
            # APIキー未設定時はJSONファイルの市区町村リストにフォールバック
            authcfg = resolve_api_header_authcfg(
                self.iface,
                REINFOLIB_AUTHCFG_NAME,
                REINFOLIB_API_KEY_HEADER,
                get_real_estate_api_key(),
                "不動産情報ライブラリ",
            )
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
