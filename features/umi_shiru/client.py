"""
海しるAPIクライアントとAPI設定
"""

from qgis.PyQt.QtCore import QUrl, QUrlQuery
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import Qgis, QgsBlockingNetworkRequest, QgsMessageLog

from ...utils.settings import PLUGIN_NAME

# 海しるAPI ベースURL
UMI_SHIRU_BASE_URL = "https://api.msil.go.jp"

# APIキーを付与するヘッダー名
UMI_SHIRU_API_KEY_HEADER = "Ocp-Apim-Subscription-Key"

# QGIS認証マネージャーに登録する認証設定の名前
UMI_SHIRU_AUTHCFG_NAME = "GreenInfraPlannerJP_UmiShiru"

# 海しるAPI 定義（エンドポイントとレイヤー情報）
UMI_SHIRU_API_CONFIG = {
    "coastline": {
        "endpoint": "/coastline-type-ESI/v2/MapServer",
        "layer": "1",  # 海岸線
    },
    "fishing_port": {
        "endpoint": "/fishing-port-area/v2/MapServer",
        "layer": "3",  # 漁港区域
    },
    "port_area": {
        "endpoint": "/port-area/v2/MapServer",
        "layer": "3",  # 港湾区域
    },
}

# 分割取得が必要な市区町村の設定
CITY_DIVISION_CONFIG = {
    "34202": {  # 呉市（広島県）
        "division_count": 4,
    },
    "42209": {  # 対馬市（長崎県）
        "division_count": 3,
    },
}

# データ取得時のバッファサイズ
BBOX_BUFFER_DEGREES = 0.01  # 約1km相当


class UmiShiruApiClient:
    """
    海しるAPI共通クライアント
    """

    def __init__(self, authcfg: str):
        """
        Args:
            authcfg (str): APIキーを付与する認証設定ID（APIHeader）
        """
        self.authcfg = authcfg
        self.base_url = UMI_SHIRU_BASE_URL

    def request(self, data_type: str, params: dict) -> str:
        """
        海しるAPIへのリクエストを実行
        Args:
            data_type (str): データタイプ（例: "coastline", "port_area"等）
            params (dict): クエリパラメータ
        Returns:
            str: レスポンスデータ（GeoJSON文字列）
        Raises:
            Exception: APIリクエスト失敗時
        """
        if data_type not in UMI_SHIRU_API_CONFIG:
            raise ValueError(f"未定義のデータタイプ: {data_type}")

        api_def = UMI_SHIRU_API_CONFIG[data_type]
        endpoint = api_def["endpoint"]
        layer_selection = api_def["layer"]

        base_full_url = f"{self.base_url}{endpoint}/{layer_selection}/query"

        query = QUrlQuery()
        for key, value in params.items():
            query.addQueryItem(key, str(value))

        # URLオブジェクトを生成
        url = QUrl(base_full_url)
        url.setQuery(query)
        full_url = url.toString()

        # ネットワークリクエスト実行
        blocking_request = QgsBlockingNetworkRequest()
        blocking_request.setAuthCfg(self.authcfg)
        error_code = blocking_request.get(QNetworkRequest(QUrl(full_url)))
        # reply() は QgsNetworkReplyContent。本文は content() で QByteArray として取り出す
        reply = blocking_request.reply()

        # エラーチェック
        if error_code != QgsBlockingNetworkRequest.ErrorCode.NoError:
            http_status = reply.attribute(
                QNetworkRequest.Attribute.HttpStatusCodeAttribute
            )
            error_response = bytes(reply.content()).decode("utf-8", errors="ignore")
            error_message = f"APIリクエスト失敗: {blocking_request.errorMessage()} (HTTP {http_status or 'Unknown'})"

            QgsMessageLog.logMessage(
                f"{error_message}\nレスポンス詳細: {error_response}",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Critical,
            )
            raise Exception(error_message)

        response_data = bytes(reply.content())
        if not response_data:
            raise Exception(f"APIからのレスポンスが空です。URL: {full_url}")

        QgsMessageLog.logMessage(
            f"海しるAPIリクエスト成功: {full_url}",
            PLUGIN_NAME,
            level=Qgis.MessageLevel.Info,
        )

        return response_data.decode("utf-8-sig")
