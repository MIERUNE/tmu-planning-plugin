import json
from typing import Optional

from qgis.core import Qgis, QgsMessageLog, QgsProject

from ..umi_shiru.coastline.coastline_algorithm import CoastlineAlgorithm
from ..umi_shiru.connect import PLUGIN_NAME
from .base_workflow import BaseWorkflow


class CoastlineWorkflow(BaseWorkflow):
    """海岸線データ取得・可視化ワークフロー"""

    def __init__(self, iface):
        super().__init__(iface)
        self.algorithm = CoastlineAlgorithm(iface)

    def _validate_geojson_data(self, geojson_data: str, municipality_code: str) -> bool:
        """
        GeoJSONデータの内容を検証し、featuresが存在するかチェック
        Args:
            geojson_data (str): GeoJSON文字列
            municipality_code (str): 市区町村コード
        Returns:
            bool: featuresが存在する場合True、存在しない場合False
        """
        try:
            geojson_obj = json.loads(geojson_data)
            features = geojson_obj.get("features", [])

            if not features:
                message = f"市区町村 {municipality_code} の範囲には海岸線データが存在しません。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Info)
                self.iface.messageBar().pushMessage("情報", message, level=Qgis.Info)
                return False

            QgsMessageLog.logMessage(
                f"海岸線データを取得しました（{len(features)} features）",
                PLUGIN_NAME,
                level=Qgis.Info,
            )
            return True

        except json.JSONDecodeError:
            message = "取得したデータの形式が正しくありません。"
            QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
            self.iface.messageBar().pushMessage("エラー", message, level=Qgis.Warning)
            return False

    def _calculate_municipality_bounds(self, municipality_code: str) -> Optional[dict]:
        """
        市区町村のbboxを取得し、バッファを追加した境界範囲を計算
        Args:
            municipality_code (str): 市区町村コード
        Returns:
            dict: バッファ付きの境界範囲、または None（計算失敗時）
        """
        QgsMessageLog.logMessage(
            f"市区町村コード {municipality_code} のbboxを計算します...",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

        calculated_bbox = self.algorithm.get_municipality_bbox(municipality_code)
        if not calculated_bbox:
            message = f"市区町村 {municipality_code} のbbox計算に失敗しました。"
            QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
            self.iface.messageBar().pushMessage("エラー", message, level=Qgis.Warning)
            return None

        # 市区町村bboxにバッファを追加（約1km）
        buffer = 0.01
        bounds = {
            "min_lon": calculated_bbox["min_lon"] - buffer,
            "min_lat": calculated_bbox["min_lat"] - buffer,
            "max_lon": calculated_bbox["max_lon"] + buffer,
            "max_lat": calculated_bbox["max_lat"] + buffer,
        }

        QgsMessageLog.logMessage(
            f"市区町村bbox（バッファ付き）: {bounds}",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

        return bounds

    def execute(
        self,
        api_key: Optional[str],
        municipality_code: Optional[str] = None,
    ) -> bool:
        """
        ワークフローを実行し、海岸線レイヤーをQGISに追加する
        Args:
            api_key (str): 海しるAPIキー
            municipality_code (str, optional): 市区町村コード（5桁）
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 1. パラメータの準備とバリデーション
            if not api_key:
                message = (
                    "海しるAPIキーが未設定のため、海岸線データの処理をスキップします。"
                )
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage("警告", message, level=Qgis.Warning)
                return False

            if not municipality_code or len(municipality_code) != 5:
                message = "海岸線を表示するには市区町村を選択してください。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Info)
                self.iface.messageBar().pushMessage("情報", message, level=Qgis.Info)
                return False

            # 市区町村の境界範囲を計算
            bounds = self._calculate_municipality_bounds(municipality_code)
            if not bounds:
                return False

            QgsMessageLog.logMessage(
                "海岸線データを取得します...", PLUGIN_NAME, level=Qgis.Info
            )

            # 2. データ取得
            geojson_data = self.algorithm.fetch_coastline_data(
                api_key=api_key, bounds=bounds
            )
            if not geojson_data:
                message = "海しるAPIからのデータ取得に失敗しました。"
                QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Warning)
                self.iface.messageBar().pushMessage(
                    "エラー", message, level=Qgis.Warning
                )
                return False

            # 3. GeoJSONデータの検証
            if not self._validate_geojson_data(geojson_data, municipality_code):
                return False

            # 4. レイヤー作成
            layer_name = f"海岸線_{municipality_code}"
            layer = self.algorithm.create_coastline_layer(geojson_data, layer_name)

            # 5. QGISプロジェクトに追加
            QgsProject.instance().addMapLayer(layer)

            # 6. UI更新
            self.iface.mapCanvas().refresh()

            success_message = f"海岸線レイヤー '{layer_name}' が正常に追加されました"
            QgsMessageLog.logMessage(success_message, PLUGIN_NAME, level=Qgis.Success)
            self.iface.messageBar().pushMessage(
                "成功", success_message, level=Qgis.Success
            )
            return True

        except Exception as e:
            error_message = f"海岸線の可視化中にエラーが発生: {str(e)}"
            QgsMessageLog.logMessage(error_message, PLUGIN_NAME, level=Qgis.Critical)
            self.iface.messageBar().pushMessage(
                "エラー", error_message, level=Qgis.Critical
            )
            return False
