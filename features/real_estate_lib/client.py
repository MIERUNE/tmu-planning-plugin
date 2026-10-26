"""
不動産情報ライブラリAPIクライアント
"""

import urllib.parse
from typing import Optional

from qgis.core import (
    Qgis,
    QgsBlockingNetworkRequest,
    QgsDataSourceUri,
    QgsMessageLog,
)
from qgis.PyQt.QtCore import QByteArray, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from ...utils.settings import PLUGIN_NAME
from .connect import CHECK_TILE_QUERY


class ReinfolibClient:
    """不動産情報ライブラリAPIのクライアント
    APIキーはQGIS認証マネージャーの認証設定（APIHeader）経由でヘッダーに付与する。
    """

    def __init__(self, authcfg: str):
        """
        Args:
            authcfg (str): APIキーを付与する認証設定ID（APIHeader）
        """
        self.authcfg = authcfg

    def check_connection(self, endpoint: str) -> tuple[bool, Optional[int]]:
        """APIキーを使ってタイルを取得できるか、タイルを1枚取得して確認
        Args:
            endpoint (str): 確認対象のタイル配信APIエンドポイント
        Returns:
            tuple[bool, Optional[int]]: (タイルを取得できたか, HTTPステータスコード)
        """
        blocking_request = QgsBlockingNetworkRequest()
        blocking_request.setAuthCfg(self.authcfg)
        error_code = blocking_request.get(
            QNetworkRequest(QUrl(endpoint + CHECK_TILE_QUERY))
        )
        http_status = blocking_request.reply().attribute(
            QNetworkRequest.Attribute.HttpStatusCodeAttribute
        )

        if error_code != QgsBlockingNetworkRequest.ErrorCode.NoError:
            QgsMessageLog.logMessage(
                f"API接続に失敗しました: {blocking_request.errorMessage()} (HTTPステータス: {http_status})",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Critical,
            )
            return False, http_status

        return True, http_status

    def get(self, url: str) -> QByteArray:
        """APIからデータを取得
        Args:
            url (str): APIエンドポイントURL（クエリ付き）
        Returns:
            QByteArray: レスポンスデータ
        Raises:
            Exception: リクエスト失敗時
        """
        blocking_request = QgsBlockingNetworkRequest()
        blocking_request.setAuthCfg(self.authcfg)
        error_code = blocking_request.get(QNetworkRequest(QUrl(url)))
        reply = blocking_request.reply()

        if error_code != QgsBlockingNetworkRequest.ErrorCode.NoError:
            http_status = reply.attribute(
                QNetworkRequest.Attribute.HttpStatusCodeAttribute
            )
            raise Exception(
                f"APIリクエスト失敗: {blocking_request.errorMessage()} (HTTP {http_status})"
            )

        return reply.content()

    def build_vector_tile_uri(
        self, endpoint: str, params: dict, zmin: int, zmax: int
    ) -> str:
        """ベクトルタイルレイヤーのデータソースURIを作成
        Args:
            endpoint (str): タイル配信APIのエンドポイント
            params (dict): クエリパラメータ（z/x/yは "{z}" 等のプレースホルダ）
            zmin (int): 最小ズームレベル
            zmax (int): 最大ズームレベル
        Returns:
            str: データソースURI
        """
        # {z}/{x}/{y} のプレースホルダはエンコードしない
        query = urllib.parse.urlencode(params, safe="{}")
        uri = QgsDataSourceUri()
        uri.setParam("type", "xyz")
        uri.setParam("url", f"{endpoint}?{query}")
        uri.setParam("zmin", str(zmin))
        uri.setParam("zmax", str(zmax))
        uri.setAuthConfigId(self.authcfg)
        return bytes(uri.encodedUri()).decode()
