from qgis.core import (
    Qgis,
    QgsMessageLog,
)

from ..estat.connect import PLUGIN_NAME
from ..estat.get_dataset_id import GetDatasetId
from ..estat.population_mesh_algorithm import PopulationMeshAlgorithm


class PopulationMeshWorkflow:
    """人口メッシュデータの取得・可視化のためのワークフロー"""

    def __init__(self, iface):
        self.iface = iface
        self.algorithm = PopulationMeshAlgorithm(iface)
        self.dataset_id_getter = GetDatasetId(iface)

    def execute(self, api_key: str, municipality_code: str) -> bool:
        """
        指定されたアルゴリズムを実行し、レイヤーをQGISに追加する
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """

        # 自治体コードから複数のメッシュコードとデータセットIDを取得
        dataset_id_dict = self.dataset_id_getter.fetch_dataset_ids_for_municipality(
            municipality_code, api_key
        )

        if not dataset_id_dict:
            QgsMessageLog.logMessage(
                f"自治体コード '{municipality_code}' のデータセットIDが取得できませんでした。",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )
            return False

        QgsMessageLog.logMessage(
            f"取得したデータセット数: {len(dataset_id_dict)}",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

        # 各メッシュコードに対してレイヤーを作成
        added_layers = []
        failed_mesh_codes = []

        for mesh_code, stats_data_id in dataset_id_dict.items():
            QgsMessageLog.logMessage(
                f"メッシュコード '{mesh_code}' の処理を開始します...",
                PLUGIN_NAME,
                level=Qgis.Info,
            )

            added_layer = self.algorithm.create_population_mesh_layer(
                api_key, mesh_code, stats_data_id
            )

            if added_layer is not None:
                added_layers.append(added_layer)
                QgsMessageLog.logMessage(
                    f"メッシュコード '{mesh_code}' のレイヤー '{added_layer.name()}' を追加しました。",
                    PLUGIN_NAME,
                    level=Qgis.Success,
                )
            else:
                failed_mesh_codes.append(mesh_code)
                QgsMessageLog.logMessage(
                    f"メッシュコード '{mesh_code}' のレイヤー追加に失敗しました。",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )

        # 処理結果のログ出力
        success_count = len(added_layers)
        total_count = len(dataset_id_dict)

        QgsMessageLog.logMessage(
            f"ワークフロー完了: {success_count}/{total_count} レイヤーを追加しました。",
            PLUGIN_NAME,
            level=Qgis.Success if success_count > 0 else Qgis.Warning,
        )

        if failed_mesh_codes:
            QgsMessageLog.logMessage(
                f"失敗したメッシュコード: {', '.join(failed_mesh_codes)}",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )

        # 少なくとも1つのレイヤーが追加されていればTrue
        return success_count > 0
