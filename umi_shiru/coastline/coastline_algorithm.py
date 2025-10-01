import glob
import json
import os
import shutil
import tempfile
import zipfile
from typing import Dict, List, Optional

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

    # ========================================
    # workflowから呼び出されるパブリックメソッド
    # ========================================

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
        海岸線データをAPIから取得（単一取得）
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

    def fetch_coastline_data_divided(
        self, api_key: str, bounds: dict, division_count: int, display_name: str
    ) -> str:
        """
        海岸線データをAPIから取得（分割取得）
        Args:
            api_key (str): 海しるAPIキー
            bounds (dict): 境界範囲
            division_count (int): 分割数
            display_name (str): 表示名（ログ用）
        Returns:
            str: 取得・処理後のGeoJSON文字列
        """
        QgsMessageLog.logMessage(
            f"市区町村「{display_name}」はデータ数が多いため、分割してデータを取得します",
            PLUGIN_NAME,
            level=Qgis.Info,
        )
        # bboxを最適な方向に分割して取得
        bbox_list = self._split_bbox_optimally(bounds, division_count)
        return self._fetch_multiple_coastline_data(api_key, bbox_list, display_name)

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

    # ========================================
    # プライベートメソッド - bbox分割関連
    # ========================================

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

    # ========================================
    # プライベートメソッド - データ処理関連
    # ========================================

    def _fetch_multiple_coastline_data(
        self, api_key: str, bbox_list: List[dict], display_name: str
    ) -> str:
        """
        複数のbboxから海岸線データを取得してマージ
        Args:
            api_key (str): 海しるAPIキー
            bbox_list (List[dict]): bboxのリスト
            display_name (str): 表示名（ログ用）
        Returns:
            str: マージ・重複削除後のGeoJSON文字列
        """
        geojson_list = []

        for i, bbox in enumerate(bbox_list):
            geojson_data = self.fetch_coastline_data(api_key=api_key, bounds=bbox)

            if geojson_data:
                geojson_list.append(geojson_data)
            else:
                QgsMessageLog.logMessage(
                    f"分割範囲 {i+1}/{len(bbox_list)} のデータ取得に失敗しました",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )

        if not geojson_list:
            return ""

        # データをマージ
        merged_data = self._merge_geojson_features(geojson_list)

        # 重複を削除
        final_data = self._remove_duplicate_features(merged_data)

        QgsMessageLog.logMessage(
            f"市区町村「{display_name}」: 分割取得完了（{len(bbox_list)}個の範囲をマージ）",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

        return final_data

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
                except Exception as e:
                    failed_count += 1
                    QgsMessageLog.logMessage(
                        f"GeoJSON 処理エラー ({i+1}/{len(geojson_list)}): {str(e)}",
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
        except Exception as e:
            QgsMessageLog.logMessage(
                f"重複削除処理: 予期しないエラーが発生しました: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return json.dumps({"type": "FeatureCollection", "features": []})

        features = geojson_obj.get("features", [])

        # 地物の座標をキーとして重複を検出・削除
        unique_features = []
        seen_coordinates = set()
        failed_features = 0

        for feature in features:
            try:
                # 座標列を文字列化してハッシュ可能にする
                coordinates_str = json.dumps(
                    feature.get("geometry", {}).get("coordinates", []), sort_keys=True
                )

                if coordinates_str not in seen_coordinates:
                    seen_coordinates.add(coordinates_str)
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
