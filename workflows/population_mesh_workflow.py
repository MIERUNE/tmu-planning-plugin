from typing import Optional

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsMessageLog,
    QgsProject,
    QgsTask,
    QgsVectorLayer,
)

from ..estat.connect import PLUGIN_NAME
from ..estat.get_dataset_id import GetDatasetId
from ..estat.merge_algorithm import MergePopulationMeshLayers
from ..estat.population_mesh_algorithm import PopulationMeshAlgorithm


class PopulationMeshTask(QgsTask):
    """人口メッシュデータの取得をバックグラウンドで実行するタスク"""

    def __init__(
        self,
        iface,
        api_key: str,
        municipality_code: str,
        municipality_name: str,
    ):
        super().__init__(
            f"人口メッシュデータ取得: {municipality_name}", QgsTask.CanCancel
        )
        self.iface = iface
        self.api_key = api_key
        self.municipality_code = municipality_code
        self.municipality_name = municipality_name
        self.workflow = PopulationMeshWorkflow(iface)
        self.merged_layer = None
        self.exception = None
        self.success = False

    def run(self):
        """
        バックグラウンドで実行される処理（レイヤー追加以外）
        Returns:
            bool: 成功した場合True、失敗した場合False
        """
        try:
            # ワークフローを実行（レイヤー追加なし）
            self.merged_layer = self.workflow.execute_without_adding_to_project(
                self.api_key, self.municipality_code, self.municipality_name
            )

            if self.isCanceled():
                QgsMessageLog.logMessage(
                    "タスクがキャンセルされました。",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )
                return False

            self.success = self.merged_layer is not None
            return self.success

        except Exception as e:
            self.exception = e
            QgsMessageLog.logMessage(
                f"タスク実行中にエラー: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return False

    def finished(self, result: bool):
        """
        タスク完了時に実行される処理（メインスレッドで実行）
        Args:
            result: run()の戻り値
        """
        if result and self.merged_layer is not None:
            # 成功時：メインスレッドでレイヤーを追加
            QgsProject.instance().addMapLayer(self.merged_layer)
            self.iface.mapCanvas().refresh()

            QgsMessageLog.logMessage(
                f"処理完了: {self.municipality_name}の人口メッシュデータを取得しました。",
                PLUGIN_NAME,
                level=Qgis.Success,
            )
            self.iface.messageBar().pushMessage(
                "成功",
                f"{self.municipality_name}の人口メッシュレイヤーが追加されました。",
                level=Qgis.Success,
                duration=5,
            )
        else:
            # 失敗時
            error_msg = "人口メッシュデータの取得に失敗しました。"
            if self.exception:
                error_msg += f" エラー: {str(self.exception)}"

            self.iface.messageBar().pushMessage(
                "エラー",
                error_msg,
                level=Qgis.Critical,
                duration=10,
            )
            QgsMessageLog.logMessage(
                f"タスク失敗: {self.municipality_name} - {error_msg}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )

    def cancel(self):
        """タスクがキャンセルされた時の処理"""
        QgsMessageLog.logMessage(
            f"タスクをキャンセル中: {self.municipality_name}",
            PLUGIN_NAME,
            level=Qgis.Warning,
        )
        super().cancel()


class PopulationMeshWorkflow:
    """人口メッシュデータの取得・可視化のためのワークフロー"""

    def __init__(self, iface):
        self.iface = iface
        self.algorithm = PopulationMeshAlgorithm(iface)
        self.merge_algorithm = MergePopulationMeshLayers(iface)
        self.dataset_id_getter = GetDatasetId(iface)

    def _fetch_dataset_ids(self, municipality_code: str, api_key: str) -> dict:
        """データセットIDを取得"""
        dataset_id_dict = self.dataset_id_getter.fetch_dataset_ids_for_municipality(
            municipality_code, api_key
        )

        if not dataset_id_dict:
            QgsMessageLog.logMessage(
                f"自治体コード '{municipality_code}' のデータセットIDが取得できませんでした。",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )
            return {}

        return dataset_id_dict

    def _create_population_layers(self, api_key: str, dataset_id_dict: dict) -> list:
        """
        各メッシュコードに対してレイヤーを作成

        Args:
            api_key: e-Stat APIキー
            dataset_id_dict: {メッシュコード: データセットID} の辞書

        Returns:
            list: 成功したレイヤーの情報リスト
        """
        added_layers = []

        # 複数メッシュに対してfor文で処理
        for mesh_code, stats_data_id in dataset_id_dict.items():
            # アルゴリズムに個別メッシュの処理を委譲
            population_mesh_layer = self.algorithm.create_population_mesh_layer(
                api_key, mesh_code, stats_data_id
            )

            if population_mesh_layer is not None:
                added_layers.append(
                    {
                        "layer": population_mesh_layer,
                        "mesh_code": mesh_code,
                        "stats_data_id": stats_data_id,
                    }
                )
            else:
                QgsMessageLog.logMessage(
                    f"メッシュコード '{mesh_code}' のレイヤー追加に失敗",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )

        return added_layers

    def execute_without_adding_to_project(
        self, api_key: str, municipality_code: str, municipality_name: str
    ) -> Optional[QgsVectorLayer]:
        """
        レイヤーをプロジェクトに追加せずに作成のみ行う（QgsTask用）
        Args:
            api_key (str): e-Stat APIキー
            municipality_code (str): 自治体コード（例: "01100" 札幌市）
            municipality_name (str): 自治体名
        Returns:
            Optional[QgsVectorLayer]: 作成されたレイヤー
        """
        # 1. 自治体コードからデータセットIDを取得
        dataset_id_dict = self._fetch_dataset_ids(municipality_code, api_key)

        if not dataset_id_dict:
            return None

        # 2. 各メッシュコードの人口メッシュレイヤーを作成
        added_population_layers = self._create_population_layers(
            api_key, dataset_id_dict
        )

        # 3. レイヤーをマージ（プロジェクトに追加しない）
        merged_layer = self.merge_algorithm.merge_population_mesh_layers_without_adding(
            added_population_layers, municipality_name, remove_originals=False
        )

        return merged_layer

    def execute(
        self, api_key: str, municipality_code: str, municipality_name: str
    ) -> bool:
        """
        指定されたアルゴリズムを実行し、レイヤーをQGISに追加する
        Args:
            api_key (str): e-Stat APIキー
            municipality_code (str): 自治体コード（例: "01100" 札幌市）
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """

        # 1. 自治体コードからデータセットIDを取得
        dataset_id_dict = self._fetch_dataset_ids(municipality_code, api_key)

        if not dataset_id_dict:
            return False

        # 2. 各メッシュコードの人口メッシュレイヤーを作成
        added_population_layers = self._create_population_layers(
            api_key, dataset_id_dict
        )

        # 3. レイヤーをマージ（別PRで対応予定）
        merged_layer = self.merge_algorithm.merge_population_mesh_layers(
            added_population_layers, municipality_name, remove_originals=True
        )

        if merged_layer is not None:
            return True
        else:
            return False

    @staticmethod
    def run_as_task(
        iface, api_key: str, municipality_code: str, municipality_name: str
    ) -> PopulationMeshTask:
        """
        ワークフローをQGISタスクとして実行

        Args:
            iface: QGISインターフェース
            api_key: e-Stat APIキー
            municipality_code: 自治体コード
            municipality_name: 自治体名

        Returns:
            PopulationMeshTask: 開始されたタスク
        """
        # タスクを作成
        task = PopulationMeshTask(iface, api_key, municipality_code, municipality_name)

        # タスクマネージャーに追加して実行
        QgsApplication.taskManager().addTask(task)

        # タスク開始通知(これを消したらQgsTaskが動かなくなる)
        iface.messageBar().pushMessage(
            "処理開始",
            f"{municipality_name}の人口メッシュデータ取得を開始しました。",
            level=Qgis.Info,
            duration=3,
        )

        return task
