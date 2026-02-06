from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
)

from ...utils.settings import PLUGIN_NAME
from .administrative_area_algorithm import AdministrativeAreaAlgorithm


class AdministrativeAreaWorkflow:
    """行政区域ポリゴンののレイヤー取得・可視化のための汎用ワークフロー"""

    def __init__(self, iface):
        self.iface = iface
        self.algorithm = AdministrativeAreaAlgorithm(iface)

    def execute(self, prefecture_name: str) -> bool:
        """
        指定されたアルゴリズムを実行し、レイヤーをQGISに追加する

        Args:
            prefecture_name: 都道府県名（例: "北海道"）
        """
        added_layer = self.algorithm.create_administrative_area_layer(
            prefecture_name=prefecture_name
        )

        if not added_layer:
            QgsMessageLog.logMessage(
                "行政区域レイヤーの取得に失敗しました。",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )
            self.iface.messageBar().pushMessage(
                "警告",
                "行政区域レイヤーの取得に失敗しました。",
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
