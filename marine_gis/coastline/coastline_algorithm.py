from PyQt5.QtCore import QEventLoop, QUrl
from PyQt5.QtGui import QColor
from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsMessageLog,
    QgsNetworkAccessManager,
    QgsVectorLayer,
)

from ..connect import COASTLINE_API_ENDPOINT, PLUGIN_NAME
from .coastline_settings import COASTLINE_STYLE, LAYER_SELECTION


class CoastlineAlgorithm:
    """
    海岸線データの取得と処理を行うクラス
    """

    def __init__(self, iface):
        self.iface = iface

    def fetch_coastline_data(self, bounds, api_key):
        """
        海岸線データをAPIから取得
        Args:
            bounds (dict): 取得範囲の境界
            api_key (str): 海しるAPIキー
        Returns:
            str: GeoJSON文字列（取得失敗時はNone）
        """
        # APIパラメータ設定
        params = {
            "f": "geojson",
            "geometry": f"{bounds['min_lon']},{bounds['min_lat']},{bounds['max_lon']},{bounds['max_lat']}",
        }

        # URLにパラメータを追加
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{COASTLINE_API_ENDPOINT}/{LAYER_SELECTION}/query?{param_str}"

        QgsMessageLog.logMessage(
            f"海岸線データを取得中: {full_url}", PLUGIN_NAME, level=Qgis.Info
        )

        # ネットワークリクエスト実行
        request = QNetworkRequest(QUrl(full_url))
        # APIキーをヘッダーに設定
        request.setRawHeader(b"Ocp-Apim-Subscription-Key", api_key.encode("utf-8"))
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
                f"APIリクエスト成功: {full_url}", PLUGIN_NAME, level=Qgis.Info
            )

            return response_data.data().decode("utf-8-sig")
        finally:
            reply.deleteLater()

    def create_coastline_layer(self, geojson_data, layer_name="海岸線"):
        """
        GeoJSONデータからQGISレイヤーを作成
        Args:
            geojson_data (str): GeoJSON文字列
            layer_name (str): レイヤー名
        Returns:
            QgsVectorLayer: 作成されたレイヤー（失敗時はNone）
        """
        # ベクターレイヤーを作成
        layer = QgsVectorLayer(geojson_data, layer_name, "ogr")

        if not layer.isValid():
            raise Exception("ベクターレイヤーの作成に失敗しました")

        # CRSを設定
        crs = QgsCoordinateReferenceSystem("EPSG:4326")
        layer.setCrs(crs)

        # スタイルを適用
        self._apply_coastline_style(layer)

        return layer

    def _apply_coastline_style(self, layer):
        """
        海岸線レイヤーにスタイルを適用
        """
        try:
            # スタイル設定
            symbol = layer.renderer().symbol()
            color = QColor(COASTLINE_STYLE["color"])
            symbol.setColor(color)
            symbol.setWidth(COASTLINE_STYLE["width"])
            symbol.setOpacity(COASTLINE_STYLE["opacity"])
            layer.triggerRepaint()

        except Exception as e:
            QgsMessageLog.logMessage(
                f"スタイル適用エラー: {str(e)}", PLUGIN_NAME, level=Qgis.Warning
            )
