from typing import Literal, Optional

from qgis.core import (
    Qgis,
    QgsLayerTreeGroup,
    QgsMessageLog,
    QgsProject,
)

from ...utils.settings import PLUGIN_NAME
from .administrative_area_algorithm import AdministrativeAreaAlgorithm


class AdministrativeAreaWorkflow:
    """行政区域ポリゴンのレイヤー取得・可視化のための汎用ワークフロー"""

    def __init__(self, iface):
        self.iface = iface
        self.algorithm = AdministrativeAreaAlgorithm(iface)

    def execute(
        self,
        class_type: Literal["base", "class3", "class5"],
        group: Optional[QgsLayerTreeGroup] = None,
    ) -> bool:
        """
        指定されたアルゴリズムを実行し、レイヤーをQGISに追加する

        Args:
            class_type: 行政区域のクラスタイプ ("base", "class3" または "class5")
            group: 行政区域を表示するグループ（ベースマップグループに追加）

        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        added_layer = self.algorithm.create_administrative_area_layer(
            class_type=class_type
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
        if group:
            # 『行政区域』サブグループをを取得または作成してからレイヤーを追加
            sub_group_name = "行政区域"
            sub_group = group.findGroup(sub_group_name)
            if not sub_group:
                sub_group = group.addGroup(sub_group_name)

            QgsProject.instance().addMapLayer(added_layer, False)
            sub_group.addLayer(added_layer)
        else:
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
