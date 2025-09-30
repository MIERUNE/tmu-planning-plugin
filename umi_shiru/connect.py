"""
海しるAPIの接続情報とAPIクライアント
"""

from PyQt5.QtCore import QEventLoop, QUrl
from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import Qgis, QgsMessageLog, QgsNetworkAccessManager

# 海しるAPI ベースURL
UMI_SHIRU_BASE_URL = "https://api.msil.go.jp"

# 海しるAPI エンドポイント定義
API_ENDPOINTS = {
    "coastline": "/coastline-type-ESI/v2/MapServer",
    # 今後追加予定:
    # "fishing_port": "/fishing-port-area/v2/MapServer",
    # "port_area": "/port-area/v2/MapServer",
}

# 海しるAPI レイヤー選択定義（データごとのデフォルト値）
LAYER_SELECTIONS = {
    "coastline": "1",  # 海岸線
    # 今後追加予定:
    # "fishing_port": "3",   # 漁港区域
    # "port_area": "3",      # 港湾区域
}

# TODO: 将来的にはe-Stat専用ディレクトリへ移動する予定
# e-Stat API ベースURL
E_STAT_BASE_URL = "https://www.e-stat.go.jp/gis/statmap-search/data"

# e-Stat API デフォルトパラメータ（行政区域データ用）
E_STAT_DEFAULT_PARAMS = {
    "dlserveyId": "A002005212020",  # 国勢調査2020年
    "coordSys": "1",  # 世界測地系
    "format": "shape",  # シェープファイル形式
    "downloadType": "5",  # 市区町村レベル
    "datum": "2011",  # 測地系2011（JGD2011）
}

# ログメッセージ用プラグイン名
PLUGIN_NAME = "Green Infra Plugin"


def build_estat_municipality_url(municipality_code: str) -> str:
    """
    e-Stat API用の市区町村データ取得URLを構築

    Args:
        municipality_code (str): 5桁の市区町村コード

    Returns:
        str: 構築されたURL
    """
    params = E_STAT_DEFAULT_PARAMS.copy()
    params["code"] = municipality_code

    param_str = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{E_STAT_BASE_URL}?{param_str}"


class UmiShiruApiClient:
    """
    海しるAPI共通クライアント
    """

    def __init__(self, api_key: str):
        """
        Args:
            api_key (str): 海しるAPIキー
        """
        self.api_key = api_key
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
        if data_type not in API_ENDPOINTS:
            raise ValueError(f"未定義のデータタイプ: {data_type}")

        if data_type not in LAYER_SELECTIONS:
            raise ValueError(f"未定義のレイヤー設定: {data_type}")

        endpoint = API_ENDPOINTS[data_type]
        layer_selection = LAYER_SELECTIONS[data_type]

        # URLを構築
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{self.base_url}{endpoint}/{layer_selection}/query?{param_str}"

        QgsMessageLog.logMessage(
            f"海しるAPIリクエスト開始: {full_url}", PLUGIN_NAME, level=Qgis.Info
        )

        # ネットワークリクエスト実行
        request = QNetworkRequest(QUrl(full_url))
        request.setRawHeader(b"Ocp-Apim-Subscription-Key", self.api_key.encode("utf-8"))

        nam = QgsNetworkAccessManager.instance()
        reply = nam.get(request)
        loop = QEventLoop()
        reply.finished.connect(loop.quit)
        loop.exec_()

        try:
            # エラーチェック
            if reply.error():
                http_status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
                error_response = reply.readAll().data().decode("utf-8", errors="ignore")
                error_message = f"APIリクエスト失敗: {reply.errorString()} (HTTP {http_status or 'Unknown'})"

                QgsMessageLog.logMessage(
                    f"{error_message}\nレスポンス詳細: {error_response}",
                    PLUGIN_NAME,
                    level=Qgis.Critical,
                )
                raise Exception(error_message)

            response_data = reply.readAll()
            if not response_data:
                raise Exception(f"APIからのレスポンスが空です。URL: {full_url}")

            QgsMessageLog.logMessage(
                f"海しるAPIリクエスト成功: {full_url}", PLUGIN_NAME, level=Qgis.Info
            )

            return response_data.data().decode("utf-8-sig")

        finally:
            reply.deleteLater()
