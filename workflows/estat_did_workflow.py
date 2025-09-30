from qgis.core import (Qgis, QgsMessageLog, QgsProject)

from ..estat.did_algorithm import DidAlgorithm
from ..estat.connect import PLUGIN_NAME


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

            # 3. 結果をハンドリング
            if added_layer is None:
                message = f"人口集中地区(DID)レイヤーの取得に失敗しました。(コード: {prefecture_code})"
                self.iface.messageBar().pushMessage("エラー", message, level=Qgis.Critical, duration=5)
                QgsMessageLog.logMessage(message, PLUGIN_NAME, Qgis.Critical)
                return False

            # 4. 成功した場合、レイヤをプロジェクトに追加
            QgsProject.instance().addMapLayer(added_layer)
            message = f"レイヤ '{added_layer.name()}' を追加しました。"
            QgsMessageLog.logMessage(message, PLUGIN_NAME, Qgis.Success)
            return True

        except Exception as e:
            error_message = f"ワークフロー実行中に予期せぬエラーが発生: {str(e)}"
            QgsMessageLog.logMessage(error_message, PLUGIN_NAME, Qgis.Critical)
            self.iface.messageBar().pushMessage("致命的エラー", error_message, level=Qgis.Critical)
            return False