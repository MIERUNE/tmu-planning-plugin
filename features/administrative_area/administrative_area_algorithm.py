"""
行政区域データの表示用モジュール
"""

import os
from typing import Literal, Optional

from qgis.core import (
    Qgis,
    QgsFillSymbol,
    QgsMarkerSymbol,
    QgsMessageLog,
    QgsPalLayerSettings,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorTileBasicLabeling,
    QgsVectorTileBasicLabelingStyle,
    QgsVectorTileBasicRenderer,
    QgsVectorTileBasicRendererStyle,
    QgsVectorTileLayer,
)
from qgis.PyQt.QtGui import QColor, QFont

from ...utils.settings import PLUGIN_NAME, ZOOM9_SCALE_THRESHOLD
from .settings import (
    BASE_STYLE,
    CLASS3_STYLES,
    CLASS5_STYLES,
    LABEL_LAYER_NAME,
    LAYER_NAME,
)



class AdministrativeAreaAlgorithm:
    """行政区域データの取得クラス"""

    def __init__(self, iface):
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

    def _create_labeling(self) -> Optional[QgsVectorTileLayer]:
        """labels.mbtilesからラベル用レイヤーを作成"""
        plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        labels_path = os.path.join(
            plugin_dir, "features", "administrative_area", "data", "labels.mbtiles"
        )

        if not os.path.exists(labels_path):
            QgsMessageLog.logMessage(
                f"ラベルMBTilesファイルが見つかりません: {labels_path}",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )
            return None

        uri = f"type=mbtiles&url={labels_path}"
        label_layer = QgsVectorTileLayer(uri, LABEL_LAYER_NAME)

        if not label_layer.isValid():
            return None

        # ポイントを透明にするレンダラー
        renderer = QgsVectorTileBasicRenderer()
        renderer_style = QgsVectorTileBasicRendererStyle()
        renderer_style.setStyleName("centroids_invisible")
        renderer_style.setLayerName("centroids")
        renderer_style.setEnabled(True)
        renderer_style.setGeometryType(Qgis.GeometryType.Point)
        symbol = QgsMarkerSymbol.createSimple(
            {"color": "0,0,0,0", "outline_color": "0,0,0,0", "size": "0"}
        )
        renderer_style.setSymbol(symbol)
        renderer.setStyles([renderer_style])
        label_layer.setRenderer(renderer)

        # テキストフォーマットの設定
        text_format = QgsTextFormat()
        text_format.setFont(QFont("Noto Sans CJK JP"))
        text_format.setSize(10)
        text_format.setColor(QColor(50, 50, 50))

        # テキストバッファ（白縁取り）の設定
        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(True)
        buffer_settings.setSize(1.0)
        buffer_settings.setColor(QColor(255, 255, 255))
        text_format.setBuffer(buffer_settings)

        # ラベルの表示フィールドを設定
        pal_settings = QgsPalLayerSettings()
        pal_settings.fieldName = "N03_004"
        pal_settings.setFormat(text_format)

        # ラベルスタイルの設定
        label_style = QgsVectorTileBasicLabelingStyle()
        label_style.setStyleName("municipal_label")
        label_style.setLayerName("centroids")
        label_style.setEnabled(True)
        label_style.setGeometryType(Qgis.GeometryType.Point)
        label_style.setLabelSettings(pal_settings)

        # ラベリングの適用
        labeling = QgsVectorTileBasicLabeling()
        labeling.setStyles([label_style])
        label_layer.setLabeling(labeling)
        
        # ズームレベル９以下では表示しない
        label_layer.setScaleBasedVisibility(True)
        label_layer.setMinimumScale(ZOOM9_SCALE_THRESHOLD)

        label_layer.triggerRepaint()
        return label_layer

    def create_administrative_area_layer(
        self,
        class_type: Literal["base", "class3", "class5"],
    ) -> Optional[tuple[QgsVectorTileLayer, QgsVectorTileLayer]]:
        """
        行政区域データのベクタタイルレイヤーを作成

        Args:
            class_type: 行政区域のクラスタイプ ("base", "class3" または "class5")
        Returns:
            tuple[QgsVectorTileLayer, QgsVectorTileLayer] : (ポリゴンレイヤー, ラベルレイヤー)
        """

        mbtiles_path = self._get_mbtiles_path()

        # MBTilesファイルの存在確認
        if not os.path.exists(mbtiles_path):
            QgsMessageLog.logMessage(
                f"MBTilesファイルが見つかりません: {mbtiles_path}",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )

        # MBTilesのURIの作成
        uri = f"type=mbtiles&url={mbtiles_path}"
        layer_name = f"{LAYER_NAME}_{class_type}"
        administrative_area_layer = QgsVectorTileLayer(uri, layer_name)

        if not administrative_area_layer.isValid():
            return None

        # レンダラーの適用
        renderer = QgsVectorTileBasicRenderer()
        styles = []

        # class_typeに応じて設定を選択
        CLASS_TYPE_MAP = {
            "class3": ("class3info", CLASS3_STYLES),
            "class5": ("class5nofo", CLASS5_STYLES),
            "base": ("base", BASE_STYLE),
        }

        attr_name, styles_dict = CLASS_TYPE_MAP[class_type]

        # 共通処理
        for attr_value, style_props in styles_dict.items():
            polygon_style = QgsVectorTileBasicRendererStyle()
            polygon_style.setStyleName(f"{attr_name}_{attr_value}")
            polygon_style.setEnabled(True)
            polygon_style.setGeometryType(Qgis.GeometryType.Polygon)

            # フィルタ式を設定
            if class_type != "base":
                polygon_style.setFilterExpression(f"{attr_name} = {attr_value}")

            # シンボルを作成
            polygon_symbol = QgsFillSymbol.createSimple(style_props)
            polygon_style.setSymbol(polygon_symbol)
            styles.append(polygon_style)

        # レイヤーにスタイルを適用
        renderer.setStyles(styles)
        administrative_area_layer.setRenderer(renderer)
        administrative_area_layer.triggerRepaint()

        # ラベルレイヤーの作成
        label_layer = self._create_labeling()
        if not label_layer:
            return None

        return (administrative_area_layer, label_layer)
