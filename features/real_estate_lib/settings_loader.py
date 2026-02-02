"""
不動産情報ライブラリのデータ読み込みユーティリティ
"""

import json
from typing import List, Tuple

from .settings import MUNICIPALITIES_JSON_FILE


def load_municipalities_from_json() -> dict:
    """JSONファイルから市区町村データを読み込み
    Returns:
        dict: 市区町村データ辞書 {"都道府県コード": [["市区町村コード", "市区町村名"], ...], ...}
    """
    try:
        with open(MUNICIPALITIES_JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"市区町村JSONファイル読み込みエラー: {e}")
        return {}


def get_municipalities_by_prefecture(prefecture_code: str) -> List[Tuple[str, str]]:
    """指定都道府県の市区町村リストをJSONファイルから取得
    Args:
        prefecture_code (str): 都道府県コード（例: "13"）
    Returns:
        List[Tuple[str, str]]: 市区町村リスト [("市区町村コード", "市区町村名"), ...]
    """
    municipalities_data = load_municipalities_from_json()

    # JSONファイルからデータを取得
    municipality_list = municipalities_data.get(prefecture_code, [])

    # データが配列の配列形式 [["01100", "札幌市"], ...] なので、
    # タプルのリスト形式 [("01100", "札幌市"), ...] に変換
    if municipality_list:
        return [(code, name) for code, name in municipality_list]
    else:
        return []
