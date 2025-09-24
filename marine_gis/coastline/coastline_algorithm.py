import tempfile

from PyQt5.QtCore import QEventLoop, QUrl
from PyQt5.QtGui import QColor
from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsMessageLog,
    QgsNetworkAccessManager,
    QgsProject,
    QgsVectorLayer,
)

from ..connect import COASTLINE_API_ENDPOINT, PLUGIN_NAME, UMI_SHIRU_API_KEY
from .coastline_settings import COASTLINE_STYLE, DEFAULT_BOUNDS, LAYER_SELECTION


class CoastlineAlgorithm:
    """
    海岸線データの取得と処理を行うクラス
    """

    def __init__(self, iface):
        self.iface = iface

    def get_coastline_data(self, bounds=None):
        """
        海岸線データを取得してQGISに表示
        """
        try:
            if bounds is None:
                bounds = DEFAULT_BOUNDS

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
            request.setRawHeader(
                b"Ocp-Apim-Subscription-Key", UMI_SHIRU_API_KEY.encode("utf-8")
            )
            nam = QgsNetworkAccessManager.instance()
            reply = nam.get(request)
            loop = QEventLoop()
            reply.finished.connect(loop.quit)
            loop.exec_()

            try:
                # エラーチェック
                if reply.error():
                    http_status = reply.attribute(
                        QNetworkRequest.HttpStatusCodeAttribute
                    )
                    error_response = (
                        reply.readAll().data().decode("utf-8", errors="ignore")
                    )
                    error_message = f"APIリクエスト失敗: {reply.errorString()} (HTTP {http_status or 'Unknown'})"

                    QgsMessageLog.logMessage(
                        f"{error_message}\nレスポンス詳細: {error_response}",
                        PLUGIN_NAME,
                        level=Qgis.Critical,
                    )
                    self.iface.messageBar().pushMessage(
                        "エラー", error_message, level=Qgis.Critical
                    )
                    return False

                response_data = reply.readAll()
                if not response_data:
                    QgsMessageLog.logMessage(
                        f"APIからのレスポンスが空です。URL: {full_url}",
                        PLUGIN_NAME,
                        level=Qgis.Warning,
                    )
                    return False

                QgsMessageLog.logMessage(
                    f"APIリクエスト成功: {full_url}", PLUGIN_NAME, level=Qgis.Info
                )

                geojson_string = response_data.data().decode("utf-8-sig")
                self._add_coastline_layer(geojson_string)
                return True
            finally:
                reply.deleteLater()

        except Exception as e:
            QgsMessageLog.logMessage(
                f"海岸線データ取得エラー: {str(e)}", PLUGIN_NAME, level=Qgis.Critical
            )
            return False

    def _add_coastline_layer(self, geojson_data):
        """
        GeoJSONデータをQGISレイヤーとして追加
        """
        try:
            # 一時ファイルにGeoJSONを保存
            with tempfile.NamedTemporaryFile(
                mode="wt", suffix=".geojson", delete=False, encoding="utf-8"
            ) as temp_file:
                temp_file.write(geojson_data)
                temp_file_path = temp_file.name

            # ベクターレイヤーを作成
            layer = QgsVectorLayer(temp_file_path, "海岸線", "ogr")

            if layer.isValid():
                # CRSを設定
                crs = QgsCoordinateReferenceSystem("EPSG:4326")
                layer.setCrs(crs)

                # スタイルを適用
                self._apply_coastline_style(layer)

                # プロジェクトに追加
                QgsProject.instance().addMapLayer(layer)

                # マップキャンバスを更新
                self.iface.mapCanvas().refresh()

                QgsMessageLog.logMessage(
                    "海岸線レイヤーが正常に追加されました", PLUGIN_NAME, level=Qgis.Info
                )
            else:
                QgsMessageLog.logMessage(
                    "海岸線レイヤーの作成に失敗しました",
                    PLUGIN_NAME,
                    level=Qgis.Critical,
                )

        except Exception as e:
            QgsMessageLog.logMessage(
                f"レイヤー追加エラー: {str(e)}", PLUGIN_NAME, level=Qgis.Critical
            )

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
