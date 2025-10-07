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

    def execute(self, municipality_code: str, api_key: str) -> bool:
        """
        指定されたアルゴリズムを実行し、レイヤーをQGISに追加する
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            dataset_id_dict = self.dataset_id_getter.fetch_dataset_ids_for_municipality(
                municipality_code, api_key
            )

            if not dataset_id_dict:
                QgsMessageLog.logMessage(
                    "処理対象のデータセットIDが見つかりませんでした。",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )
                return False

            created_layers = 0

            for mesh_code, stats_data_id in dataset_id_dict.items():
                QgsMessageLog.logMessage(
                    f"メッシュ {mesh_code} (ID: {stats_data_id}) のレイヤー作成を開始します。",
                    PLUGIN_NAME,
                    level=Qgis.Info,
                )
                # 3. 必要な3つの引数をすべて渡してメソッドを呼び出す
                added_layer = self.algorithm.create_population_mesh_layer(
                    api_key, mesh_code, stats_data_id
                )
                if added_layer is not None:
                    created_layers += 1

            if created_layers > 0:
                QgsMessageLog.logMessage(
                    f"{created_layers}個の人口メッシュレイヤーを追加しました。",
                    PLUGIN_NAME,
                    level=Qgis.Success,
                )
                return True

            else:
                QgsMessageLog.logMessage(
                    "すべてのメッシュレイヤーの作成に失敗しました。",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )
                return False

        except Exception as e:
            QgsMessageLog.logMessage(
                f"人口メッシュレイヤーの可視化中にエラーが発生: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return False
