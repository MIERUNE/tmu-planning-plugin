"""
ベースマップワークフロー
ベースマップの追加から地物可視化までの一連の処理を管理
"""

from typing import Dict, Optional

from qgis.PyQt.QtGui import QColor
from qgis.core import QgsLayerTreeGroup

from ..basemap.basemap_algorithm import BaseMapAlgorithm
from ..basemap.basemap_settings import (
    GSI_TILE_URL,
    GROUP_LAYER_NAME,
    DEFAULT_COLOR,
    LAYER_FEATURE_SETTINGS,
)
from .base_workflow import BaseWorkflow


class BasemapWorkflow(BaseWorkflow):
    """ベースマップ処理のワークフロー"""

    def __init__(self, iface):
        super().__init__(iface)
        self.basemap_manager = BaseMapAlgorithm(iface)

    # ==================
    # 1. メイン実行関数
    # ==================
    def execute(self, selected_features: Optional[Dict] = None) -> bool:
        """ベースマップワークフローを実行
        Args:
            selected_features: 選択された地物と色の辞書
        Returns:
            Dict[str, Any]: 実行結果
        """
        try:
            # Step 1: ベースマップグループを設定
            group = self._setup_basemap_group()
            if not group:
                raise Exception("ベースマップグループの設定に失敗しました")

            # グループ内の不足しているレイヤーを取得
            needed_layers = self._get_missing_layers(group)

            if needed_layers:
                # Step 2: グループ内にレイヤーを作成
                self._create_layers(group, needed_layers)

                # Step 3: グループ内のレイヤーに地物シンボロジを追加
                self._configure_layer_symbologies(group)

            # Step 4: 選択された地物レイヤーの表示状態＆色を変更
            self.basemap_manager.reset_layer_visibility(group)
            if selected_features:
                self._visualize_selected_features(group, selected_features)

            # マップキャンバスを更新
            self.iface.mapCanvas().refresh()

            return True
        except Exception as e:
            self.iface.messageBar().pushCritical("ベースマップ処理エラー", str(e))
            return False

    # ==================
    # 2. グループ管理
    # ==================
    def _setup_basemap_group(self) -> QgsLayerTreeGroup:
        """ベースマップグループを設定
        Returns:
            QgsLayerTreeGroup: 作成されたグループオブジェクト
        """
        # 既存のグループを取得
        existing_groups = self.basemap_manager.get_layer_groups(GROUP_LAYER_NAME)
        group_count = len(existing_groups)

        if group_count == 0:
            group = self.basemap_manager.create_layer_group(GROUP_LAYER_NAME)
        elif group_count == 1:
            group = existing_groups[0]
        else:
            # 重複グループを削除
            self.basemap_manager.remove_duplicate_groups(existing_groups)
            # 新規グループを作成
            group = self.basemap_manager.create_layer_group(GROUP_LAYER_NAME)

        if not group:
            raise Exception("地理院ベクトルタイルグループの作成に失敗しました")

        return group

    # ==================
    # 3. レイヤー管理
    # ==================
    def _get_missing_layers(self, group: QgsLayerTreeGroup) -> list:
        """グループ内の不足しているレイヤーを取得
        Args:
            group (QgsLayerTreeGroup): 対象のレイヤーグループ
        Returns:
            list: 不足しているレイヤー名のリスト
        """
        existing_layer_names = {
            layer.name()
            for layer in self.basemap_manager.get_layers_from_group(group) or []
        }
        required_layer_names = {
            settings["layer_name"] for settings in LAYER_FEATURE_SETTINGS.values()
        }
        needed_layers = list(required_layer_names - existing_layer_names)

        return needed_layers

    def _create_layers(self, group: QgsLayerTreeGroup, needed_layers: list) -> None:
        """グループ内にレイヤーを作成
        Args:
            group (QgsLayerTreeGroup): 対象のレイヤーグループ
            needed_layers (list): 作成するレイヤー名のリスト
        """
        for _feature_type, settings in LAYER_FEATURE_SETTINGS.items():
            layer_name = settings["layer_name"]

            if layer_name in needed_layers:
                layer = self.basemap_manager.add_basemap_layer(
                    gsi_tile_url=GSI_TILE_URL,
                    layer_name=layer_name,
                    tile_zoom_min=settings["zoom_min"],
                    tile_zoom_max=settings["zoom_max"],
                    group=group,
                )

                if layer is not None:
                    # デフォルトで非表示に設定
                    self.basemap_manager.set_layer_visibility(layer, False)
                else:
                    raise Exception(f"レイヤー「{layer_name}」の作成に失敗しました")

    # ==================
    # 4. シンボロジ管理
    # ==================
    def _configure_layer_symbologies(self, group: QgsLayerTreeGroup) -> None:
        """グループ内のレイヤーに地物シンボロジを追加
        Args:
            group (QgsLayerTreeGroup): 対象のレイヤーグループ
        """
        for feature_type, settings in LAYER_FEATURE_SETTINGS.items():
            # グループから該当するレイヤーを取得
            basemap_layer = self.basemap_manager.get_layer_from_group(
                layer_name=settings["layer_name"],
                group=group,
            )

            if basemap_layer:
                default_color = DEFAULT_COLOR.get(
                    feature_type, QColor(128, 128, 128, 100)
                )

                # レイヤーに地物シンボロジを追加
                success = self.basemap_manager.add_feature_symbology(
                    basemap_layer=basemap_layer,
                    feature_color=default_color,
                    feature_settings=settings,
                )

                if not success:
                    raise Exception(
                        f"地物「{settings['layer_name']}」のシンボロジ設定に失敗しました"
                    )

            else:
                raise Exception(f"レイヤー「{settings['layer_name']}」が見つかりません")

    # ==================
    # 5. 可視化処理
    # ==================
    def _visualize_selected_features(
        self, group: QgsLayerTreeGroup, selected_features: dict
    ) -> None:
        """選択された地物レイヤーの表示状態＆色を変更
        Args:
            group (QgsLayerTreeGroup): 対象のレイヤーグループ
            selected_features (dict): 選択された地物とその色の辞書
        """
        for feature_type, color in selected_features.items():
            if feature_type in LAYER_FEATURE_SETTINGS:
                feature_settings = LAYER_FEATURE_SETTINGS[feature_type]

                # グループから該当するレイヤーを取得
                basemap_layer = self.basemap_manager.get_layer_from_group(
                    layer_name=feature_settings["layer_name"],
                    group=group,
                )

                if basemap_layer:
                    # 選択された色でシンボロジを更新
                    success = self.basemap_manager.add_feature_symbology(
                        basemap_layer=basemap_layer,
                        feature_color=color,
                        feature_settings=feature_settings,
                    )

                    if not success:
                        raise Exception(
                            f"地物「{feature_settings['layer_name']}」の可視化に失敗しました"
                        )

                    # レイヤーを表示状態にする
                    self.basemap_manager.set_layer_visibility(basemap_layer, True)
                else:
                    raise Exception(
                        f"レイヤー「{feature_settings['layer_name']}」が見つかりません"
                    )
