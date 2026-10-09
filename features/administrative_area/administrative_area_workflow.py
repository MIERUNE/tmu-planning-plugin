from typing import Literal, Optional

from qgis.core import (
    Qgis,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
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
        add_layers = self.algorithm.create_administrative_area_layer(
            class_type=class_type
        )

        if not add_layers:
            QgsMessageLog.logMessage(
                "行政区域レイヤーの取得に失敗しました。",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Warning,
            )
            self.iface.messageBar().pushMessage(
                "警告",
                "行政区域レイヤーの取得に失敗しました。",
                level=Qgis.MessageLevel.Warning,
            )
            return False

        polygon_layer, label_layer = add_layers

        layers_to_add = [polygon_layer]
        if label_layer:
            layers_to_add.append(label_layer)

        # レイヤー有効性チェック
        for layer in layers_to_add:
            if not layer.isValid():
                QgsMessageLog.logMessage(
                    f"レイヤーが無効です: {layer.name()}",
                    PLUGIN_NAME,
                    level=Qgis.MessageLevel.Critical,
                )
                self.iface.messageBar().pushMessage(
                    "エラー",
                    f"{layer.name()}レイヤーが無効です。",
                    level=Qgis.MessageLevel.Critical,
                )
                return False

        # プロジェクトに追加
        project = QgsProject.instance()
        if project is None:
            return False

        if group:
            # 『行政区域』サブグループを取得または作成してからレイヤーを追加
            sub_group_name = "行政区域"
            sub_group = group.findGroup(sub_group_name)

            if sub_group:
                # 既に同名のレイヤーがサブグループ内に存在する場合は削除
                layer_names = {layer.name() for layer in layers_to_add}
                for child in sub_group.children():
                    if isinstance(child, QgsLayerTreeLayer):
                        child_layer = child.layer()
                        if child_layer and child_layer.name() in layer_names:
                            project.removeMapLayer(child_layer.id())
            else:
                # サブグループが存在しない場合は新規作成
                sub_group = group.addGroup(sub_group_name)
                if sub_group is None:
                    return False

            # レイヤーをサブグループに追加（ポリゴン→ラベルの順で、ラベルが上に表示）
            for layer in layers_to_add:
                project.addMapLayer(layer, False)
                sub_group.addLayer(layer)

        else:
            for layer in layers_to_add:
                project.addMapLayer(layer)

        QgsMessageLog.logMessage(
            f"'{polygon_layer.name()}' レイヤーを追加しました。",
            PLUGIN_NAME,
            level=Qgis.MessageLevel.Success,
        )
        self.iface.messageBar().pushMessage(
            "成功",
            f"{polygon_layer.name()}を表示しました。",
            level=Qgis.MessageLevel.Success,
            duration=3,
        )

        return True
