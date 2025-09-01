"""
都道府県市区町村一覧取得APIの設定ファイル
"""
import json
import os
from typing import List, Tuple

# 不動産情報ライブラリAPIキー
# TODO: 次の段階でAPIキー入力フォームと連携させる
REAL_ESTATE_API_KEY = ""
# REAL_ESTATE_API_KEY = "8ef021ba2e7241158260dc2de39d650b"

# 都道府県一覧（マニュアル記載の固定リスト）
PREFECTURE_LIST = [
    ("01", "北海道"),
    ("02", "青森県"),
    ("03", "岩手県"),
    ("04", "宮城県"),
    ("05", "秋田県"),
    ("06", "山形県"),
    ("07", "福島県"),
    ("08", "茨城県"),
    ("09", "栃木県"),
    ("10", "群馬県"),
    ("11", "埼玉県"),
    ("12", "千葉県"),
    ("13", "東京都"),
    ("14", "神奈川県"),
    ("15", "新潟県"),
    ("16", "富山県"),
    ("17", "石川県"),
    ("18", "福井県"),
    ("19", "山梨県"),
    ("20", "長野県"),
    ("21", "岐阜県"),
    ("22", "静岡県"),
    ("23", "愛知県"),
    ("24", "三重県"),
    ("25", "滋賀県"),
    ("26", "京都府"),
    ("27", "大阪府"),
    ("28", "兵庫県"),
    ("29", "奈良県"),
    ("30", "和歌山県"),
    ("31", "鳥取県"),
    ("32", "島根県"),
    ("33", "岡山県"),
    ("34", "広島県"),
    ("35", "山口県"),
    ("36", "徳島県"),
    ("37", "香川県"),
    ("38", "愛媛県"),
    ("39", "高知県"),
    ("40", "福岡県"),
    ("41", "佐賀県"),
    ("42", "長崎県"),
    ("43", "熊本県"),
    ("44", "大分県"),
    ("45", "宮崎県"),
    ("46", "鹿児島県"),
    ("47", "沖縄県"),
]

# 市区町村JSONファイル名
MUNICIPALITIES_JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "municipalities.json")

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