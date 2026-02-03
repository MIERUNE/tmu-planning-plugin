from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
)

from ...utils.settings import PLUGIN_NAME


class HazardMapWorkflow:
    """ハザードマップポータルからのレイヤー取得・可視化のための汎用ワークフロー"""

    def __init__(self, iface):
        self.iface = iface

    def execute(self, algorithm) -> bool:
        """
        指定されたアルゴリズムを実行し、レイヤーをQGISに追加する
        """
        added_layer = algorithm.create_FloodHazardArea_layer()

        if not added_layer:
            QgsMessageLog.logMessage(
                "レイヤーの取得に失敗しました。",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )
            self.iface.messageBar().pushMessage(
                "警告",
                "レイヤーの取得に失敗しました。",
                level=Qgis.Warning,
            )
            return False

        # レイヤー有効性チェック
        if not added_layer.isValid():
            QgsMessageLog.logMessage(
                f"レイヤーが無効です: {added_layer.name()}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            self.iface.messageBar().pushMessage(
                "エラー",
                f"{added_layer.name()}レイヤーが無効です。",
                level=Qgis.Critical,
            )
            return False
        
        # 透過度を設定
        added_layer.renderer().setOpacity(0.65)

        # プロジェクトに追加
        QgsProject.instance().addMapLayer(added_layer)

        QgsMessageLog.logMessage(
            f"'{added_layer.name()}' レイヤーを追加しました。",
            PLUGIN_NAME,
            level=Qgis.Success,
        )
        self.iface.messageBar().pushMessage(
            "成功",
            f"{added_layer.name()}を表示しました。",
            level=Qgis.Success,
            duration=3,
        )

        return True
