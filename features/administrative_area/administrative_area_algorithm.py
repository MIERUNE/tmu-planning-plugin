"""
行政区域データの表示用モジュール
"""

import os
from typing import Optional

from qgis.core import (
    Qgis,
    QgsFillSymbol,
    QgsMessageLog,
    QgsVectorTileBasicRenderer,
    QgsVectorTileBasicRendererStyle,
    QgsVectorTileLayer,
)

from ...utils.settings import PLUGIN_NAME
from .settings import CLASS3_STYLE, LAYER_NAME


class AdministrativeAreaAlgorithm:
    """行政区域データの取得クラス"""

    def __init__(self, iface):
        self.iface = iface

    def _get_mbtiles_path(self) -> str:
        """MBTilesファイルのパスを取得（将来的にはここの関数をAPIからデータを取得する形に変更）"""
        plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        print("plugin_dir", plugin_dir)

        QgsMessageLog.logMessage(
            f"MBTilesファイルのパスを取得: {plugin_dir}",
            PLUGIN_NAME,
            level=Qgis.Info,
        )
        return os.path.join(
            plugin_dir,
            "features",
            "administrative_area",
            "data",
            "class.mbtiles",
        )

    def create_administrative_area_layer(self) -> Optional[QgsVectorTileLayer]:
        """行政区域データのベクタタイルレイヤーを作成"""

        mbtiles_path = self._get_mbtiles_path()

        QgsMessageLog.logMessage(
            f"MBTilesパス: {mbtiles_path}",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

        # MBTilesファイルの存在確認
        if not os.path.exists(mbtiles_path):
            QgsMessageLog.logMessage(
                f"MBTilesファイルが見つかりません: {mbtiles_path}",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )

        # MBTilesのURIの作成
        uri = f"type=mbtiles&url={mbtiles_path}"
        class3_layer = QgsVectorTileLayer(uri, LAYER_NAME)

        if not class3_layer.isValid():
            return None

        QgsMessageLog.logMessage(
            f"べクタータイルの作成: {class3_layer.name()}",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

        # レンダラーの適用
        renderer = QgsVectorTileBasicRenderer()
        polygon_style = QgsVectorTileBasicRendererStyle()
        polygon_style.setStyleName("Polygons")
        polygon_style.setEnabled(True)

        polygon_style.setGeometryType(Qgis.GeometryType.Polygon)

        # シンボルを作成
        polygon_symbol = QgsFillSymbol.createSimple(CLASS3_STYLE)

        # レイヤーにスタイルを適用
        polygon_style.setSymbol(polygon_symbol)
        renderer.setStyles([polygon_style])
        class3_layer.setRenderer(renderer)
        class3_layer.triggerRepaint()

        return class3_layer
