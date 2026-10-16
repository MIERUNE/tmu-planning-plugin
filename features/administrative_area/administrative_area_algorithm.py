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
    QgsDataSourceUri,
    QgsVectorTileLayer,
)
from qgis.PyQt.QtGui import QColor, QFont

from ...utils.auth import get_api_header_authcfg
from ...utils.settings import PLUGIN_NAME, ZOOM10_SCALE_THRESHOLD
from .client import MlitDpfClient
from .connect import (
    DATA_IDS,
    MLIT_DPF_API_KEY_HEADER,
    MLIT_DPF_AUTHCFG_NAME,
    TILE_ZOOM_MAX,
    TILE_ZOOM_MIN,
)
from .settings import (
    BASE_STYLE,
    CLASS3_STYLES,
    CLASS5_STYLES,
    CLASS6_STYLES,
    LABEL_LAYER_NAME,
    LAYER_NAME,
)

ClassType = Literal["base", "class3", "class5", "class6"]


class AdministrativeAreaAlgorithm:
    """行政区域データの取得クラス"""

    def __init__(self, iface):
        self.iface = iface
        # 国交DPFから取得したタイルURL（dataIDごと、取得失敗時は None）
        self._tile_url_cache: dict[str, Optional[str]] = {}
        # ローカルデータを使用した旨を通知済みか
        self._fallback_notified = False

    def clear_tile_url_cache(self):
        """タイルURLのキャッシュをクリア（可視化の実行ごとに呼び出す）"""
        self._tile_url_cache.clear()
        self._fallback_notified = False

    def _fetch_tile_url(self, data_id: str, api_key: str) -> Optional[str]:
        """国交DPFからベクトルタイルURLを取得
        取得時、取得失敗共にキャッシュし、同じ実行中に同じdataIDへ再リクエストしない
        """
        if data_id in self._tile_url_cache:
            return self._tile_url_cache[data_id]

        tile_url = None
        authcfg = get_api_header_authcfg(
            MLIT_DPF_AUTHCFG_NAME, MLIT_DPF_API_KEY_HEADER, api_key
        )
        if authcfg:
            client = MlitDpfClient(authcfg)
            tile_url = client.fetch_tile_url(data_id)
            # タイルの配信元（S3）だけ通信を遮断されている場合も取得失敗として扱う
            if tile_url and not client.can_access_tiles(tile_url):
                tile_url = None

        self._tile_url_cache[data_id] = tile_url
        return tile_url

    def _get_source_uri(self, class_type: ClassType, api_key: str) -> Optional[str]:
        """
        行政区域ポリゴンのデータソースURIを取得

        国交DPFのベクトルタイルを優先し、取得できない場合はローカルのMBTilesを使う。
        6クラス分類はローカルデータがないため、取得できない場合は None を返す。
        """
        data_id = DATA_IDS["class6" if class_type == "class6" else "class3_5"]
        tile_url = self._fetch_tile_url(data_id, api_key)

        if tile_url:
            uri = QgsDataSourceUri()
            uri.setParam("type", "xyz")
            uri.setParam("url", tile_url)
            uri.setParam("zmin", str(TILE_ZOOM_MIN))
            uri.setParam("zmax", str(TILE_ZOOM_MAX))
            return bytes(uri.encodedUri()).decode()

        if class_type == "class6":
            return None

        mbtiles_path = self._get_mbtiles_path()
        if not self._fallback_notified:
            message = "国土交通データプラットフォームから行政区域データを取得できなかったため、ローカルデータを使用しました。"
            QgsMessageLog.logMessage(
                f"{message} {mbtiles_path}",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Warning,
            )
            self.iface.messageBar().pushMessage(
                "警告", message, level=Qgis.MessageLevel.Warning
            )
            self._fallback_notified = True
        if not os.path.exists(mbtiles_path):
            QgsMessageLog.logMessage(
                f"MBTilesファイルが見つかりません: {mbtiles_path}",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Warning,
            )
        return f"type=mbtiles&url={mbtiles_path}"

    def _get_mbtiles_path(self) -> str:
        """MBTilesファイルのパスを取得（国交DPFから取得できない場合のフォールバック用）"""
        plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        return os.path.join(
            plugin_dir,
            "features",
            "administrative_area",
            "data",
            "class.mbtiles",
        )

    def _create_label_layer(self) -> Optional[QgsVectorTileLayer]:
        """labels.mbtilesからラベル用レイヤーを作成"""
        plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        labels_path = os.path.join(
            plugin_dir, "features", "administrative_area", "data", "labels.mbtiles"
        )

        if not os.path.exists(labels_path):
            QgsMessageLog.logMessage(
                f"ラベルMBTilesファイルが見つかりません: {labels_path}",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Warning,
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

        # ズームレベル10未満では表示しない
        label_layer.setScaleBasedVisibility(True)
        label_layer.setMinimumScale(ZOOM10_SCALE_THRESHOLD)

        label_layer.triggerRepaint()
        return label_layer

    def create_administrative_area_layer(
        self,
        class_type: ClassType,
        api_key: str,
    ) -> Optional[tuple[QgsVectorTileLayer, Optional[QgsVectorTileLayer]]]:
        """
        行政区域データのベクタタイルレイヤーを作成

        Args:
            class_type: 行政区域のクラスタイプ ("base", "class3", "class5" または "class6")
            api_key: 国土交通データプラットフォームのAPIキー
        Returns:
            tuple[QgsVectorTileLayer, Optional[QgsVectorTileLayer]] : (ポリゴンレイヤー, ラベルレイヤー)
                ラベルレイヤーが作成できない場合は None
        """

        uri = self._get_source_uri(class_type, api_key)
        if not uri:
            return None

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
            "class6": ("class", CLASS6_STYLES),
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
        label_layer = self._create_label_layer()

        return (administrative_area_layer, label_layer)
