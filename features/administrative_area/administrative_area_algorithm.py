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

    # def _apply_style(self, layer: QgsVectorLayer):
    #     """レイヤーにスタイルを適用"""
    #     renderer = layer.renderer()
    #     symbol = renderer.symbol()
    #     style = CLASS3_STYLE

    #     # シンボルレイヤーを取得
    #     symbol_layer = symbol.symbolLayer(0)
    #     # symbol_layer.setStrokeColor(style["stroke_color"])
    #     # symbol_layer.setStrokeWidth(style["stroke_width"])
    #     # symbol_layer.setFillColor(style["fill_color"])

    #     if symbol_layer:
    #         # 文字列を QColor に変換
    #         # symbol_layer.setStrokeWidth(style["width"])
    #         symbol_layer.setStrokeColor(QColor(style["color"]))
    #         fill_color = QColor(style["color"])
    #         fill_color.setAlphaF(0.2)  # 塗りつぶしは薄く
    #         symbol_layer.setFillColor(fill_color)

    #     # 全体の透明度
    #     symbol.setOpacity(style["opacity"])

    #     layer.triggerRepaint()

    #     QgsMessageLog.logMessage(
    #         f"レイヤー '{layer.name()}' にスタイルを適用しました。",
    #         PLUGIN_NAME,
    #         level=Qgis.Info,
    #     )

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

        # # スタイルの設定
        # style = CLASS3_STYLE

        

        

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

        # self._apply_style(class3_layer)

        return class3_layer

    # def create_administrative_area_layer(self) -> Optional[QgsVectorLayer]:
    #     """行政区域データのベクタタイルレイヤーを作成"""

    #     mbtiles_path = self._get_mbtiles_path()

    #     print("MBTilesパス", mbtiles_path)
    #     QgsMessageLog.logMessage(
    #         f"MBTilesパス: {mbtiles_path}",
    #         PLUGIN_NAME,
    #         level=Qgis.Info,
    #     )

    #     # MBTilesファイルの存在確認
    #     if not os.path.exists(mbtiles_path):
    #         QgsMessageLog.logMessage(
    #             f"MBTilesファイルが見つかりません: {mbtiles_path}",
    #             PLUGIN_NAME,
    #             level=Qgis.Warning,
    #         )

    #     # MBTilesのURIの作成
    #     uri = f"{mbtiles_path}|layername=municipality"
    #     class3_layer = QgsVectorLayer(uri, LAYER_NAME, "ogr")

    #     if not class3_layer.isValid():
    #         class3_layer = QgsVectorLayer(mbtiles_path, LAYER_NAME, "ogr")
    #         if not class3_layer.isValid():
    #             return None

    #     self._apply_style(class3_layer)

    #     return class3_layer
