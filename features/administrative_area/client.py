"""
国土交通データプラットフォームAPIクライアント
"""

import json
from typing import Optional

from qgis.core import Qgis, QgsBlockingNetworkRequest, QgsMessageLog
from qgis.PyQt.QtCore import QByteArray, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from ...utils.settings import PLUGIN_NAME
from .connect import DATASET_ID, MLIT_DPF_API_ENDPOINT, VECTOR_TILES_QUERY


class MlitDpfClient:
    """国交DPFの利用者向けAPI（GraphQL）クライアント"""

    def __init__(self, authcfg: str):
        """
        Args:
            authcfg (str): APIキーを付与する認証設定ID（APIHeader）
        """
        self.authcfg = authcfg

    def fetch_tile_url(self, data_id: str) -> Optional[str]:
        """データのベクトルタイルURLを取得
        Args:
            data_id (str): 国交DPFのデータID
        Returns:
            Optional[str]: タイルURL（{z}/{x}/{y}を含む）。取得できない場合は None
        """
        query = VECTOR_TILES_QUERY.format(dataset_id=DATASET_ID, data_id=data_id)
        response = self._post({"query": query, "variables": None})
        if response is None:
            return None

        try:
            results = response["data"]["data"]["getDataResults"]
            style = results[0]["vectorTiles"][0]["style"]
            # styleはJSON文字列で返る場合もある
            if isinstance(style, str):
                style = json.loads(style)
            source = next(iter(style["sources"].values()))
            return source["tiles"][0]
        except (KeyError, IndexError, TypeError, ValueError, StopIteration) as e:
            QgsMessageLog.logMessage(
                f"国土交通データプラットフォームのレスポンスからタイルURLを取得できませんでした（dataID: {data_id}）"
                f" {type(e).__name__}: {e}\nレスポンス: {response}",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Warning,
            )
            return None

    def _post(self, body: dict) -> Optional[dict]:
        """GraphQLリクエストを送信してJSONを返す"""
        request = QNetworkRequest(QUrl(MLIT_DPF_API_ENDPOINT))
        request.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json"
        )

        blocking_request = QgsBlockingNetworkRequest()
        blocking_request.setAuthCfg(self.authcfg)
        error_code = blocking_request.post(
            request, QByteArray(json.dumps(body).encode("utf-8"))
        )
        reply = blocking_request.reply()

        if error_code != QgsBlockingNetworkRequest.ErrorCode.NoError:
            http_status = reply.attribute(
                QNetworkRequest.Attribute.HttpStatusCodeAttribute
            )
            QgsMessageLog.logMessage(
                f"国土交通データプラットフォーム APIリクエスト失敗: {blocking_request.errorMessage()} (HTTP {http_status or 'Unknown'})",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Warning,
            )
            return None

        content = bytes(reply.content())
        if not content:
            QgsMessageLog.logMessage(
                "国土交通データプラットフォーム APIのレスポンスが空です。",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Warning,
            )
            return None

        try:
            response = json.loads(content.decode("utf-8-sig"))
        except ValueError as e:
            QgsMessageLog.logMessage(
                f"国土交通データプラットフォーム APIのレスポンスがJSONではありません。{type(e).__name__}: {e}",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Warning,
            )
            return None

        if response.get("errors"):
            QgsMessageLog.logMessage(
                f"国土交通データプラットフォーム APIがエラーを返しました: {response['errors']}",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Warning,
            )
            return None

        return response
