"""
海しるAPIクライアントとAPI設定
"""

from PyQt5.QtCore import QEventLoop, QUrl, QUrlQuery
from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import Qgis, QgsMessageLog, QgsNetworkAccessManager

# 海しるAPI ベースURL
UMI_SHIRU_BASE_URL = "https://api.msil.go.jp"

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

# 政令指定都市のデフォルト境界範囲
CITY_DEFAULT_BOUNDS = {
    # 北海道
    "01100": {  # 札幌市
        "min_lon": 140.95,
        "min_lat": 42.71,
        "max_lon": 141.65,
        "max_lat": 43.29,
    },
    # 宮城県
    "04100": {  # 仙台市
        "min_lon": 140.63,
        "min_lat": 38.15,
        "max_lon": 141.05,
        "max_lat": 38.42,
    },
    # 埼玉県
    "11100": {  # さいたま市
        "min_lon": 139.55,
        "min_lat": 35.83,
        "max_lon": 139.72,
        "max_lat": 35.98,
    },
    # 千葉県
    "12100": {  # 千葉市
        "min_lon": 140.03,
        "min_lat": 35.51,
        "max_lon": 140.23,
        "max_lat": 35.73,
    },
    # 神奈川県
    "14100": {  # 横浜市
        "min_lon": 139.46,
        "min_lat": 35.31,
        "max_lon": 139.78,
        "max_lat": 35.61,
    },
    "14130": {  # 川崎市
        "min_lon": 139.58,
        "min_lat": 35.48,
        "max_lon": 139.73,
        "max_lat": 35.65,
    },
    "14150": {  # 相模原市
        "min_lon": 139.19,
        "min_lat": 35.45,
        "max_lon": 139.45,
        "max_lat": 35.62,
    },
    # 新潟県
    "15100": {  # 新潟市
        "min_lon": 138.77,
        "min_lat": 37.59,
        "max_lon": 139.36,
        "max_lat": 37.96,
    },
    # 静岡県
    "22100": {  # 静岡市
        "min_lon": 138.01,
        "min_lat": 34.82,
        "max_lon": 138.53,
        "max_lat": 35.49,
    },
    "22130": {  # 浜松市
        "min_lon": 137.49,
        "min_lat": 34.61,
        "max_lon": 137.99,
        "max_lat": 35.37,
    },
    # 愛知県
    "23100": {  # 名古屋市
        "min_lon": 136.80,
        "min_lat": 35.03,
        "max_lon": 137.03,
        "max_lat": 35.28,
    },
    # 京都府
    "26100": {  # 京都市
        "min_lon": 135.58,
        "min_lat": 34.89,
        "max_lon": 135.88,
        "max_lat": 35.31,
    },
    # 大阪府
    "27100": {  # 大阪市
        "min_lon": 135.38,
        "min_lat": 34.59,
        "max_lon": 135.59,
        "max_lat": 34.76,
    },
    "27140": {  # 堺市
        "min_lon": 135.40,
        "min_lat": 34.46,
        "max_lon": 135.59,
        "max_lat": 34.62,
    },
    # 兵庫県
    "28100": {  # 神戸市
        "min_lon": 134.90,
        "min_lat": 34.58,
        "max_lon": 135.41,
        "max_lat": 34.88,
    },
    # 岡山県
    "33100": {  # 岡山市
        "min_lon": 133.72,
        "min_lat": 34.55,
        "max_lon": 134.12,
        "max_lat": 34.93,
    },
    # 広島県
    "34100": {  # 広島市
        "min_lon": 132.32,
        "min_lat": 34.25,
        "max_lon": 132.65,
        "max_lat": 34.58,
    },
    # 福岡県
    "40100": {  # 北九州市
        "min_lon": 130.59,
        "min_lat": 33.72,
        "max_lon": 131.02,
        "max_lat": 33.95,
    },
    "40130": {  # 福岡市
        "min_lon": 130.20,
        "min_lat": 33.43,
        "max_lon": 130.49,
        "max_lat": 33.68,
    },
    # 熊本県
    "43100": {  # 熊本市
        "min_lon": 130.56,
        "min_lat": 32.69,
        "max_lon": 130.88,
        "max_lat": 32.92,
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

# ログメッセージ用プラグイン名
PLUGIN_NAME = "Green Infra Plugin"


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
