"""
行政区域データの表示用モジュール
"""

import os
from typing import Literal, Optional

from qgis.core import (
    Qgis,
    QgsFillSymbol,
    QgsMessageLog,
    QgsVectorTileBasicRenderer,
    QgsVectorTileBasicRendererStyle,
    QgsVectorTileLayer,
)

from ...utils.settings import PLUGIN_NAME
from .settings import CLASS3_STYLES, CLASS5_STYLES, LAYER_NAME


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

    def create_administrative_area_layer(
        self, prefecture_name: str, class_type: Literal["class3", "class5"]
    ) -> Optional[QgsVectorTileLayer]:
        """
        行政区域データのベクタタイルレイヤーを作成

        Args:
            prefecture_name: フィルタする都道府県名（例: "北海道"）
            class_type: 行政区域のクラスタイプ ("3" または "5")
        Returns:
            QgsVectorTileLayer : 追加に成功した場合はレイヤーオブジェクト
        """

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
        layer_name = f"{LAYER_NAME}_{class_type}_{prefecture_name}"
        administrative_area_layer = QgsVectorTileLayer(uri, layer_name)

        if not administrative_area_layer.isValid():
            return None

        # レンダラーの適用
        renderer = QgsVectorTileBasicRenderer()
        styles = []

        if class_type == "class3":
            for class3info_value, style_props in CLASS3_STYLES.items():
                polygon_style = QgsVectorTileBasicRendererStyle()
                polygon_style.setStyleName(f"class3info_{class3info_value}")
                polygon_style.setEnabled(True)

                polygon_style.setGeometryType(Qgis.GeometryType.Polygon)

                # 都道府県名でフィルタ
                polygon_style.setFilterExpression(
                    f"class3info = {class3info_value} AND N03_001 = '{prefecture_name}'"
                )

                # シンボルを作成
                polygon_symbol = QgsFillSymbol.createSimple(style_props)
                polygon_style.setSymbol(polygon_symbol)
                styles.append(polygon_style)

        if class_type == "class5":
            for class5info_value, style_props in CLASS5_STYLES.items():
                polygon_style = QgsVectorTileBasicRendererStyle()
                polygon_style.setStyleName(f"class5info_{class5info_value}")
                polygon_style.setEnabled(True)

                polygon_style.setGeometryType(Qgis.GeometryType.Polygon)

                # 都道府県名でフィルタ
                polygon_style.setFilterExpression(
                    f"class5nofo = {class5info_value} AND N03_001 = '{prefecture_name}'"
                )

                # シンボルを作成
                polygon_symbol = QgsFillSymbol.createSimple(style_props)
                polygon_style.setSymbol(polygon_symbol)
                styles.append(polygon_style)

        # レイヤーにスタイルを適用
        renderer.setStyles(styles)
        administrative_area_layer.setRenderer(renderer)
        administrative_area_layer.triggerRepaint()

        return administrative_area_layer
