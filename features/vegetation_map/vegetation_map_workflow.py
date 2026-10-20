from typing import Optional

from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
)

from ...utils.settings import PLUGIN_NAME
from .vegetation_map_algorithm import VegetationMapAlgorithm


class VegetationMapWorkflow:
    """現存植生図2024（環境ジオポータル）のレイヤー取得・可視化ワークフロー"""

    def __init__(self, iface):
        self.iface = iface
        self.algorithm = VegetationMapAlgorithm(iface)

    def execute(
        self,
        prefecture_code: Optional[str],
        municipality_code: str,
        municipality_name: Optional[str],
    ) -> bool:
        """
        現存植生図2024 を取得し、レイヤーをQGISに追加する
        Args:
            prefecture_code (str, optional): 都道府県コード（2桁）
            municipality_code (str): 市区町村コード（5桁）
            municipality_name (str, optional): 市区町村名
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            added_layer = self.algorithm.create_layer(
                prefecture_code=prefecture_code,
                municipality_code=municipality_code,
                municipality_name=municipality_name,
            )
            if added_layer is None:
                QgsMessageLog.logMessage(
                    "現存植生図2024レイヤーの取得に失敗しました。",
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
                f"現存植生図2024の可視化中にエラーが発生: {str(e)}",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Critical,
            )
            return False
