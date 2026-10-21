from typing import Optional

from qgis.core import (
    Qgis,
    QgsLayerTreeGroup,
    QgsMessageLog,
    QgsProject,
)
from qgis.gui import QgisInterface

from ...utils.api_keys import get_mlit_dpf_api_key
from ...utils.settings import PLUGIN_NAME
from .administrative_area_algorithm import AdministrativeAreaAlgorithm, ClassType


class AdministrativeAreaWorkflow:
    """行政区域ポリゴンのレイヤー取得・可視化のための汎用ワークフロー"""

    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self.algorithm = AdministrativeAreaAlgorithm(iface)
        self._missing_key_warned = False

    def reset(self):
        """国交DPFへの問い合わせ結果をクリアする（可視化の実行開始時に呼び出す）"""
        self.algorithm.clear_tile_url_cache()
        self._missing_key_warned = False

    def execute(
        self,
        class_type: ClassType,
        group: Optional[QgsLayerTreeGroup] = None,
    ) -> bool:
        """
        指定されたアルゴリズムを実行し、レイヤーをQGISに追加する

        Args:
            class_type: 行政区域のクラスタイプ ("base", "class3", "class5" または "class6")
            group: 行政区域を表示するグループ（ベースマップグループに追加）

        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        api_key = get_mlit_dpf_api_key()
        if not api_key:
            # 1回の可視化で複数回呼ばれるため、警告は reset() ごとに1回だけ出す
            if not self._missing_key_warned:
                self._missing_key_warned = True
                message = "国土交通データプラットフォームAPIキーが未設定のため、行政区域の取得をスキップします。"
                QgsMessageLog.logMessage(
                    message, PLUGIN_NAME, level=Qgis.MessageLevel.Warning
                )
                self.iface.messageBar().pushMessage(
                    "警告", message, level=Qgis.MessageLevel.Warning
                )
            return False

        add_layers = self.algorithm.create_administrative_area_layer(
            class_type=class_type, api_key=api_key
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
        if group:
            # 『行政区域』サブグループを取得または作成してからレイヤーを追加
            sub_group_name = "行政区域"
            sub_group = group.findGroup(sub_group_name)

            if sub_group:
                # 既に同名のレイヤーがサブグループ内に存在する場合は削除
                layer_names = {layer.name() for layer in layers_to_add}
                for child in sub_group.children():
                    if (
                        hasattr(child, "layer")
                        and child.layer()
                        and child.layer().name() in layer_names
                    ):
                        QgsProject.instance().removeMapLayer(child.layer().id())
            else:
                # サブグループが存在しない場合は新規作成
                sub_group = group.addGroup(sub_group_name)

            # レイヤーをサブグループに追加（ポリゴン→ラベルの順で、ラベルが上に表示）
            for layer in layers_to_add:
                QgsProject.instance().addMapLayer(layer, False)
                sub_group.addLayer(layer)

        else:
            for layer in layers_to_add:
                QgsProject.instance().addMapLayer(layer)

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
