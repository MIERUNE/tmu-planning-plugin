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

    def __init__(self, description, api_key, municipality_code, layer_name, iface):
        super().__init__(description, QgsTask.CanCancel)
        self.api_key = api_key
        self.municipality_code = municipality_code
        self.layer_name = layer_name
        self.iface = iface
        self.final_layer = None
        self.exception = None

    def run(self):
        """
        バックグラウンドスレッドで実行されるメインの処理。
        GUIに関わる操作（addMapLayerなど）は絶対にここで行わない。
        """

        try:
            # === ログ追加 1 ===
            QgsMessageLog.logMessage("Task.run() 開始", PLUGIN_NAME, level=Qgis.Info)

            self.algorithm = PopulationMeshAlgorithm(None)
            dataset_id_getter = GetDatasetId(None)

            # === ログ追加 2 ===
            QgsMessageLog.logMessage(
                f"データセットIDの取得開始: municipality_code={self.municipality_code}",
                PLUGIN_NAME,
                level=Qgis.Info,
            )
            dataset_id_dict = dataset_id_getter.fetch_dataset_ids_for_municipality(
                self.municipality_code, self.api_key
            )
            # === ログ追加 3 ===
            QgsMessageLog.logMessage(
                f"データセットIDの取得完了: {len(dataset_id_dict)}件見つかりました。",
                PLUGIN_NAME,
                level=Qgis.Info,
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

        except Exception as e:
            self.exception = e
            return False

    def finished(self, result):
        """
        runメソッド完了後、自動的にメインスレッドで実行される。
        GUI操作（レイヤー追加、メッセージ表示）はここで行う。
        """
        QgsMessageLog.logMessage(
            "[finished] タスク完了。メインスレッドで最終処理を開始します。",
            PLUGIN_NAME,
            level=Qgis.Info,
        )
        QgsMessageLog.logMessage(
            f"[finished] result: {result}", PLUGIN_NAME, level=Qgis.Info
        )

        if result:
            # 成功した場合
            if self.final_layer is not None and self.final_layer.isValid():
                QgsMessageLog.logMessage(
                    f"[finished] 最終レイヤー '{self.final_layer.name()}' は有効です。",
                    PLUGIN_NAME,
                    level=Qgis.Info,
                )
                QgsMessageLog.logMessage(
                    f"[finished] 地物数: {self.final_layer.featureCount()}",
                    PLUGIN_NAME,
                    level=Qgis.Info,
                )

                # レイヤーをプロジェクトに追加
                QgsProject.instance().addMapLayer(self.final_layer)
                QgsMessageLog.logMessage(
                    "[finished] レイヤーをプロジェクトに追加しました。",
                    PLUGIN_NAME,
                    level=Qgis.Info,
                )

                # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
                # ★★★ これが決定打：追加したレイヤーの範囲にズームする ★★★
                # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
                self.iface.mapCanvas().setExtent(self.final_layer.extent())
                self.iface.mapCanvas().refresh()
                QgsMessageLog.logMessage(
                    "[finished] レイヤーの範囲にズームしました。",
                    PLUGIN_NAME,
                    level=Qgis.Info,
                )

                QgsMessageLog.logMessage(
                    f"レイヤー「{self.layer_name}」の作成が完了しました。",
                    PLUGIN_NAME,
                    level=Qgis.Success,
                )
            else:
                QgsMessageLog.logMessage(
                    "タスクは成功しましたが、最終的なレイヤーが無効か、見つかりません。",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )
        else:
            # 失敗またはキャンセルされた場合
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
            self.iface,
        )
        # QGISのタスクマネージャーにタスクを登録
        QgsApplication.taskManager().addTask(task)

        QgsMessageLog.logMessage(
            "人口メッシュデータのバックグラウンド処理を開始しました。",
            PLUGIN_NAME,
            level=Qgis.Info,
        )
