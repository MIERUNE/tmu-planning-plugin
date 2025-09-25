from PyQt5.QtGui import QColor
from qgis.core import Qgis, QgsCoordinateReferenceSystem, QgsMessageLog, QgsVectorLayer

from ..connect import PLUGIN_NAME, UmiShiruApiClient
from .coastline_settings import COASTLINE_STYLE


class CoastlineAlgorithm:
    """
    海岸線データの取得と処理を行うアルゴリズムクラス
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
        # APIクライアントを作成
        client = UmiShiruApiClient(api_key)

        # APIパラメータ設定
        params = {
            "f": "geojson",
            "geometry": f"{bounds['min_lon']},{bounds['min_lat']},{bounds['max_lon']},{bounds['max_lat']}",
        }

        # 海岸線データを取得
        return client.request("coastline", params)

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
