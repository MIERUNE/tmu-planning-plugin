import requests
import json
from qgis.core import Qgis, QgsMessageLog
from typing import Optional

# --- 設定項目 ---
# あなたのe-StatアプリケーションIDに置き換えてください
APP_ID = "" 
# 検索したいメッシュコード（リスト形式に変更）
MESH_CODES = ["6441", "6440"]  # 例として2つのメッシュコードを指定
# ログを見やすくするためのタグ
LOG_TAG = "eStatJsonTest"

def get_dataset_id(mesh_code: str) -> Optional[str]:
    """
    指定されたメッシュコードを使い、e-Stat APIからデータセットIDを取得します。
    結果はQGISログメッセージパネルに出力します。

    Args:
        mesh_code (str): 検索する一次メッシュコード

    Returns:
        Optional[str]: 取得したデータセットID。失敗した場合はNone。
    """
    api_endpoint = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList"
    search_word = f"M{mesh_code} AND 世界測地系(1KMメッシュ)"
    params = {
        "appId": APP_ID, "lang": "J", "surveyYears": "2020",
        "statsCode": "00200521", "searchKind": "2", 
        "searchWord": search_word, "limit": 10
    }

    try:
        QgsMessageLog.logMessage(f"APIリクエストを開始します (メッシュコード: {mesh_code})", LOG_TAG, level=Qgis.Info)
        response = requests.get(api_endpoint, params=params, timeout=60)
        response.raise_for_status()
        json_data = response.json()
        
        # --- @id 抽出処理 ---
        # 安全にネストされた辞書の値を取得
        datalist_inf = json_data.get("GET_STATS_LIST", {}).get("DATALIST_INF", {})
        table_info = datalist_inf.get("TABLE_INF")
        
        dataset_id = None
        # table_infoが存在するかチェック
        if table_info:
            # 検索結果が複数の場合はリスト、1件の場合は辞書になるため両対応
            if isinstance(table_info, list) and len(table_info) > 0:
                # リストの場合、最初の要素から@idを取得
                dataset_id = table_info[0].get("@id")
            elif isinstance(table_info, dict):
                # 辞書の場合、直接@idを取得
                dataset_id = table_info.get("@id")
        
        if dataset_id:
            QgsMessageLog.logMessage(f"dataSetId '{dataset_id}' の取得に成功しました。", LOG_TAG, level=Qgis.Success)
            return dataset_id
        else:
            QgsMessageLog.logMessage(f"メッシュコード '{mesh_code}' のdataSetIdが見つかりませんでした。", LOG_TAG, level=Qgis.Warning)
            return None

    except requests.exceptions.RequestException as e:
        QgsMessageLog.logMessage(f"APIリクエストでエラーが発生しました (メッシュコード: {mesh_code}): {e}", LOG_TAG, level=Qgis.Critical)
        return None
    except json.JSONDecodeError:
        QgsMessageLog.logMessage(f"レスポンスのJSONパースに失敗しました (メッシュコード: {mesh_code})。レスポンス内容: \n{response.text}", LOG_TAG, level=Qgis.Critical)
        return None
    except Exception as e:
        QgsMessageLog.logMessage(f"予期せぬエラーが発生しました (メッシュコード: {mesh_code}): {e}", LOG_TAG, level=Qgis.Critical)
        return None

# --- スクリプトの実行 ---
def run_extraction_test_for_multiple_meshes():
    """複数のメッシュコードに対して抽出処理のテストを実行する"""
    
    QgsMessageLog.logMessage(f"--- 複数メッシュの処理を開始します ---", LOG_TAG, level=Qgis.Info)
    
    # 取得したIDを格納する辞書 {メッシュコード: dataSetId}
    retrieved_ids = {}

    # リスト内の各メッシュコードでループ処理
    for code in MESH_CODES:
        QgsMessageLog.logMessage(f"--- メッシュ: {code} の処理を開始 ---", LOG_TAG, level=Qgis.Info)
        dataset_id = get_dataset_id(code)
        retrieved_ids[code] = dataset_id  # 成功しても失敗(None)しても結果を格納
    
    QgsMessageLog.logMessage(f"--- 全ての処理が完了しました ---", LOG_TAG, level=Qgis.Info)
    QgsMessageLog.logMessage(f"最終結果: {retrieved_ids}", LOG_TAG, level=Qgis.Info)

run_extraction_test_for_multiple_meshes()

