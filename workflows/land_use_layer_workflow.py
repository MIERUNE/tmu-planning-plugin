from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
)

from ..real_estate_lib.connect import PLUGIN_NAME
from ..real_estate_lib.land_use.urban_planning_algorithm import (
    UrbanPlanningAlgorithm,
)


# class UrbanPlanningWorkflow:
#     """都市計画区域データ取得・可視化ワークフロー"""

#     def __init__(self, iface):
#         self.iface = iface
#         self.algorithm = UrbanPlanningAlgorithm(iface)

#     def execute(self, api_key: str) -> bool:
#         """
#         ワークフローを実行し、都市計画区域タイルレイヤーをQGISに追加する
#         Args:
#             api_key (str): APIキー
#         Returns:
#             bool: 成功した場合はTrue、失敗した場合はFalse
#         """
#         try:
#             added_layer = self.algorithm.get_urban_planning_area(api_key)

#             # データが空なら処理を中断
#             if not added_layer:
#                 message = "都市計画区域データの追加に失敗しました。"
#                 QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
#                 self.iface.messageBar().pushMessage("情報", message, level=Qgis.Warning)
#                 return False

#             QgsProject.instance().addMapLayer(added_layer)
#             QgsMessageLog.logMessage(
#                 f"'{added_layer.name()}'都市計画区域レイヤーの追加に成功しました。",
#                 PLUGIN_NAME,
#                 level=Qgis.Success,
#             )

#             return True

#         except Exception as e:
#             QgsMessageLog.logMessage(
#                 f"都市計画区域の可視化中にエラーが発生: {str(e)}",
#                 PLUGIN_NAME,
#                 level=Qgis.Critical,
#             )
#             return False

class LayerWorkflow:
    """不動産情報ライブラリからのレイヤー取得・可視化のための汎用ワークフロー"""

    def __init__(self, iface):
        self.iface = iface

    def execute(self, algorithm, api_key: str) -> bool:
        """
        指定されたアルゴリズムを実行し、レイヤーをQGISに追加する
        """
        try:
            added_layer = algorithm.create_layer(api_key)

            if not added_layer:
                # メッセージを汎用的に変更
                QgsMessageLog.logMessage("レイヤーの取得に失敗しました。", PLUGIN_NAME, level=Qgis.Warning)
                return False

            QgsProject.instance().addMapLayer(added_layer)
            QgsMessageLog.logMessage(
                f"'{added_layer.name()}' レイヤーを追加しました。",
                PLUGIN_NAME,
                level=Qgis.Success,
            )
            return True

        except Exception as e:
            QgsMessageLog.logMessage(
                f"レイヤーの可視化中にエラーが発生: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return False
