"""
行政区域データの表示用モジュール
"""
import os
from typing import Optional

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsMessageLog,
    QgsVectorLayer,
    QgsWkbTypes,
)

from ...utils.settings import PLUGIN_NAME
from .settings import LAYER_NAME, CLASS3_STYLE

class AdministrativeAreaAlgorithm:
    """行政区域データの取得クラス"""

    def __init__(self, iface) :
        self.iface = iface

    def _get_mbtiles_path(self) -> str:
            """MBTilesファイルのパスを取得（将来的にはここの関数をAPIからデータを取得する形に変更）"""
            plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            return os.path.join(
                plugin_dir,
                "features",
                "administrative_area",
                "data",
                "class.mbtiles",
            )
    
    def create_administrative_area_layer(self) -> Optional[QgsVectorLayer]:
        """行政区域データのベクタタイルレイヤーを作成"""
        
        mbtiles_path = self._get_mbtiles_path()

        # MBTilesファイルの存在確認
        if not os.path.exists(mbtiles_path):
             QgsMessageLog.logMessage(
                f"MBTilesファイルが見つかりません: {mbtiles_path}",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )

        # MBTilesのURIの作成
        uri = f"{mbtiles_path}|layername=municipality"
        layer = QgsVectorLayer(uri, LAYER_NAME, "ogr")

        print("レイヤー", layer)

