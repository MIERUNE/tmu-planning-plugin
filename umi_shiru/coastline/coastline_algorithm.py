import glob
import os
import shutil
import tempfile
import zipfile
from typing import Dict, Optional

import requests
from PyQt5.QtGui import QColor
from qgis.core import Qgis, QgsCoordinateReferenceSystem, QgsMessageLog, QgsVectorLayer

from ..connect import PLUGIN_NAME, UmiShiruApiClient, build_estat_municipality_url
from .coastline_settings import COASTLINE_STYLE


class CoastlineAlgorithm:
    """
    海岸線データの取得と処理を行うアルゴリズムクラス
    """

    def __init__(self, iface):
        self.iface = iface

    def get_municipality_bbox(
        self, municipality_code: str
    ) -> Optional[Dict[str, float]]:
        """
        市区町村コードからe-Stat APIでポリゴンを取得し、bboxを計算

        Args:
            municipality_code (str): 5桁の市区町村コード

        Returns:
            dict: bbox座標 {'min_lon', 'min_lat', 'max_lon', 'max_lat'} または None
        """
        QgsMessageLog.logMessage(
            f"市区町村 {municipality_code} のbboxを取得中...",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

        # e-Stat API URL
        url = build_estat_municipality_url(municipality_code)

        temp_dir = tempfile.mkdtemp()
        try:
            # ZIPファイルをダウンロード
            QgsMessageLog.logMessage(
                "行政区域データをダウンロード中...", PLUGIN_NAME, level=Qgis.Info
            )
            response = requests.get(url, timeout=60)
            response.raise_for_status()

            zip_path = os.path.join(temp_dir, "municipality.zip")
            with open(zip_path, "wb") as f:
                f.write(response.content)

            # ZIPファイルを解凍
            extract_dir = os.path.join(temp_dir, "extracted")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # シェープファイルを検索
            shp_files = glob.glob(
                os.path.join(extract_dir, "**", "*.shp"), recursive=True
            )
            if not shp_files:
                QgsMessageLog.logMessage(
                    "シェープファイルが見つかりません", PLUGIN_NAME, level=Qgis.Critical
                )
                return None

            # 最初のシェープファイルからbboxを取得
            shp_path = shp_files[0]
            layer = QgsVectorLayer(
                shp_path, f"temp_municipality_{municipality_code}", "ogr"
            )

            if not layer.isValid():
                QgsMessageLog.logMessage(
                    "シェープファイルの読み込みに失敗", PLUGIN_NAME, level=Qgis.Critical
                )
                return None

            extent = layer.extent()
            bbox = {
                "min_lon": extent.xMinimum(),
                "min_lat": extent.yMinimum(),
                "max_lon": extent.xMaximum(),
                "max_lat": extent.yMaximum(),
            }

            QgsMessageLog.logMessage(
                f"bbox取得成功: {bbox}", PLUGIN_NAME, level=Qgis.Info
            )
            return bbox

        except Exception as e:
            error_msg = f"bbox取得エラー: {str(e)}"
            QgsMessageLog.logMessage(error_msg, PLUGIN_NAME, level=Qgis.Critical)
            return None
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def fetch_coastline_data(
        self, api_key: str, bounds: Dict[str, float]
    ) -> Optional[str]:
        """
        海岸線データをAPIから取得
        Args:
            api_key (str): 海しるAPIキー
            bounds (dict): 取得範囲の境界
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

    def create_coastline_layer(
        self, geojson_data: str, layer_name: str = "海岸線"
    ) -> QgsVectorLayer:
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

    def _apply_coastline_style(self, layer: QgsVectorLayer):
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
