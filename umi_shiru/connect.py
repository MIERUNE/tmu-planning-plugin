"""
海しるAPIの接続情報とAPIクライアント
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
    # 今後追加予定:
    # "fishing_port": {
    #     "endpoint": "/fishing-port-area/v2/MapServer",
    #     "layer": "3",  # 漁港区域
    # },
    # "port_area": {
    #     "endpoint": "/port-area/v2/MapServer",
    #     "layer": "3",  # 港湾区域
    # },
}

# TODO: 将来的にはe-Stat専用ディレクトリへ移動する予定
# e-Stat API 定義
E_STAT_API_CONFIG = {
    "base_url": "https://www.e-stat.go.jp/gis/statmap-search/data",
    "default_params": {
        "dlserveyId": "A002005212020",  # 国勢調査2020年
        "coordSys": "1",  # 世界測地系
        "format": "shape",  # シェープファイル形式
        "downloadType": "5",  # 市区町村レベル
        "datum": "2011",  # 測地系2011（JGD2011）
    },
}

# 主要都市のデフォルト境界範囲
CITY_DEFAULT_BOUNDS = {
    "01100": {  # 札幌市
        "min_lon": 141.0,
        "min_lat": 42.8,
        "max_lon": 141.6,
        "max_lat": 43.4,
    },
    # 他の都市も必要に応じて追加可能
}

# 分割取得が必要な市区町村の設定
CITY_DIVISION_CONFIG = {
    "42209": {  # 対馬市
        "division_count": 3,
    },
}

# データ取得時のバッファサイズ
BBOX_BUFFER_DEGREES = 0.01  # 約1km相当

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
    params = E_STAT_API_CONFIG["default_params"].copy()
    params["code"] = municipality_code

    query = QUrlQuery()
    for key, value in params.items():
        query.addQueryItem(key, str(value))

    # URLオブジェクトを生成
    url = QUrl(E_STAT_API_CONFIG["base_url"])
    url.setQuery(query)
    return url.toString()


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
