from qgis.core import Qgis, QgsMessageLog, QgsProject

from ..estat.connect import PLUGIN_NAME
from ..estat.did_algorithm import DidAlgorithm


class EstatDidWorkflow:
    """e-Stat APIを利用して、人口集中地区（DID）データを取得し、QGISに追加するワークフローを管理するクラス"""

    def __init__(self, iface):
        self.iface = iface

    def execute(self, prefecture_code: str) -> bool:
        """
        指定された都道府県コードでワークフローを実行する
        Args:
            prefecture_code (str): 実行対象の都道府県コード
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            algorithm = DidAlgorithm(prefecture_code, self.iface)
            added_layer = algorithm.get_did_area()

            if not added_layer:
                message = "人口集中地区(DID)レイヤーの取得に失敗しました。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, Qgis.Critical)
                self.iface.messageBar().pushMessage(
                    "エラー", message, level=Qgis.Critical, duration=5
                )
                return False

            QgsProject.instance().addMapLayer(added_layer)
            return True

        except Exception as e:
            message = f"人口集中地区(DID)の可視化中にエラーが発生しました: {str(e)}"
            QgsMessageLog.logMessage(message, PLUGIN_NAME, Qgis.Critical)
            self.iface.messageBar().pushMessage(message, level=Qgis.Critical)
            return False
