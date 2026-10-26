from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
)

from ....utils.settings import PLUGIN_NAME


class LayerWorkflow:
    """不動産情報ライブラリからのレイヤー取得・可視化のための汎用ワークフロー"""

    def __init__(self, iface):
        self.iface = iface

    def execute(self, algorithm, authcfg: str, **kwargs) -> bool:
        """
        指定されたアルゴリズムを実行し、レイヤーをQGISに追加する
        Args:
            algorithm: create_layer(authcfg, **kwargs) を持つアルゴリズム
            authcfg (str): APIキーを付与する認証設定ID（APIHeader）
        """
        try:
            added_layer = algorithm.create_layer(authcfg, **kwargs)
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
