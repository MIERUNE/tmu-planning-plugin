import json
from typing import Optional

import requests
from qgis.core import Qgis, QgsMessageLog

from ..utils.estat.bbox import calculate_municipality_bbox
from ..utils.estat.client import AdministrativeAreaClient
from ..utils.estat.mesh import get_mesh_codes_from_bbox
from .connect import (
    GET_STATS_LIST_API_ENDPOINT,
    PLUGIN_NAME,
)


class GetDatasetId:
    def __init__(self, iface):
        self.iface = iface

    def _get_mesh_codes(self, municipality_code: str):
        """
        指定された自治体コードからメッシュコードを取得
        Args:
            municipality_code (str): 自治体コード
        """
        QgsMessageLog.logMessage(
            f"[_get_mesh_codes] メッシュコードの取得開始 (municipality_code: {municipality_code})",
            PLUGIN_NAME,
            level=Qgis.Info,
        )
        # e-Statに行政区域ポリゴンが存在しない自治体コードの場合
        if municipality_code == "01100":
            mesh_codes = ["6441", "6541"]
            return mesh_codes

        else:
            # e-Statから行政区域ポリゴンレイヤーを取得
            client = AdministrativeAreaClient(PLUGIN_NAME)
            # === ログ追加 B ===
            QgsMessageLog.logMessage(
                "[_get_mesh_codes] 行政区域ポリゴンの取得開始...",
                PLUGIN_NAME,
                level=Qgis.Info,
            )
            municipality_layer = client.fetch_municipality_polygon(municipality_code)
            QgsMessageLog.logMessage(municipality_code, PLUGIN_NAME, level=Qgis.Info)
            # === ログ追加 C ===
            QgsMessageLog.logMessage(
                "[_get_mesh_codes] 行政区域ポリゴンの取得完了",
                PLUGIN_NAME,
                level=Qgis.Info,
            )

            # 取得したレイヤーが有効か確認
            if municipality_layer is not None and municipality_layer.isValid():
                # BBOXを計算
                bbox = None
                bbox = calculate_municipality_bbox(municipality_layer)

                if bbox:
                    mesh_codes = get_mesh_codes_from_bbox(bbox)
                    QgsMessageLog.logMessage(
                        f"取得したメッシュコード: {mesh_codes}",
                        PLUGIN_NAME,
                        level=Qgis.Success,
                    )
                    return mesh_codes
                else:
                    QgsMessageLog.logMessage(
                        "BBOXの計算に失敗しました。", PLUGIN_NAME, level=Qgis.Warning
                    )
                    return []

    def _get_dataset_id(self, mesh_code: str, api_key: str) -> Optional[str]:
        """
        指定されたメッシュコードを使い、e-Stat APIからデータセットIDを取得。
        Args:
            mesh_code (str): 検索する一次メッシュコード
        Returns:
            Optional[str]: 取得したデータセットID。失敗した場合はNone。
        """
        search_word = f"M{mesh_code} AND 世界測地系(1KMメッシュ)"
        params = {
            "appId": api_key,
            "lang": "J",
            "surveyYears": "2020",
            "statsCode": "00200521",
            "searchKind": "2",
            "searchWord": search_word,
        }

        try:
            QgsMessageLog.logMessage(
                f"APIリクエストを開始します (メッシュコード: {mesh_code})",
                PLUGIN_NAME,
                level=Qgis.Info,
            )
            response = requests.get(
                GET_STATS_LIST_API_ENDPOINT, params=params, timeout=60
            )
            response.raise_for_status()
            json_data = response.json()

            # @id 抽出処理
            table_info = (
                json_data.get("GET_STATS_LIST", {})
                .get("DATALIST_INF", {})
                .get("TABLE_INF")
            )

            dataset_id = None
            # table_infoが存在するかチェック
            if table_info:
                if isinstance(table_info, list) and len(table_info) > 0:
                    # リストの場合、最初の要素から@idを取得
                    dataset_id = table_info[0].get("@id")
                elif isinstance(table_info, dict):
                    # 辞書の場合、直接@idを取得
                    dataset_id = table_info.get("@id")

            if dataset_id:
                QgsMessageLog.logMessage(
                    f"dataSetId '{dataset_id}' の取得に成功しました。",
                    PLUGIN_NAME,
                    level=Qgis.Success,
                )
                return dataset_id
            else:
                QgsMessageLog.logMessage(
                    f"メッシュコード '{mesh_code}' のdataSetIdが見つかりませんでした。",
                    PLUGIN_NAME,
                    level=Qgis.Warning,
                )
                return None

        except requests.exceptions.RequestException as e:
            QgsMessageLog.logMessage(
                f"APIリクエストでエラーが発生しました (メッシュコード: {mesh_code}): {e}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return None
        except json.JSONDecodeError:
            QgsMessageLog.logMessage(
                f"レスポンスのJSONパースに失敗しました (メッシュコード: {mesh_code})。レスポンス内容: \n{response.text}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return None
        except Exception as e:
            QgsMessageLog.logMessage(
                f"予期せぬエラーが発生しました (メッシュコード: {mesh_code}): {e}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return None

    def fetch_dataset_ids_for_municipality(
        self, municipality_code: str, api_key: str
    ) -> dict[str, str]:
        """
        自治体コードを元にメッシュコードを取得し、各メッシュコードに対応する
        データセットIDのリストを取得する。
        Args:
            municipality_code (str): 自治体コード
        Returns:
           -> dict[str, str]: 取得したデータセットIDの辞書
        """
        mesh_codes = self._get_mesh_codes(municipality_code)
        QgsMessageLog.logMessage(
            f"取得したメッシュコードリスト: {mesh_codes}", PLUGIN_NAME, level=Qgis.Info
        )

        if not mesh_codes:
            QgsMessageLog.logMessage(
                "有効なメッシュコードが取得できなかったため、処理を終了します。",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )
            return {}

        dataset_id_dict = {}
        for mesh_code in mesh_codes:
            dataset_id = self._get_dataset_id(mesh_code, api_key)
            if dataset_id:
                dataset_id_dict[mesh_code] = dataset_id

        QgsMessageLog.logMessage(
            f"最終的に取得したデータセットIDリスト: {dataset_id_dict}",
            PLUGIN_NAME,
            level=Qgis.Success,
        )
        return dataset_id_dict