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


class PopulationMeshAlgorithm:
    """人口メッシュデータ取得クラス"""

    # メッシュコード
    # TODO : 指定した自治体でIDを取得できるようにする
    mesh_number = "6441"  # 1kmメッシュコード

    def __init__(self, iface):
        self.iface = iface
        self.temp_dir = tempfile.TemporaryDirectory()

    def _get_mesh_data(self) -> Optional[str]:
        """メッシュ形状データをダウンロードして取得"""
        # パラメーター
        mesh_request_params = {
            "dlserveyId": "S",
            "code": "6441",
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

    def create_population_mesh_layer(self, api_key: str) -> Optional[QgsVectorLayer]:
        """人口メッシュデータの取得とQGISへのレイヤー追加
        Args:
            api_key (str): e-Stat APIキー
        Returns:

        """

        try:
            # メッシュ形状データのダウンロードとシェープファイルのパス取得
            shp_path = self._get_mesh_data()
            if not shp_path:
                return None

            # QGISにレイヤーとして追加
            # TODO : レイヤー名指定した自治体名+人口メッシュにする
            layer_name = "人口メッシュ_1km"

            population_mesh_layer = QgsVectorLayer(str(shp_path), layer_name, "ogr")
            if not population_mesh_layer.isValid():
                QgsMessageLog.logMessage(
                    "シェープファイルからレイヤーを作成できませんでした。",
                    PLUGIN_NAME,
                    level=Qgis.Critical,
                )
                return None

            QgsProject.instance().addMapLayer(population_mesh_layer)
            QgsMessageLog.logMessage(
                f"レイヤー「{layer_name}」を追加しました。",
                PLUGIN_NAME,
                level=Qgis.Info,
            )

            # 人口データの取得と整形)

            # 取得したいデータのID（人口メッシュデータ）
            # TODO : 指定した自治体でIDを取得できるようにする
            stats_data_id = "8003007181"
            # TODO : APIキーを引数で受け取るようにする
            api_key = ""  # e-StatのAPIキー
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

            if not population_mesh_layer.commitChanges():
                QgsMessageLog.logMessage(
                    "人口メッシュレイヤーのコミットに失敗しました。ロールバックを実行します。",
                    PLUGIN_NAME,
                    level=Qgis.Critical,
                )
                population_mesh_layer.rollBack()
                return None

            # 可視化（段階分けレンダリング）
            target_field = join_field_name

            # 5段階に分類して色分け
            class_count = 5

            renderer = QgsGraduatedSymbolRenderer(target_field)
            renderer.setClassAttribute(target_field)

            color_ramp = QgsStyle.defaultStyle().colorRamp("Viridis")
            renderer.setSourceColorRamp(color_ramp)

            renderer.updateClasses(
                population_mesh_layer, QgsGraduatedSymbolRenderer.Jenks, class_count
            )

            population_mesh_layer.setRenderer(renderer)
            population_mesh_layer.triggerRepaint()  # 地図を再描画

            return population_mesh_layer

        except requests.exceptions.RequestException as e:
            QgsMessageLog.logMessage(
                f"エラー: データ取得に失敗しました。URLやAPIキー、ネットワーク接続を確認してください。\n{e}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return None
        except Exception as e:
            QgsMessageLog.logMessage(
                f"予期せぬエラーが発生しました: {e}", PLUGIN_NAME, level=Qgis.Critical
            )
            return None
