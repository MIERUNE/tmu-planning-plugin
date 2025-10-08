import traceback

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsMessageLog,
    QgsProject,
    QgsTask,
)

from ..estat.connect import PLUGIN_NAME
from ..estat.get_dataset_id import GetDatasetId
from ..estat.population_mesh_algorithm import PopulationMeshAlgorithm


class PopulationMeshTask(QgsTask):
    """人口メッシュ取得処理をバックグラウンドで実行するためのタスク"""

    def __init__(
        self,
        description,
        api_key,
        municipality_code,
        layer_name,
    ):
        super().__init__(description, QgsTask.CanCancel)
        self.api_key = api_key
        self.municipality_code = municipality_code
        self.layer_name = layer_name
        self.final_layer = None
        self.exception = None

    def run(self):
        """
        バックグラウンドスレッドで実行されるメインの処理。
        """
        try:
            QgsMessageLog.logMessage("Task run: 開始", PLUGIN_NAME, level=Qgis.Info)
            self.algorithm = PopulationMeshAlgorithm(None)
            dataset_id_getter = GetDatasetId(None)

            dataset_id_dict = dataset_id_getter.fetch_dataset_ids_for_municipality(
                self.municipality_code, self.api_key
            )

            if not dataset_id_dict:
                return False

            layers_to_merge = []
            total_steps = len(dataset_id_dict)

            for i, (mesh_code, stats_data_id) in enumerate(dataset_id_dict.items()):
                # ユーザーがキャンセルボタンを押したかチェック
                if self.isCanceled():
                    return False

                # 進捗を更新
                self.setProgress((i / total_steps) * 100)

                layer = self.algorithm.create_single_population_layer(
                    self.api_key, mesh_code, stats_data_id
                )
                if layer is not None:
                    layers_to_merge.append(layer)

            if layers_to_merge:
                self.final_layer = self.algorithm.merge_population_layers(
                    layers_to_merge, self.layer_name
                )
                if self.final_layer is not None:
                    return True

            return False

        except Exception:
            self.exception = traceback.format_exc()
            return False

    def finished(self, result):
        """人口メッシュ取得処理をバックグラウンドで実行するためのタスク"""
        if result:
            if self.final_layer is not None:
                QgsProject.instance().addMapLayer(self.final_layer)
                QgsMessageLog.logMessage(
                    f"レイヤー「{self.layer_name}」の作成が完了しました。",
                    PLUGIN_NAME,
                    level=Qgis.Success,
                )
            else:
                QgsMessageLog.logMessage(
                    "タスクは成功しましたが、最終的なレイヤーが見つかりません。",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )
        else:
            if self.exception:
                QgsMessageLog.logMessage(
                    f"エラーが発生しました: {self.exception}",
                    PLUGIN_NAME,
                    level=Qgis.Critical,
                )
            else:
                QgsMessageLog.logMessage(
                    "タスクがキャンセルされたか、データが見つかりませんでした。",
                    PLUGIN_NAME,
                    level=Qgis.Info,
                )


class PopulationMeshWorkflow:
    """人口メッシュデータの取得・可視化のためのワークフロー"""

    def __init__(self, iface):
        self.iface = iface
        self.algorithm = PopulationMeshAlgorithm(iface)
        self.dataset_id_getter = GetDatasetId(iface)

    def execute(self, municipality_code: str, api_key: str, layer_name: str):
        """
        指定されたアルゴリズムを実行し、レイヤーをQGISに追加する
        Args:
            municipality_code (str): 市区町村コード
            api_key (str): e-Stat APIキー
            layer_name (str): 追加するレイヤーの名前
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        task = PopulationMeshTask(
            f"'{layer_name}' を作成中...",
            api_key,
            municipality_code,
            layer_name,
        )
        # QGISのタスクマネージャーにタスクを登録
        QgsApplication.taskManager().addTask(task)

        QgsMessageLog.logMessage(
            "人口メッシュデータのバックグラウンド処理を開始しました。",
            PLUGIN_NAME,
            level=Qgis.Info,
        )
