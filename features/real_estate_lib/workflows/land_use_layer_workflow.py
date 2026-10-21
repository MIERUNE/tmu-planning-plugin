from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
)
from qgis.gui import QgisInterface

from ....utils.api_keys import get_real_estate_api_key
from ....utils.settings import PLUGIN_NAME


class LayerWorkflow:
    """不動産情報ライブラリからのレイヤー取得・可視化のための汎用ワークフロー"""

    def __init__(self, iface: QgisInterface):
        self.iface = iface

    def execute(self, algorithm, **kwargs) -> bool:
        """
        指定されたアルゴリズムを実行し、レイヤーをQGISに追加する
        """
        api_key = get_real_estate_api_key()
        if not api_key:
            message = f"不動産情報ライブラリAPIキーが未設定のため、{algorithm.LAYER_DISPLAY_NAME}の取得をスキップします。"
            QgsMessageLog.logMessage(
                message, PLUGIN_NAME, level=Qgis.MessageLevel.Warning
            )
            self.iface.messageBar().pushMessage(
                "警告", message, level=Qgis.MessageLevel.Warning
            )
            return False

        try:
            added_layer = algorithm.create_layer(api_key, **kwargs)
            if not added_layer:
                # メッセージを汎用的に変更
                QgsMessageLog.logMessage(
                    "レイヤーの取得に失敗しました。",
                    PLUGIN_NAME,
                    level=Qgis.MessageLevel.Warning,
                )
                return False

            QgsProject.instance().addMapLayer(added_layer)
            QgsMessageLog.logMessage(
                f"'{added_layer.name()}' レイヤーを追加しました。",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Success,
            )
            return True

        except Exception as e:
            QgsMessageLog.logMessage(
                f"レイヤーの可視化中にエラーが発生: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Critical,
            )
            return False
