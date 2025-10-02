from qgis.core import (
    Qgis,
    QgsMessageLog,
)

from ..estat.connect import PLUGIN_NAME
from ..estat.population_mesh_algorithm import PopulationMeshAlgorithm


class PopulationMeshWorkflow:
    """人口メッシュデータの取得・可視化のためのワークフロー"""

    def __init__(self, iface):
        self.iface = iface
        self.algorithm = PopulationMeshAlgorithm(iface)

    def execute(self) -> bool:
        """
        指定されたアルゴリズムを実行し、レイヤーをQGISに追加する
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            added_layer = self.algorithm.create_population_mesh_layer()

            if added_layer is None:
                QgsMessageLog.logMessage(
                    "人口メッシュレイヤーの取得に失敗しました。",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )
                return False

            QgsMessageLog.logMessage(
                f"'{added_layer.name()}' 人口メッシュレイヤーを追加しました。",
                PLUGIN_NAME,
                level=Qgis.Success,
            )
            return True

        except Exception as e:
            QgsMessageLog.logMessage(
                f"人口メッシュレイヤーの可視化中にエラーが発生: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return False
