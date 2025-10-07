"""
人口メッシュ（1km）データの取得機能モジュール
"""

import io
import tempfile
import urllib.parse
import zipfile
from pathlib import Path
from typing import Optional

import requests
from qgis.core import (
    Qgis,
    QgsField,
    QgsGraduatedSymbolRenderer,
    QgsMessageLog,
    QgsProject,
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

    # メッシュコード
    # TODO : 指定した自治体でIDを取得できるようにする
    mesh_number = "6441"  # 1kmメッシュコード

    def __init__(self, iface):
        self.iface = iface
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dataset_id = GetDatasetId(iface)

    def _get_mesh_data(self, mesh_code: str) -> Optional[str]:
        """メッシュ形状データをダウンロードして取得"""
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

        # メッシュ形状データのダウンロード
        mesh_data = requests.get(mesh_request_url, timeout=60)
        # エラーチェック
        mesh_data.raise_for_status()
        zip_data = io.BytesIO(mesh_data.content)

        # ダウンロードしたZIPファイルを一時ディレクトリに展開
        with zipfile.ZipFile(zip_data, "r") as zip_ref:
            zip_ref.extractall(self.temp_dir.name)

        # 展開したファイルの中からシェープファイル（.shp）を探す
        temp_dir_path = Path(self.temp_dir.name)
        shapefiles = list(temp_dir_path.glob("*.shp"))

        if not shapefiles:
            QgsMessageLog.logMessage(
                "展開されたZIPファイル内にシェープファイルが見つかりませんでした。",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return None

        # 最初のシェープファイルのフルパスを文字列として返す
        return str(shapefiles[0])

    def create_single_population_layer(
        self, api_key: str, mesh_code: str, stats_data_id: str
    ) -> Optional[QgsVectorLayer]:
        """人口メッシュデータの取得
        Args:
            api_key (str): e-Stat APIキー
            mesh_code (str): 1kmメッシュコード
            stats_data_id (str): e-StatのデータセットID
        Returns:
            QgsVectorLayer: 追加に成功した場合はレイヤーオブジェクト、失敗した場合はNone
        """
        try:
            # メッシュ形状データのダウンロードとシェープファイルのパス取得
            shp_path = self._get_mesh_data(mesh_code)
            if not shp_path:
                return None

            # QGISにレイヤーとして追加
            # TODO : レイヤー名指定した自治体名+人口メッシュにする
            layer_name = f"人口メッシュ_({mesh_code})"

            population_mesh_layer = QgsVectorLayer(str(shp_path), layer_name, "ogr")
            if not population_mesh_layer.isValid():
                QgsMessageLog.logMessage(
                    "シェープファイルからレイヤーを作成できませんでした。",
                    PLUGIN_NAME,
                    level=Qgis.Critical,
                )
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

            # データの結合
            join_field_name = "population"
            key_field_name = (
                "KEY_CODE"  # e-Statのシェープファイルのメッシュコードのフィールド名
            )

            # レイヤーの編集を開始
            population_mesh_layer.startEditing()

            if population_mesh_layer.fields().indexFromName(join_field_name) == -1:
                population_mesh_layer.dataProvider().addAttributes(
                    [QgsField(join_field_name, QVariant.Int)]
                )
                population_mesh_layer.updateFields()

            join_field_idx = population_mesh_layer.fields().indexFromName(
                join_field_name
            )
            updated_count = 0
            for feature in population_mesh_layer.getFeatures():
                mesh_code = feature[key_field_name]
                if mesh_code in population_dict:
                    population_value = population_dict[mesh_code]
                    population_mesh_layer.changeAttributeValue(
                        feature.id(), join_field_idx, population_value
                    )
                    updated_count += 1

            population_mesh_layer.commitChanges()
            QgsMessageLog.logMessage(
                f"人口データを{updated_count}件更新しました。",
                PLUGIN_NAME,
                level=Qgis.Info,
            )
            return population_mesh_layer

            # if not population_mesh_layer.commitChanges():
            #     QgsMessageLog.logMessage(
            #         "人口メッシュレイヤーのコミットに失敗しました。ロールバックを実行します。",
            #         PLUGIN_NAME,
            #         level=Qgis.Critical,
            #     )
            #     population_mesh_layer.rollBack()
            #     return None

            # # 可視化（段階分けレンダリング）
            # target_field = join_field_name

            # # 5段階に分類して色分け
            # class_count = 5

            # renderer = QgsGraduatedSymbolRenderer(target_field)
            # renderer.setClassAttribute(target_field)

            # color_ramp = QgsStyle.defaultStyle().colorRamp("Viridis")
            # renderer.setSourceColorRamp(color_ramp)

            # renderer.updateClasses(
            #     population_mesh_layer, QgsGraduatedSymbolRenderer.Jenks, class_count
            # )

            # population_mesh_layer.setRenderer(renderer)
            # population_mesh_layer.triggerRepaint()  # 地図を再描画

            # return population_mesh_layer
        except Exception as e:
            QgsMessageLog.logMessage(
                f"予期せぬエラーが発生しました: {e}", PLUGIN_NAME, level=Qgis.Critical
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

        # 最終的なレイヤーをプロジェクトに追加
        QgsProject.instance().addMapLayer(merged_layer)
        return merged_layer