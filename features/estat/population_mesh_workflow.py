from typing import Literal

from qgis.core import (
    Qgis,
    QgsMessageLog,
)

from .algorithms.get_dataset_id import GetDatasetId
from .algorithms.merge_algorithm import MergePopulationMeshLayers
from .algorithms.population_mesh_algorithm import PopulationMeshAlgorithm
from ...utils.settings import PLUGIN_NAME


class PopulationMeshWorkflow:
    """人口メッシュデータの取得・可視化のためのワークフロー"""

    def __init__(self, iface):
        self.iface = iface
        self.algorithm = PopulationMeshAlgorithm(iface)
        self.merge_algorithm = MergePopulationMeshLayers(iface)
        self.dataset_id_getter = GetDatasetId(iface)

    def _fetch_dataset_ids(
        self, municipality_code: str, api_key: str, mesh_type: Literal["3rd", "4th"]
    ) -> dict:
        """データセットIDを取得"""
        dataset_id_dict = self.dataset_id_getter.fetch_dataset_ids_for_municipality(
            municipality_code, api_key, mesh_type
        )

        if not dataset_id_dict:
            QgsMessageLog.logMessage(
                f"自治体コード '{municipality_code}' のデータセットIDが取得できませんでした。",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Warning,
            )
            return {}

        QgsMessageLog.logMessage(
            f"取得したデータセット数: {len(dataset_id_dict)}",
            PLUGIN_NAME,
            level=Qgis.MessageLevel.Info,
        )

        return dataset_id_dict

    def _create_population_layers(
        self, api_key: str, dataset_id_dict: dict, mesh_type: Literal["3rd", "4th"]
    ) -> list:
        """
        各メッシュコードに対してレイヤーを作成

        Args:
            api_key: e-Stat APIキー
            dataset_id_dict: {メッシュコード: データセットID} の辞書
            mesh_type: メッシュタイプ

        Returns:
            list: 成功したレイヤーの情報リスト
        """
        added_layers = []

        # 複数メッシュに対してfor文で処理
        for mesh_code, stats_data_id in dataset_id_dict.items():
            QgsMessageLog.logMessage(
                f"メッシュコード '{mesh_code}' の処理を開始...",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Info,
            )

            # アルゴリズムに個別メッシュの処理を委譲
            population_mesh_layer = self.algorithm.create_population_mesh_layer(
                api_key, mesh_code, stats_data_id, mesh_type
            )

            if population_mesh_layer is not None:
                added_layers.append(
                    {
                        "layer": population_mesh_layer,
                        "mesh_code": mesh_code,
                        "stats_data_id": stats_data_id,
                    }
                )
                QgsMessageLog.logMessage(
                    f"メッシュコード '{mesh_code}' のレイヤー '{population_mesh_layer.name()}' を追加",
                    PLUGIN_NAME,
                    level=Qgis.MessageLevel.Success,
                )
            else:
                QgsMessageLog.logMessage(
                    f"メッシュコード '{mesh_code}' のレイヤー追加に失敗",
                    PLUGIN_NAME,
                    level=Qgis.MessageLevel.Warning,
                )

        return added_layers

    def execute(
        self,
        api_key: str,
        municipality_code: str,
        municipality_name: str,
        mesh_type: Literal["3rd", "4th"],
    ) -> bool:
        """
        指定されたアルゴリズムを実行し、レイヤーをQGISに追加する
        Args:
            api_key (str): e-Stat APIキー
            municipality_code (str): 自治体コード（例: "01100" 札幌市）
            municipality_name (str): 自治体名（例: "札幌市"）
            mesh_type (Literal["3rd", "4th"]): メッシュタイプ
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """

        # 1. 自治体コードからデータセットIDを取得
        dataset_id_dict = self._fetch_dataset_ids(municipality_code, api_key, mesh_type)

        if not dataset_id_dict:
            return False

        # 2. 各メッシュコードの人口メッシュレイヤーを作成
        added_population_layers = self._create_population_layers(
            api_key, dataset_id_dict, mesh_type
        )

        # 3. レイヤーをマージ
        merged_layer = self.merge_algorithm.merge_population_mesh_layers(
            added_population_layers, municipality_name, mesh_type, remove_originals=True
        )
        return merged_layer is not None
