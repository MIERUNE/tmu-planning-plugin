import json
from typing import Optional

from qgis.core import Qgis, QgsMessageLog, QgsProject

from ..umi_shiru.client import (
    BBOX_BUFFER_DEGREES,
    CITY_DIVISION_CONFIG,
)
from ..umi_shiru.fishing_port.fishing_port_algorithm import FishingPortAlgorithm
from ..utils.estat.bbox import calculate_municipality_bbox
from ..utils.estat.client import AdministrativeAreaClient
from ..utils.settings import CITY_DEFAULT_BOUNDS, PLUGIN_NAME
from .base_workflow import BaseWorkflow


class FishingPortWorkflow(BaseWorkflow):
    """漁港区域データ取得・可視化専用ワークフロー"""

    def __init__(self, iface):
        """
        漁港区域ワークフローの初期化
        Args:
            iface: QGISインターフェース
        """
        super().__init__(iface)
        self.algorithm = FishingPortAlgorithm(iface)
        self.estat_client = AdministrativeAreaClient(PLUGIN_NAME)

    def _get_display_name(
        self, municipality_code: str, municipality_name: Optional[str] = None
    ) -> str:
        """
        市区町村の表示名を生成
        Args:
            municipality_code (str): 市区町村コード
            municipality_name (str, optional): 市区町村名
        Returns:
            str: 表示名（例：「札幌市（01100）」）
        """
        if municipality_name:
            return f"{municipality_name}（{municipality_code}）"
        else:
            return municipality_code

    def _validate_geojson_data(
        self,
        geojson_data: str,
        display_name: str,
    ) -> bool:
        """
        GeoJSONデータの内容を検証し、featuresが存在するかチェック
        Args:
            geojson_data (str): GeoJSON文字列
            display_name (str): 表示名（例：「札幌市（01100）」）
        Returns:
            bool: featuresが存在する場合True、存在しない場合False
        """
        try:
            geojson_obj = json.loads(geojson_data)
            features = geojson_obj.get("features", [])

            if not features:
                message = f"市区町村「{display_name}」の範囲には漁港区域データが存在しません。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Info)
                self.iface.messageBar().pushMessage("情報", message, level=Qgis.Info)
                return False

            QgsMessageLog.logMessage(
                f"漁港区域データを取得しました（{len(features)} features）",
                PLUGIN_NAME,
                level=Qgis.Info,
            )
            return True

        except json.JSONDecodeError:
            message = "取得したデータの形式が正しくありません。"
            QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
            self.iface.messageBar().pushMessage("エラー", message, level=Qgis.Warning)
            return False

    def _calculate_municipality_bounds(
        self,
        municipality_code: str,
        display_name: str,
    ) -> Optional[dict]:
        """
        市区町村のbboxを取得し、バッファを追加した境界範囲を計算
        Args:
            municipality_code (str): 市区町村コード
            display_name (str): 表示名（例：「札幌市（01100）」）
        Returns:
            dict: バッファ付きの境界範囲、または None（計算失敗時）
        """
        # 行政区域ポリゴンを取得してbboxを計算
        municipality_layer = self.estat_client.fetch_municipality_polygon(
            municipality_code
        )
        calculated_bbox = calculate_municipality_bbox(municipality_layer)

        if not calculated_bbox:
            # APIからデータが取得できない場合、デフォルト境界範囲を使用
            if municipality_code in CITY_DEFAULT_BOUNDS:
                calculated_bbox = CITY_DEFAULT_BOUNDS[municipality_code]
            else:
                message = f"市区町村「{display_name}」のbbox計算に失敗しました。デフォルト境界範囲も設定されていません。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage(
                    "エラー", message, level=Qgis.Warning
                )
                return None

        # 市区町村bboxにバッファを追加（約1km）
        bounds = {
            "min_lon": calculated_bbox["min_lon"] - BBOX_BUFFER_DEGREES,
            "min_lat": calculated_bbox["min_lat"] - BBOX_BUFFER_DEGREES,
            "max_lon": calculated_bbox["max_lon"] + BBOX_BUFFER_DEGREES,
            "max_lat": calculated_bbox["max_lat"] + BBOX_BUFFER_DEGREES,
        }

        return bounds

    def execute(
        self,
        api_key: Optional[str],
        municipality_code: Optional[str],
        municipality_name: Optional[str],
    ) -> bool:
        """
        漁港区域ワークフローを実行し、漁港区域レイヤーをQGISに追加する
        Args:
            api_key (str): 海しるAPIキー
            municipality_code (str, optional): 市区町村コード（5桁）
            municipality_name (str, optional): 市区町村名
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 1. パラメータの準備とバリデーション
            if not api_key:
                message = "海しるAPIキーが未設定のため、漁港区域データの処理をスキップします。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("警告", message, level=Qgis.Warning)
                return False

            if not municipality_code:
                message = "漁港区域を表示するには市区町村を選択してください。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("警告", message, level=Qgis.Warning)
                return False

            display_name = self._get_display_name(municipality_code, municipality_name)

            # 市区町村の境界範囲を計算
            bounds = self._calculate_municipality_bounds(
                municipality_code, display_name
            )
            if not bounds:
                return False

            # 2. データ取得（分割取得が必要な市区町村かチェック）
            if municipality_code in CITY_DIVISION_CONFIG:
                division_config = CITY_DIVISION_CONFIG[municipality_code]
                division_count = division_config["division_count"]
                geojson_data = self.algorithm.fetch_data_divided(
                    api_key=api_key,
                    bounds=bounds,
                    division_count=division_count,
                )
            else:
                geojson_data = self.algorithm.fetch_data(api_key=api_key, bounds=bounds)

            if not geojson_data:
                message = "海しるAPIからのデータ取得に失敗しました。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage(
                    "エラー", message, level=Qgis.Warning
                )
                return False

            # 3. GeoJSONデータの検証
            if not self._validate_geojson_data(geojson_data, display_name):
                return False

            # 4. レイヤー作成
            layer_name = f"漁港区域_{display_name}"
            layer = self.algorithm.create_layer(geojson_data, layer_name)

            # 5. QGISプロジェクトに追加
            QgsProject.instance().addMapLayer(layer)

            # 6. UI更新
            self.iface.mapCanvas().refresh()

            success_message = f"漁港区域レイヤー '{layer_name}' が正常に追加されました"
            QgsMessageLog.logMessage(success_message, PLUGIN_NAME, level=Qgis.Success)
            self.iface.messageBar().pushMessage(
                "成功", success_message, level=Qgis.Success
            )
            return True

        except Exception as e:
            error_message = f"漁港区域の可視化中にエラーが発生: {str(e)}"
            QgsMessageLog.logMessage(error_message, PLUGIN_NAME, level=Qgis.Critical)
            self.iface.messageBar().pushMessage(
                "エラー", error_message, level=Qgis.Critical
            )
            return False
