"""
人口メッシュ（1km）データの取得機能モジュール
"""

import io
import tempfile
import urllib.parse
import zipfile
from pathlib import Path
from typing import Optional

import processing
import requests
from qgis.core import (
    Qgis,
    QgsFeature,
    QgsField,
    QgsMessageLog,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant

from ..utils.settings import PLUGIN_NAME
from .connect import (
    MESH_SHAPE_DOWNLOAD_URL,
    POPULATION_MESH_API_ENDPOINT,
)


class PopulationMeshAlgorithm:
    """人口メッシュデータ取得クラス"""

    def __init__(self, iface):
        self.iface = iface
        self.temp_dir = tempfile.TemporaryDirectory()

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
        QgsMessageLog.logMessage(
            f"メッシュ形状データのダウンロードURL: {mesh_request_url}",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

        # メッシュ形状データのダウンロード
        mesh_data = requests.get(mesh_request_url, timeout=60)
        # エラーチェック
        mesh_data.raise_for_status()
        zip_data = io.BytesIO(mesh_data.content)

        # メッシュコードごとに専用のサブディレクトリを作成
        temp_dir_path = Path(self.temp_dir.name)
        mesh_dir = temp_dir_path / f"mesh_{mesh_code}"
        mesh_dir.mkdir(exist_ok=True)

        # ダウンロードしたZIPファイルを一時ディレクトリに展開
        with zipfile.ZipFile(zip_data, "r") as zip_ref:
            zip_ref.extractall(mesh_dir)

        # 展開したファイルの中からシェープファイル（.shp）を探す
        shapefiles = list(mesh_dir.glob("*.shp"))

        if not shapefiles:
            QgsMessageLog.logMessage(
                "展開されたZIPファイル内にシェープファイルが見つかりませんでした。",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return None

        # 最初のシェープファイルのフルパスを文字列として返す
        QgsMessageLog.logMessage(
            f"シェープファイルのパス: {shapefiles[0]}",
            PLUGIN_NAME,
            level=Qgis.Info,
        )
        return str(shapefiles[0])

    def create_population_mesh_layer(
        self, api_key: str, mesh_code: str, stats_data_id: str
    ) -> Optional[QgsVectorLayer]:
        """人口メッシュデータの取得とQGISへのレイヤー追加
        Args:
            api_key (str): e-Stat APIキー
            mesh_code (str): 取得対象のメッシュコード（例: "6441"）
            stats_data_id (str): データセットID
        Returns:
            Optional[QgsVectorLayer]: 追加された人口メッシュレイヤー。失敗した場合はNone。
        """
        # メッシュ形状データのダウンロードとシェープファイルのパス取得
        shp_path = self._get_mesh_data(mesh_code)
        if not shp_path:
            return None

        layer_name = f"人口メッシュ_1km_{mesh_code}"

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

        # 一時レイヤーを作成
        temp_layer = QgsVectorLayer("None", "temp_population", "memory")
        provider = temp_layer.dataProvider()
        provider.addAttributes(
            [
                QgsField("mesh_code", QVariant.String),
                QgsField("population", QVariant.Int),
            ]
        )
        temp_layer.updateFields()

        # データを追加
        features = []
        for mesh_code_key, pop_value in population_dict.items():
            feature = QgsFeature()
            feature.setAttributes([mesh_code_key, pop_value])
            features.append(feature)

        provider.addFeatures(features)

        # プロセシングツールで結合
        result = processing.run(
            "native:joinattributestable",
            {
                "INPUT": population_mesh_layer,
                "FIELD": "KEY_CODE",
                "INPUT_2": temp_layer,
                "FIELD_2": "mesh_code",
                "FIELDS_TO_COPY": ["population"],
                "METHOD": 1,
                "DISCARD_NONMATCHING": False,
                "PREFIX": "",
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )

        population_mesh_layer = result["OUTPUT"]
        population_mesh_layer.setName(layer_name)

        # 結合結果の確認
        # デバッグ用に結合結果の件数をログに出力
        joined_count = result.get("JOINED_COUNT", 0)
        unjoinable_count = result.get("UNJOINABLE_COUNT", 0)

        QgsMessageLog.logMessage(
            f"結合完了: {joined_count}件成功, {unjoinable_count}件不一致",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

        return population_mesh_layer
