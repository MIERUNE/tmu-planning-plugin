"""
エリア管理機能モジュール
都道府県や市区町村の情報を取得し、エリア選択に関する機能を提供
"""

import json
from typing import List, Tuple

from PyQt5.QtCore import QEventLoop, QUrl, QByteArray
from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import QgsNetworkAccessManager


class AreaAlgorithm:
    """エリア選択・管理クラス"""

    def __init__(self, iface):
        self.iface = iface

    def get_municipalities(
        self,
        prefecture_code: str,
        api_key: str,
        base_url: str,
        response_encoding: str = "utf-8-sig",
    ) -> List[Tuple[str, str]]:
        """指定都道府県の市区町村一覧を取得"""
        if not self._validate_inputs(prefecture_code, api_key):
            return []

        url_string = f"{base_url}?area={prefecture_code}"

        response_data = self._fetch_api_data(url_string, api_key)
        if response_data is None or response_data.isEmpty():
            raise Exception(
                f"APIからのレスポンスが空です（都道府県: {prefecture_code}）"
            )

        data = self._decode_response(response_data, response_encoding, prefecture_code)
        if data is None:
            return []

        municipalities = self._parse_municipalities(data, prefecture_code)
        if municipalities:
            municipalities.sort(key=lambda x: x[0])
            return municipalities

        return []

    def _validate_inputs(self, prefecture_code: str, api_key: str) -> bool:
        """入力値の検証
        Args:
            prefecture_code (str): 都道府県コード
            api_key (str): APIキー
        Returns:
            bool: 検証結果（True: 有効、False: 無効）
        """
        if not api_key or not prefecture_code:
            raise ValueError("APIキーまたは都道府県コードが未設定です")
        if not prefecture_code.isdigit() or len(prefecture_code) != 2:
            raise ValueError(f"無効な都道府県コード: {prefecture_code} (2桁の数字である必要があります)")
        return True

    def _fetch_api_data(self, url_string: str, api_key: str) -> QByteArray:
        """APIからデータを取得
        Args:
            url_string (str): APIエンドポイントURL
            api_key (str): APIキー
            plugin_name (str): プラグイン名（ログ出力用）
        Returns:
            QByteArray: レスポンスデータ（エラー時は空のQByteArray）
        """
        url = QUrl(url_string)
        request = QNetworkRequest(url)
        request.setRawHeader(b"Ocp-Apim-Subscription-Key", api_key.encode("utf-8"))

        nam = QgsNetworkAccessManager.instance()
        reply = nam.get(request)
        loop = QEventLoop()
        reply.finished.connect(loop.quit)
        loop.exec_()

        try:
            if reply.error():
                http_status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
                raise Exception(
                    f"APIリクエスト失敗: {reply.errorString()} (HTTP {http_status})"
                )
            return reply.readAll()
        finally:
            reply.deleteLater()

    def _decode_response(
        self, response_data: QByteArray, response_encoding: str, prefecture_code: str
    ) -> dict[str, str]:
        try:
            response_string = response_data.data().decode(response_encoding)
            return json.loads(response_string)
        except (UnicodeDecodeError, json.JSONDecodeError) as decode_error:
            raise Exception(
                f"レスポンスのデコード/JSONパースエラー（都道府県: {prefecture_code}）: {str(decode_error)}"
            ) from decode_error

    def _parse_municipalities(self, data, prefecture_code) -> List[Tuple[str, str]]:
        """APIレスポンスから市区町村データを抽出
        Args:
            data (dict): APIレスポンスデータ
            prefecture_code (str): 都道府県コード
        Returns:
            list: 市区町村のタプルリスト [(code, name), ...]
        """
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            if data.get("status", "Unknown") != "OK":
                raise Exception(
                    f"APIがエラーステータスを返しました: {data.get('status')}"
                )
            return [
                (item["id"], item["name"])
                for item in data["data"]
                if isinstance(item, dict) and "id" in item and "name" in item
            ]
        elif isinstance(data, list):
            return [
                (item["id"], item["name"])
                for item in data
                if isinstance(item, dict) and "id" in item and "name" in item
            ]
        else:
            raise Exception(
                f"無効なデータ形式を受信しました（都道府県: {prefecture_code}）: {data}"
            )
