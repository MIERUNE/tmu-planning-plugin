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
        # APIキー未設定で6クラス分類をスキップしたか（base 実行時の警告に含める）
        self._class6_skipped = False
        # レイヤー取得失敗の警告を出したか（1回の可視化で1件だけ出す）
        self._failure_notified = False

    def reset(self):
        """国交DPFへの問い合わせ結果をクリアする（可視化の実行開始時に呼び出す）"""
        self.algorithm.clear_tile_url_cache()
        self._class6_skipped = False
        self._failure_notified = False

    def _no_api_key_message(self, use_local: bool) -> str:
        """APIキー未設定時の警告文"""
        if not use_local:
            return "国土交通DPFのAPIキーが未設定のため、行政区域データの取得をスキップします。"
        message = "国土交通DPFのAPIキーが未設定のため、行政区域はローカルデータを使用しました。"
        if self._class6_skipped:
            message += "6クラス分類はAPIキーが必要なためスキップしました。"
        return message

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
        # APIキー未設定時、ローカルデータを同梱していればフォールバックし、なければスキップする
        # （6クラス分類はローカルデータがないため常にスキップ）
        api_key = get_mlit_dpf_api_key()
        if not api_key:
            use_local = class_type != "class6" and self.algorithm.has_local_fallback()
            if class_type == "class6":
                self._class6_skipped = True
            # 警告は1回の可視化で最後に呼ばれる base のときにまとめて1件だけ出す
            if class_type == "base":
                message = self._no_api_key_message(use_local)
                QgsMessageLog.logMessage(
                    message, PLUGIN_NAME, level=Qgis.MessageLevel.Warning
                )
                self.iface.messageBar().pushMessage(
                    "警告", message, level=Qgis.MessageLevel.Warning
                )
            if not use_local:
                return False

        add_layers = self.algorithm.create_administrative_area_layer(
            class_type=class_type, api_key=api_key
        )

        if not add_layers:
            QgsMessageLog.logMessage(
                f"行政区域レイヤー（{class_type}）の取得に失敗しました。",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Warning,
            )
            # 国交DPFから取得できない場合は全レイヤーで失敗するため、メッセージバーには1件だけ出す
            if not self._failure_notified:
                self.iface.messageBar().pushMessage(
                    "警告",
                    "行政区域レイヤーの取得に失敗しました。",
                    level=Qgis.MessageLevel.Warning,
                )
                self._failure_notified = True
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
