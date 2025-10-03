import hashlib
import json
import os
import tempfile
from typing import Dict, List, Optional

from PyQt5.QtCore import QTimer
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
        # 作成した一時ファイルのリスト
        self._temp_files = {}
        # 削除予定のレイヤーIDを一時的に保持するリスト
        self._layers_to_be_removed = []

        # レイヤー削除時のシグナル接続
        self._setup_signals()

    # ========================================
    # workflowから呼び出されるパブリックメソッド
    # ========================================

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
        # bboxを最適な方向に分割
        bbox_list = self._split_bbox_optimally(bounds, division_count)

        # 各分割範囲からデータを取得
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

        return final_data

    def create_coastline_layer(
        self, geojson_data: str, layer_name: str = "海岸線"
    ) -> QgsVectorLayer:
        """
        GeoJSONデータからQGISレイヤーを作成（一時ファイル使用）
        Args:
            geojson_data (str): GeoJSON文字列
            layer_name (str): レイヤー名
        Returns:
            QgsVectorLayer: 作成されたレイヤー（失敗時はNone）
        """
        # 一時ファイルにGeoJSONを保存
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".geojson", delete=False, encoding="utf-8"
        )

        try:
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
            self._apply_coastline_style(layer)

            # レイヤーに一時ファイルパスを記録（デバッグ用）
            QgsMessageLog.logMessage(
                f"海岸線レイヤー用一時ファイル作成: {temp_file_path}",
                PLUGIN_NAME,
                level=Qgis.Info,
            )

            # 一時ファイルパスをレイヤーIDと関連付けて保存
            self._temp_files[layer.id()] = temp_file_path

            return layer

        except Exception as e:
            # エラー時は一時ファイルをクリーンアップ
            if "temp_file_path" in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise Exception(f"海岸線レイヤーの作成に失敗: {str(e)}")
        finally:
            if not temp_file.closed:
                temp_file.close()

    def _on_layers_will_be_removed(self, layer_ids: list):
        """
        レイヤーが削除される直前に、対象の一時ファイルパスを特定する
        Args:
            layer_ids (list): 削除される予定のレイヤーIDリスト
        """
        # 削除対象のレイヤーIDをリストに追加
        self._layers_to_be_removed.extend(layer_ids)
        QgsMessageLog.logMessage(
            f"削除予定レイヤーを記録: {layer_ids}",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

    def _on_layers_removed(self):
        """
        レイヤーが完全に削除された後に、タイマーを使って一時ファイルを削除する
        """
        for layer_id in self._layers_to_be_removed:
            if layer_id in self._temp_files:
                temp_file_path = self._temp_files[layer_id]

                QTimer.singleShot(
                    0,  # タイムアウト0msは「できるだけ早く、ただし現在のイベントの後で」という意味
                    lambda p=temp_file_path, lid=layer_id: self._delete_temp_file(
                        p, lid
                    ),
                )

        self._layers_to_be_removed.clear()

    def _delete_temp_file(self, file_path: str, layer_id: str):
        """
        一時ファイルを実際に削除するメソッド
        Args:
            file_path (str): 削除する一時ファイルのパス
            layer_id (str): レイヤーID
        """
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                QgsMessageLog.logMessage(
                    f"レイヤー削除に伴い一時ファイルを削除: {file_path}",
                    PLUGIN_NAME,
                    level=Qgis.Info,
                )

            if layer_id in self._temp_files:
                del self._temp_files[layer_id]
        except Exception as e:
            QgsMessageLog.logMessage(
                f"レイヤー削除時の一時ファイル削除エラー: {file_path} - {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )

    def _setup_signals(self):
        """
        QGISシグナルの接続を設定
        """
        try:
            from qgis.core import QgsProject

            project = QgsProject.instance()

            # 2つのシグナルを接続
            project.layersWillBeRemoved.connect(self._on_layers_will_be_removed)  # type: ignore
            project.layersRemoved.connect(self._on_layers_removed)  # type: ignore

            QgsMessageLog.logMessage(
                "レイヤー削除追跡シグナルを接続しました",
                PLUGIN_NAME,
                level=Qgis.Info,
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"シグナル接続エラー: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )

    # ===========================================================
    # fetch_coastline_data_dividedから呼び出されるプライベートメソッド
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
