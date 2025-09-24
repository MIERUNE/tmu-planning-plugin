from qgis.core import Qgis, QgsMessageLog

from ..marine_gis.coastline.coastline_algorithm import CoastlineAlgorithm
from ..marine_gis.connect import PLUGIN_NAME
from .base_workflow import BaseWorkflow


class CoastlineWorkflow(BaseWorkflow):
    """海岸線データ取得・可視化ワークフロー"""

    def __init__(self, iface):
        super().__init__(iface)
        self.algorithm = CoastlineAlgorithm(iface)

    def execute(self, bounds=None) -> bool:
        """
        ワークフローを実行し、海岸線レイヤーをQGISに追加する
        Args:
            bounds (dict, optional): 取得範囲の境界。Noneの場合はデフォルト範囲を使用
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            QgsMessageLog.logMessage(
                "海岸線データを取得します...", PLUGIN_NAME, level=Qgis.Info
            )

            success = self.algorithm.get_coastline_data(bounds)

            if success:
                QgsMessageLog.logMessage(
                    "海岸線レイヤーを追加しました。",
                    PLUGIN_NAME,
                    level=Qgis.Success,
                )
                return True
            else:
                message = "海岸線データが見つかりませんでした。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("情報", message, level=Qgis.Info)
                return False

        except Exception as e:
            QgsMessageLog.logMessage(
                f"海岸線の可視化中にエラーが発生: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return False
