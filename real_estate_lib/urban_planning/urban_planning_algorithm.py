"""
都市計画区域データの取得機能モジュール
"""

from PyQt5.QtCore import QByteArray, QEventLoop, QUrl
from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import Qgis, QgsMessageLog, QgsNetworkAccessManager

from ..connect import PLUGIN_NAME, URBAN_PLANNING_AREA_API_ENDPOINT


class UrbanPlanningAlgorithm:
    """都市計画区域データ取得クラス"""

    def __init__(self, iface):
        self.iface = iface

    def get_urban_planning_area(self, api_key: str) -> QByteArray:
        """
        指定した市区町村の都市計画区域データをAPIから取得する
        Args:
            api_key (str): APIキー
        Returns:
            QByteArray: APIからのレスポンスデータ（GeoJSON形式のバイト配列）
        """

        # TODO : 指定した自治体のデータに必要なタイル分を取得するようにする
        z = 11
        x = 1828
        y = 752

        url_string = f"{URBAN_PLANNING_AREA_API_ENDPOINT}?response_format=geojson&z={z}&x={x}&y={y}"

        url = QUrl(url_string)
        request = QNetworkRequest(url)
        # ヘッダーにAPIキーを設定
        request.setRawHeader(b"Ocp-Apim-Subscription-Key", api_key.encode("utf-8"))

        # QGISのネットワークマネージャーを使って非同期でリクエストを送信
        nam = QgsNetworkAccessManager.instance()
        reply = nam.get(request)
        loop = QEventLoop()
        reply.finished.connect(loop.quit)
        loop.exec_()

        try:
            # エラーチェック
            if reply.error():
                http_status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
                error_message = (
                    f"APIリクエスト失敗: {reply.errorString()} (HTTP {http_status or 'Unknown'})"
                )
                QgsMessageLog.logMessage(
                    error_message, PLUGIN_NAME, level=Qgis.Critical
                )
                self.iface.messageBar().pushMessage(
                    "エラー", error_message, level=Qgis.Critical
                )
                return QByteArray()

            response_data = reply.readAll()
            if not response_data:
                QgsMessageLog.logMessage(
                    f"APIからのレスポンスが空です。URL: {url_string}",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )
                return QByteArray()

            QgsMessageLog.logMessage(
                f"APIリクエスト成功: {url_string}", PLUGIN_NAME, level=Qgis.Info
            )
            return response_data

        finally:
            reply.deleteLater()
