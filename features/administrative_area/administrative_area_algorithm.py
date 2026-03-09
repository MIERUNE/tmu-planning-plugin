"""
行政区域データの表示用モジュール
"""

import os
from typing import Literal, Optional

from qgis.core import (
    Qgis,
    QgsFillSymbol,
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

from ...utils.settings import PLUGIN_NAME
from .settings import BASE_STYLE, CLASS3_STYLES, CLASS5_STYLES, LAYER_NAME


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

    def _create_labeling(self) -> QgsVectorTileBasicLabeling:
        """N03_004属性を使用したラベリングを作成"""

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

        # 重複ラベルの軽減設定
        pal_settings.displayAll = False
        pal_settings.minimumFeatureSize = 100
        pal_settings.repeatDistance = 1000

        # ラベルスタイルの設定
        label_style = QgsVectorTileBasicLabelingStyle()
        label_style.setStyleName("municipal_label")
        label_style.setEnabled(True)
        label_style.setGeometryType(Qgis.GeometryType.Polygon)
        label_style.setLabelSettings(pal_settings)

        # 小さいポリゴン断片にラベルを出さない（面積ベースのフィルタ）
        label_style.setFilterExpression("$area > 10000")
        

        # ラベリングの作成と適用
        labeling = QgsVectorTileBasicLabeling()
        labeling.setStyles([label_style])
        return labeling

    def create_administrative_area_layer(
        self,
        class_type: Literal["base", "class3", "class5"],
    ) -> Optional[QgsVectorTileLayer]:
        """
        行政区域データのベクタタイルレイヤーを作成

        Args:
            class_type: 行政区域のクラスタイプ ("base", "class3" または "class5")
        Returns:
            QgsVectorTileLayer : 追加に成功した場合はレイヤーオブジェクト
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

        # ラベリングの適用
        labeling = self._create_labeling()
        administrative_area_layer.setLabeling(labeling)

        administrative_area_layer.triggerRepaint()

        return administrative_area_layer
