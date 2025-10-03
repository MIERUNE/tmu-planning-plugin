"""
ベースマップ管理機能モジュール
国土地理院のベクトルタイルレイヤーをQGISに追加し、地物の可視化を管理する機能を提供
"""

from typing import List, Optional

from qgis.core import (
    Qgis,
    QgsLayerTreeGroup,
    QgsProject,
    QgsSimpleFillSymbolLayer,
    QgsSymbol,
    QgsVectorTileBasicRenderer,
    QgsVectorTileBasicRendererStyle,
    QgsVectorTileLayer,
)
from qgis.PyQt.QtGui import QColor


class BaseMapAlgorithm:
    """ベースマップ管理クラス"""

    def __init__(self, iface):
        self.iface = iface

    # ====================
    # 1. グループ管理機能
    # ====================
    def create_layer_group(self, group_name: str) -> QgsLayerTreeGroup:
        """新しいレイヤーグループを作成
        Args:
            group_name (str): グループ名
        Returns:
            QgsLayerTreeGroup: 作成されたグループオブジェクト
        """
        root = QgsProject.instance().layerTreeRoot()
        return root.insertGroup(0, group_name)

    def get_layer_groups(self, group_name: str) -> List[QgsLayerTreeGroup]:
        """指定された名前の全グループを検索
        Args:
            group_name (str): 検索するグループ名
        Returns:
            list: 見つかった全グループのリスト
        """
        root = QgsProject.instance().layerTreeRoot()
        found_groups = []

        for child in root.children():
            if hasattr(child, "name") and child.name() == group_name:
                if hasattr(child, "addLayer"):
                    found_groups.append(child)

        return found_groups

    def remove_duplicate_groups(self, existing_groups: List[QgsLayerTreeGroup]) -> bool:
        """重複グループを削除
        Args:
            existing_groups (List[QgsLayerTreeGroup]): 削除対象のグループリスト
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            if not existing_groups:
                self.iface.messageBar().pushWarning(
                    "警告", "削除するグループが見つかりません"
                )
                return False

            root = QgsProject.instance().layerTreeRoot()
            for group in existing_groups:
                root.removeChildNode(group)

            return True
        except Exception as e:
            raise Exception(
                f"重複グループの削除中にエラーが発生しました: {str(e)}"
            ) from e

    # ====================
    # 2. レイヤー管理機能
    # ====================
    def add_basemap_layer(
        self,
        gsi_tile_url: str,
        layer_name: str,
        tile_zoom_min: int,
        tile_zoom_max: int,
        group: Optional[QgsLayerTreeGroup] = None,
    ) -> Optional[QgsVectorTileLayer]:
        """地理院ベクトルタイルレイヤーを追加
        Args:
            gsi_tile_url (str): 地理院タイルのURL
            layer_name (str): レイヤー名
            tile_zoom_min (int): 最小ズームレベル
            tile_zoom_max (int): 最大ズームレベル
            group (Optional[QgsLayerTreeGroup]): 追加先のグループ
        Returns:
            Optional[QgsVectorTileLayer]: 作成されたレイヤー
        """
        try:
            # TODO: URLクエリパラメータを安全に構築する方法へ変更
            uri = (
                f"type=xyz&url={gsi_tile_url}&zmax={tile_zoom_max}&zmin={tile_zoom_min}"
            )
            new_layer = QgsVectorTileLayer(uri, layer_name)

            if not new_layer.isValid():
                error_msg = (
                    new_layer.error().message() if new_layer.error() else "不明なエラー"
                )
                raise Exception(f"レイヤー作成失敗: {error_msg}")

            QgsProject.instance().addMapLayer(new_layer, False)
            if group:
                group.addLayer(new_layer)

            return new_layer
        except Exception as e:
            raise Exception(
                f"地理院ベクトルタイルレイヤーの作成に失敗しました: {str(e)}"
            ) from e

    def get_layers_from_group(
        self, group: QgsLayerTreeGroup
    ) -> List[QgsVectorTileLayer]:
        """グループ内から全てのレイヤーを取得
        Args:
            group (QgsLayerTreeGroup): レイヤーグループオブジェクト
        Returns:
            List[QgsVectorTileLayer]: 見つかったレイヤーのリスト
        """
        if not group:
            return []

        layers = []
        for child in group.children():
            if hasattr(child, "layer"):
                layer = child.layer()
                if layer:
                    layers.append(layer)

        return layers

    def get_layer_from_group(
        self,
        layer_name: str,
        group: QgsLayerTreeGroup,
    ) -> Optional[QgsVectorTileLayer]:
        """グループ内から特定のレイヤーを取得
        Args:
            layer_name (str): 取得するレイヤーの名前
            group (QgsLayerTreeGroup): レイヤーグループオブジェクト
        Returns:
            Optional[QgsVectorTileLayer]: 見つかったレイヤー
        """
        if not group:
            return None

        for child in group.children():
            if hasattr(child, "layer"):
                layer = child.layer()
                if layer and layer.name() == layer_name:
                    return layer
        return None

    # ====================
    # 3. レイヤー可視化機能
    # ====================
    def set_layer_visibility(
        self, basemap_layer: QgsVectorTileLayer, visible: bool
    ) -> bool:
        """レイヤーの表示状態を設定
        Args:
            basemap_layer (QgsVectorTileLayer): 対象のベースマップレイヤー
            visible (bool): 表示状態（True: 表示, False: 非表示）
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            root = QgsProject.instance().layerTreeRoot()
            layer_tree_layer = root.findLayer(basemap_layer.id())

            if layer_tree_layer:
                layer_tree_layer.setItemVisibilityChecked(visible)
            else:
                self.iface.messageBar().pushWarning(
                    "警告",
                    f"レイヤーツリーでレイヤー「{basemap_layer.name()}」が見つかりません",
                )
                return False

            # マップキャンバスを更新
            self.iface.mapCanvas().refresh()

            return True

        except Exception as e:
            raise Exception(
                f"レイヤー「{basemap_layer.name()}」の表示状態を設定中にエラーが発生しました: {str(e)}"
            ) from e

    def reset_layer_visibility(self, group: QgsLayerTreeGroup):
        """グループ内の全レイヤーの表示状態を非表示に設定
        Args:
            group (QgsLayerTreeGroup): 対象のレイヤーグループ
        """
        if not group:
            self.iface.messageBar().pushWarning("警告", "グループが指定されていません")
            return

        existing_layers = self.get_layers_from_group(group)
        for layer in existing_layers:
            if layer:
                self.set_layer_visibility(layer, False)

    # ====================
    # 4. 地物シンボロジ機能
    # ====================
    def add_feature_symbology(
        self,
        basemap_layer: QgsVectorTileLayer,
        feature_color: QColor,
        feature_settings: dict,
    ) -> bool:
        """地物シンボロジを追加
        Args:
            basemap_layer (QgsVectorTileLayer): 対象のベースマップレイヤー
            feature_color (QColor): 地物の色
            feature_settings (dict): 地物設定辞書
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        if not isinstance(basemap_layer, QgsVectorTileLayer):
            self.iface.messageBar().pushCritical(
                "エラー", "ベースマップレイヤーが正しく設定されていません"
            )
            return False

        try:
            styles = self.create_feature_style(feature_color, feature_settings)
            if not styles:
                return False

            renderer = QgsVectorTileBasicRenderer()
            renderer.setStyles(styles)
            basemap_layer.setRenderer(renderer)
            basemap_layer.triggerRepaint()
            self.iface.layerTreeView().refreshLayerSymbology(basemap_layer.id())
            return True
        except Exception as e:
            raise Exception(
                f"地物可視化の適用中にエラーが発生しました: {str(e)}"
            ) from e

    def create_feature_style(
        self, color: QColor, feature_settings: dict
    ) -> List[QgsVectorTileBasicRendererStyle]:
        """地物スタイルを生成
        Args:
            color (QColor): 地物の色
            feature_settings (dict): 地物設定辞書
        Returns:
            List[QgsVectorTileBasicRendererStyle]: 作成されたスタイルのリスト
        """
        try:
            styles = []
            features = feature_settings.get("features", [])
            for feature_item in features:
                style = self._create_renderer_style(feature_item, color)
                styles.append(style)
            return styles
        except Exception as e:
            raise Exception(
                f"地物スタイルの作成中にエラーが発生しました: {str(e)}"
            ) from e

    def _create_renderer_style(
        self, feature_item: dict, color: QColor
    ) -> QgsVectorTileBasicRendererStyle:
        """地物のレンダラースタイルを作成
        Args:
            feature_item (dict): 地物設定辞書の1項目
            color (QColor): 地物の色
        Returns:
            QgsVectorTileBasicRendererStyle: 作成されたスタイル
        """
        style = QgsVectorTileBasicRendererStyle()
        style.setStyleName(feature_item.get("description", ""))
        style.setLayerName(feature_item.get("source_layer", ""))
        style.setEnabled(True)
        style.setFilterExpression(f'"ftCode" = {feature_item.get("ft_code", 0)}')

        geometry_type = feature_item.get("geometry_type", "Polygon")
        if geometry_type == "Polygon":
            geom_type = Qgis.GeometryType.Polygon
            symbol = self._create_polygon_symbol(color)
        elif geometry_type == "Line":
            geom_type = Qgis.GeometryType.Line
            symbol = self._create_line_symbol(color)
        else:
            geom_type = Qgis.GeometryType.Point
            symbol = self._create_point_symbol(color)

        style.setGeometryType(geom_type)
        style.setSymbol(symbol)
        return style

    def _create_polygon_symbol(self, color: QColor) -> QgsSymbol:
        """ポリゴン用のシンボルを作成"""
        symbol = QgsSymbol.defaultSymbol(Qgis.GeometryType.Polygon)
        symbol.setColor(color)
        symbol.setOpacity(0.7)
        symbol_layer = symbol.symbolLayer(0)
        if isinstance(symbol_layer, QgsSimpleFillSymbolLayer):
            symbol_layer.setStrokeColor(color.darker(150))
            symbol_layer.setStrokeWidth(0.5)
        return symbol

    def _create_line_symbol(self, color: QColor) -> QgsSymbol:
        """ライン用のシンボルを作成"""
        symbol = QgsSymbol.defaultSymbol(Qgis.GeometryType.Line)
        symbol.setColor(color)
        symbol.setWidth(1.0)
        return symbol

    def _create_point_symbol(self, color: QColor) -> QgsSymbol:
        """ポイント用のシンボルを作成"""
        symbol = QgsSymbol.defaultSymbol(Qgis.GeometryType.Point)
        symbol.setColor(color)
        symbol.setSize(4.0)
        return symbol
