"""
海しるAPIデータ取得・処理用の基底アルゴリズムクラス
"""

import hashlib
import json
import os
import tempfile
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from PyQt5.QtGui import QColor
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsMessageLog,
    QgsVectorLayer,
    QgsWkbTypes,
)

from ....utils.settings import PLUGIN_NAME
from ..client import UmiShiruApiClient
from ..settings.layer_settings import UmiShiruLayerSettings


class UmiShiruBaseAlgorithm(ABC):
    """
    海しるAPIデータの取得と処理を行う基底アルゴリズムクラス
    各データタイプ（海岸線、漁港区域等）で継承して使用
    """

    def __init__(self, iface, layer_settings: UmiShiruLayerSettings):
        self.iface = iface
        self.layer_settings = layer_settings

    # ========================================
    # 抽象メソッド（継承クラスで実装必須）
    # ========================================

    @abstractmethod
    def get_data_type_key(self) -> str:
        """
        connect.pyのAPI設定キーを返す
        Returns:
            str: "coastline", "fishing_port", "port_area" など
        """
        pass

    # ========================================
    # workflowから呼び出されるパブリックメソッド
    # ========================================

    def fetch_data(self, api_key: str, bounds: Dict[str, float]) -> Optional[str]:
        """
        APIからデータを取得（単一取得）
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

        return client.request(self.get_data_type_key(), params)

    def fetch_data_divided(
        self, api_key: str, bounds: dict, division_count: int
    ) -> str:
        """
        APIからデータを取得（分割取得）
        Args:
            api_key (str): 海しるAPIキー
            bounds (dict): 境界範囲
            division_count (int): 分割数
        Returns:
            str: 取得・処理後のGeoJSON文字列
        """
        # bboxを最適な方向に分割
        bbox_list = self._split_bbox_optimally(bounds, division_count)

        # 各分割範囲からデータを取得
        geojson_list = []
        for i, bbox in enumerate(bbox_list):
            geojson_data = self.fetch_data(api_key=api_key, bounds=bbox)

            if geojson_data:
                geojson_list.append(geojson_data)

        if not geojson_list:
            return ""

        # データをマージ
        merged_data = self._merge_geojson_features(geojson_list)

        # 重複を削除
        final_data = self._remove_duplicate_features(merged_data)

        return final_data

    def create_layer(
        self, geojson_data: str, layer_name: Optional[str] = None
    ) -> QgsVectorLayer:
        """
        GeoJSONデータからQGISレイヤーを作成（一時ファイル使用）
        Args:
            geojson_data (str): GeoJSON文字列
            layer_name (str): レイヤー名（Noneの場合はデフォルト名を使用）
        Returns:
            QgsVectorLayer: 作成されたレイヤー（失敗時は例外）
        """
        if layer_name is None:
            layer_name = self.layer_settings.get_default_layer_name()

        temp_file_path = None

        # 一時ファイルにGeoJSONを保存
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".geojson", delete=False, encoding="utf-8"
        )

        try:
            # GeoJSONデータを一時ファイルに書き込み
            temp_file.write(geojson_data)
            temp_file.flush()
            temp_file_path = temp_file.name
            temp_file.close()

            # 一時ファイルからベクターレイヤーを作成
            layer = QgsVectorLayer(temp_file_path, layer_name, "ogr")

            if not layer.isValid():
                raise Exception("ベクターレイヤーの作成に失敗しました")

            # CRSを設定
            crs = QgsCoordinateReferenceSystem("EPSG:4326")
            layer.setCrs(crs)

            # スタイルを適用
            self._apply_layer_style(layer)

            return layer

        except Exception as e:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            data_type = self.get_data_type_key()
            raise Exception(f"{data_type}レイヤーの作成に失敗: {str(e)}") from e
        finally:
            if not temp_file.closed:
                temp_file.close()

    # ===========================================================
    # fetch_data_dividedから呼び出されるプライベートメソッド
    # ===========================================================

    def _split_bbox_optimally(self, bbox: dict, divisions: int) -> List[dict]:
        """
        bboxの形状に基づいて最適な方向に分割
        Args:
            bbox (dict): 分割元のbbox
            divisions (int): 分割数
        Returns:
            List[dict]: 分割されたbboxのリスト
        """
        division_type = self._determine_optimal_division(bbox)

        if division_type == "vertical":
            return self._split_bbox_vertically(bbox, divisions)
        else:
            return self._split_bbox_horizontally(bbox, divisions)

    def _determine_optimal_division(self, bbox: dict) -> str:
        """
        bboxの形状に基づいて最適な分割方向を自動判定
        Args:
            bbox (dict): 境界範囲
        Returns:
            str: "vertical" または "horizontal"
        """
        width = bbox["max_lon"] - bbox["min_lon"]  # 経度幅
        height = bbox["max_lat"] - bbox["min_lat"]  # 緯度幅

        # 縦長なら縦分割、横長なら横分割
        return "vertical" if height > width else "horizontal"

    def _split_bbox_vertically(self, bbox: dict, divisions: int) -> List[dict]:
        """
        bboxを縦方向（緯度方向）に分割
        Args:
            bbox (dict): 分割元のbbox
            divisions (int): 分割数
        Returns:
            List[dict]: 分割されたbboxのリスト
        """
        lat_range = bbox["max_lat"] - bbox["min_lat"]
        lat_step = lat_range / divisions

        bbox_list = []
        for i in range(divisions):
            split_bbox = {
                "min_lon": bbox["min_lon"],
                "max_lon": bbox["max_lon"],
                "min_lat": bbox["min_lat"] + (i * lat_step),
                "max_lat": bbox["min_lat"] + ((i + 1) * lat_step),
            }
            bbox_list.append(split_bbox)

        return bbox_list

    def _split_bbox_horizontally(self, bbox: dict, divisions: int) -> List[dict]:
        """
        bboxを横方向（経度方向）に分割
        Args:
            bbox (dict): 分割元のbbox
            divisions (int): 分割数
        Returns:
            List[dict]: 分割されたbboxのリスト
        """
        lon_range = bbox["max_lon"] - bbox["min_lon"]
        lon_step = lon_range / divisions

        bbox_list = []
        for i in range(divisions):
            split_bbox = {
                "min_lon": bbox["min_lon"] + (i * lon_step),
                "max_lon": bbox["min_lon"] + ((i + 1) * lon_step),
                "min_lat": bbox["min_lat"],
                "max_lat": bbox["max_lat"],
            }
            bbox_list.append(split_bbox)

        return bbox_list

    def _merge_geojson_features(self, geojson_list: List[str]) -> str:
        """
        複数のGeoJSONをマージ
        Args:
            geojson_list (List[str]): GeoJSON文字列のリスト
        Returns:
            str: マージされたGeoJSON文字列
        """
        if not geojson_list:
            return json.dumps({"type": "FeatureCollection", "features": []})

        all_features = []
        failed_count = 0

        for i, geojson_str in enumerate(geojson_list):
            if geojson_str:
                try:
                    geojson_obj = json.loads(geojson_str)
                    features = geojson_obj.get("features", [])
                    all_features.extend(features)
                except json.JSONDecodeError as e:
                    failed_count += 1
                    QgsMessageLog.logMessage(
                        f"GeoJSON パース失敗 ({i+1}/{len(geojson_list)}): {str(e)}",
                        PLUGIN_NAME,
                        level=Qgis.Warning,
                    )

        if failed_count > 0:
            QgsMessageLog.logMessage(
                f"マージ処理: {failed_count}/{len(geojson_list)} 件の GeoJSON 処理に失敗しましたが、処理を継続します",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )

        merged_geojson = {"type": "FeatureCollection", "features": all_features}

        return json.dumps(merged_geojson)

    def _remove_duplicate_features(self, geojson_data: str) -> str:
        """
        重複する地物を削除
        Args:
            geojson_data (str): GeoJSON文字列
        Returns:
            str: 重複削除後のGeoJSON文字列
        """
        try:
            geojson_obj = json.loads(geojson_data)
        except json.JSONDecodeError as e:
            QgsMessageLog.logMessage(
                f"重複削除処理: GeoJSON パースに失敗しました: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return json.dumps({"type": "FeatureCollection", "features": []})

        features = geojson_obj.get("features", [])

        # 地物の座標をキーとして重複を検出・削除
        unique_features = []
        seen_coordinate_hashes = set()
        failed_features = 0

        for feature in features:
            try:
                coordinates = feature.get("geometry", {}).get("coordinates", [])
                coordinates_str = str(
                    sorted(coordinates)
                    if isinstance(coordinates, list)
                    else coordinates
                )
                coordinate_hash = hashlib.md5(
                    coordinates_str.encode("utf-8")
                ).hexdigest()

                if coordinate_hash not in seen_coordinate_hashes:
                    seen_coordinate_hashes.add(coordinate_hash)
                    unique_features.append(feature)
            except Exception as e:
                failed_features += 1
                QgsMessageLog.logMessage(
                    f"地物の座標処理でエラー: {str(e)}",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )

        if failed_features > 0:
            QgsMessageLog.logMessage(
                f"重複削除: {failed_features} 件の地物で座標処理に失敗しましたが、処理を継続します",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )

        deduplicated_geojson = {
            "type": "FeatureCollection",
            "features": unique_features,
        }

        return json.dumps(deduplicated_geojson)

    # ========================================
    # プライベートメソッド - UI関連
    # ========================================

    def _apply_layer_style(self, layer: QgsVectorLayer):
        """
        レイヤーにスタイルを適用
        """
        try:
            style_config = self.layer_settings.get_style_config()

            # スタイル設定
            symbol = layer.renderer().symbol()
            color = QColor(style_config["color"])
            symbol.setColor(color)

            # ジオメトリタイプに応じて適切なスタイルを適用
            geometry_type = layer.geometryType()

            if geometry_type == QgsWkbTypes.PolygonGeometry:
                # 面（Polygon）の場合
                symbol_layer = symbol.symbolLayer(0)
                if symbol_layer:
                    symbol_layer.setStrokeWidth(style_config["width"])
                    symbol_layer.setStrokeColor(color)
                    fill_color = QColor(color)
                    fill_color.setAlphaF(style_config["opacity"])
                    symbol_layer.setFillColor(fill_color)
            else:
                # 線（LineString）や点（Point）の場合
                symbol.setWidth(style_config["width"])

            symbol.setOpacity(style_config["opacity"])
            layer.triggerRepaint()

        except Exception as e:
            data_type = self.get_data_type_key()
            QgsMessageLog.logMessage(
                f"{data_type}スタイル適用エラー: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )
