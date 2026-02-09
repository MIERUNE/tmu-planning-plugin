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
from .settings import CLASS3_STYLES, LAYER_NAME


class AdministrativeAreaAlgorithm:
    """行政区域データの取得クラス"""

    def __init__(self, iface):
        self.iface = iface

    def _get_data_source_path(self) -> str:
        """ベクタタイルのデータソースURIを構築する（暫定: ローカルMBTilesを参照。今後の対応：国交DPF配信開始後はAPIエンドポイントへの接続に置き換え予定）"""
        plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        QgsMessageLog.logMessage(
            f"MBTilesファイルのパスを取得: {plugin_dir}",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

        data_source_path = os.path.join(
            plugin_dir,
            "features",
            "administrative_area",
            "data",
            "class.mbtiles",
        )

        # MBTilesファイルの存在確認
        if not os.path.exists(data_source_path):
            QgsMessageLog.logMessage(
                f"MBTilesファイルが見つかりません: {data_source_path}",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )
            return None

        # MBTilesのURIの作成
        return f"type=mbtiles&url={data_source_path}"

    def create_administrative_area_layer(
        self, prefecture_name: str
    ) -> Optional[QgsVectorTileLayer]:
        """
        行政区域データのベクタタイルレイヤーを作成

        Args:
            prefecture_name: フィルタする都道府県名（例: "北海道"）
        """

        data_source_path = self._get_data_source_path()

        # レイヤーの作成
        layer_name = f"{LAYER_NAME}_{prefecture_name}"
        class3_layer = QgsVectorTileLayer(data_source_path, layer_name)

        if not class3_layer.isValid():
            return None

        # レンダラーの適用
        renderer = QgsVectorTileBasicRenderer()
        styles = []

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

        # レイヤーにスタイルを適用
        renderer.setStyles(styles)
        class3_layer.setRenderer(renderer)
        class3_layer.triggerRepaint()

        return class3_layer
