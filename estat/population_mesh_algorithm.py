"""
人口メッシュ（1km）データの取得機能モジュール
"""

import os
import shutil
import tempfile
import time
import traceback
import urllib.parse
import zipfile
from typing import Optional

import requests
from qgis.core import (
    Qgis,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsGraduatedSymbolRenderer,
    QgsMessageLog,
    QgsStyle,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant

from .connect import (
    MESH_SHAPE_DOWNLOAD_URL,
    PLUGIN_NAME,
    POPULATION_MESH_API_ENDPOINT,
)
from .get_dataset_id import GetDatasetId


class PopulationMeshAlgorithm:
    """人口メッシュデータ取得クラス"""

    def __init__(self, iface):
        self.iface = iface
        self.dataset_id = GetDatasetId(iface)

    def _get_mesh_data(self, mesh_code: str) -> Optional[QgsGeometry]:
        """メッシュ形状データをダウンロードしてジオメトリを取得"""
        # パラメーター
        mesh_request_params = {
            "dlserveyId": "S",
            "code": mesh_code,
            "coordSys": "1",
            "format": "shape",
            "downloadType": "5",
        }
        encode_params = urllib.parse.urlencode(mesh_request_params)
        mesh_request_url = f"{MESH_SHAPE_DOWNLOAD_URL}?{encode_params}"

        temp_dir = None

        try:
            mesh_data = requests.get(mesh_request_url, timeout=60)
            mesh_data.raise_for_status()

            # 一時ディレクトリを作成（手動削除に変更）
            temp_dir = tempfile.mkdtemp()

            # ZIPファイルを一時ファイルに保存
            zip_file_path = os.path.join(temp_dir, f"mesh_{mesh_code}.zip")
            with open(zip_file_path, "wb") as zip_file:
                zip_file.write(mesh_data.content)

            # ZIPファイルを展開
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(zip_file_path, "r") as zf:
                zf.extractall(extract_dir)

            # シェープファイルを探して読み込む
            result_geometry = None

            for root, _, files in os.walk(extract_dir):
                for filename in files:
                    if filename.endswith(".shp"):
                        shp_path = os.path.join(root, filename)
                        temp_layer = QgsVectorLayer(shp_path, "temp", "ogr")

                        if temp_layer.isValid() and temp_layer.featureCount() > 0:
                            # 最初のフィーチャーのジオメトリをコピー
                            feature = next(temp_layer.getFeatures())
                            result_geometry = QgsGeometry(feature.geometry())

                            temp_layer = None
                            break

                if result_geometry:
                    break

            # ジオメトリが取得できたかチェック
            if result_geometry is None:
                QgsMessageLog.logMessage(
                    f"メッシュコード {mesh_code} のジオメトリが見つかりませんでした",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )
                return None

            QgsMessageLog.logMessage(
                f"メッシュコード {mesh_code} のジオメトリ取得成功",
                PLUGIN_NAME,
                level=Qgis.Info,
            )
            return result_geometry

        except requests.RequestException as e:
            error_traceback = traceback.format_exc()
            QgsMessageLog.logMessage(
                f"メッシュデータDLエラー (コード: {mesh_code}): {str(e)}\n詳細:\n{error_traceback}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return None

        except Exception as e:
            error_traceback = traceback.format_exc()
            QgsMessageLog.logMessage(
                f"ジオメトリ取得エラー (コード: {mesh_code}): {str(e)}\n詳細:\n{error_traceback}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return None

        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    time.sleep(0.1)  # ファイルハンドル解放待機
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as cleanup_error:
                    QgsMessageLog.logMessage(
                        f"一時ファイル削除警告 (コード: {mesh_code}): {cleanup_error}",
                        PLUGIN_NAME,
                        level=Qgis.Warning,
                    )

    def create_single_population_layer(
        self, api_key: str, mesh_code: str, stats_data_id: str
    ) -> Optional[QgsVectorLayer]:
        """単一のメッシュのジオメトリと人口データからメモリレイヤーを作成する
        Args:
            api_key (str): e-Stat APIキー
            mesh_code (str): メッシュコード
            stats_data_id (str): データセットID
        Returns:
            QgsVectorLayer: 作成したレイヤー、または None（失敗時
        """
        try:
            # メッシュのジオメトリを取得
            mesh_geometry = self._get_mesh_data(mesh_code)
            if not mesh_geometry:
                return None

            # 人口データの取得と整形
            # パラメーター
            population_mesh_url_params = {
                "appId": api_key,
                "lang": "J",
                "statsDataId": stats_data_id,
                "cdCat01": "0010",  # 総人口
            }
            encoded_params = urllib.parse.urlencode(population_mesh_url_params)
            population_mesh_url = f"{POPULATION_MESH_API_ENDPOINT}?{encoded_params}"

            response_pop = requests.get(population_mesh_url, timeout=60)
            response_pop.raise_for_status()

            # 取得したJSONデータをパース
            json_data = response_pop.json()
            stats_values = json_data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"][
                "VALUE"
            ]

            # {メッシュコード: 人口} の辞書を作成
            population_dict = {
                item["@area"]: int(item["$"])
                for item in stats_values
                if "$" in item and str(item["$"]).isnumeric()
            }
            # メモリレイヤーの準備
            layer = QgsVectorLayer(
                "Polygon?crs=EPSG:4326", f"temp_mesh_{mesh_code}", "memory"
            )
            provider = layer.dataProvider()
            fields = QgsFields()
            fields.append(QgsField("KEY_CODE", QVariant.String))
            fields.append(QgsField("population", QVariant.Int))
            provider.addAttributes(fields)
            layer.updateFields()

            # ジオメトリと属性を持つフィーチャーを作成
            for area_code, population in population_dict.items():
                feature = QgsFeature()
                # ジオメトリは最初に取得したメッシュ全体の形状を使いまわす
                # (e-Statの仕様上、1メッシュ内の複数エリアでもジオメトリは同じはず)
                feature.setGeometry(mesh_geometry)
                feature.setAttributes([area_code, population])
                provider.addFeature(feature)

            QgsMessageLog.logMessage(
                f"メッシュコード {mesh_code} のメモリレイヤー作成完了",
                PLUGIN_NAME,
                level=Qgis.Info,
            )
            return layer

        except Exception as e:
            QgsMessageLog.logMessage(
                f"単一レイヤー作成中の予期せぬエラー: {e}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return None

    def merge_population_layers(
        self, layers_to_merge: list[QgsVectorLayer], merged_layer_name: str
    ) -> Optional[QgsVectorLayer]:
        """複数の人口メッシュレイヤーを結合して1つのレイヤーにまとめる
        Args:
            layers (list[QgsVectorLayer]): 結合するレイヤーのリスト
            merged_layer_name (str): 結合後のレイヤー名
        Returns:
            QgsVectorLayer: 結合に成功した場合はレイヤーオブジェクト、失敗した場合はNone
        """
        try:
            if not layers_to_merge:
                QgsMessageLog.logMessage(
                    "結合するレイヤーが指定されていません。",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )
                return None

            # 最初のレイヤーをベースにして結合
            source_layer = layers_to_merge[0]
            target_crs = source_layer.crs()
            target_fields = source_layer.fields()

            # 結果を格納する「メモリレイヤー」を作成
            merged_layer = QgsVectorLayer(
                f"Polygon?crs={target_crs.toWkt()}", merged_layer_name, "memory"
            )
            provider = merged_layer.dataProvider()
            provider.addAttributes(target_fields)
            merged_layer.updateFields()

            # すべてのレイヤーから地物をコピー
            features_to_add = []
            for layer in layers_to_merge:
                for feature in layer.getFeatures():
                    features_to_add.append(feature)
            provider.addFeatures(features_to_add)
            merged_layer.updateExtents()

            # 可視化（段階分けレンダリング）
            target_field = "population"
            renderer = QgsGraduatedSymbolRenderer(target_field)
            renderer.setClassAttribute(target_field)
            color_ramp = QgsStyle.defaultStyle().colorRamp("Viridis")
            if color_ramp:
                renderer.setSourceColorRamp(color_ramp)
            renderer.updateClasses(merged_layer, QgsGraduatedSymbolRenderer.Jenks, 5)
            merged_layer.setRenderer(renderer)

            QgsMessageLog.logMessage(
                f"レイヤー「{merged_layer}」の作成が完了しました。",
                PLUGIN_NAME,
                level=Qgis.Success,
            )
            return merged_layer
        except Exception as e:
            error_traceback = traceback.format_exc()
            QgsMessageLog.logMessage(
                f"レイヤー結合中の予期せぬエラー: {str(e)}\n詳細:\n{error_traceback}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return None
