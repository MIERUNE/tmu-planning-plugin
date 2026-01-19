from typing import Literal, Optional

import processing
from qgis.core import (
    Qgis,
    QgsGraduatedSymbolRenderer,
    QgsMessageLog,
    QgsProject,
    QgsStyle,
    QgsVectorLayer,
)

from .connect import MESH_TYPE_CONFIG, PLUGIN_NAME


class MergePopulationMeshLayers:
    """
    人口メッシュのレイヤーをマージして可視化するクラス
    """

    def __init__(self, iface):
        self.iface = iface

    def _apply_population_style(self, layer: QgsVectorLayer):
        """
        レイヤーに段階分けレンダリングを適用

        Args:
            layer: 可視化対象のレイヤー
        """
        # 可視化（段階分けレンダリング）
        target_field = "population"

        # 5段階に分類して色分け
        class_count = 5

        renderer = QgsGraduatedSymbolRenderer(target_field)
        renderer.setClassAttribute(target_field)

        color_ramp = QgsStyle.defaultStyle().colorRamp("Viridis")
        renderer.setSourceColorRamp(color_ramp)

        renderer.updateClasses(layer, QgsGraduatedSymbolRenderer.Jenks, class_count)

        layer.setRenderer(renderer)
        layer.triggerRepaint()  # 地図を再描画

        QgsMessageLog.logMessage(
            f"レイヤー '{layer.name()}' に可視化を適用しました。",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

    def merge_population_mesh_layers(
        self,
        added_population_layers: list[dict],
        municipality_name: str,
        mesh_type: Literal["3rd", "4th"],
        remove_originals: bool = True,
    ) -> Optional[QgsVectorLayer]:
        """
        人口メッシュレイヤーをマージして一つのレイヤーにまとめる
        Returns:
            QgsVectorLayer: マージされた人口メッシュレイヤー
        """
        if not added_population_layers:
            QgsMessageLog.logMessage(
                "統合するレイヤーがありません。",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )
            return None

        # 1つのレイヤーの場合はマージしない
        if len(added_population_layers) == 1:
            single_layer = added_population_layers[0]["layer"]
            single_layer.setName(
                f"{MESH_TYPE_CONFIG[mesh_type]['output_layer_name']}_{municipality_name}"
            )

            QgsProject.instance().addMapLayer(single_layer)

            # 可視化を適用
            self._apply_population_style(single_layer)
            return single_layer

        # レイヤーオブジェクトのリストを取得
        layer_objects = [item["layer"] for item in added_population_layers]

        QgsMessageLog.logMessage(
            f"{len(layer_objects)}個のレイヤーを統合中...",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

        # プロセシングツールで統合
        result = processing.run(
            "native:mergevectorlayers",
            {
                "LAYERS": layer_objects,
                "CRS": layer_objects[0].crs(),
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )

        merged_layer = result["OUTPUT"]
        merged_layer.setName(
            f"{MESH_TYPE_CONFIG[mesh_type]['output_layer_name']}_{municipality_name}"
        )

        # 統合レイヤーをプロジェクトに追加
        QgsProject.instance().addMapLayer(merged_layer)

        QgsMessageLog.logMessage(
            f"統合レイヤー '{merged_layer.name()}' を作成しました。",
            PLUGIN_NAME,
            level=Qgis.Success,
        )

        # 可視化を適用
        self._apply_population_style(merged_layer)

        # 元の個別レイヤーを削除
        if remove_originals:
            for layer_obj in layer_objects:
                QgsProject.instance().removeMapLayer(layer_obj.id())
            QgsMessageLog.logMessage(
                f"{len(layer_objects)}個の個別レイヤーを削除しました。",
                PLUGIN_NAME,
                level=Qgis.Info,
            )

        return merged_layer
