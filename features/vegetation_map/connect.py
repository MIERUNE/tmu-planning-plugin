"""
環境ジオポータルの接続情報
"""

# 環境ジオポータル Hub API（データセットのメタデータ取得。FeatureServer URL や itemId を解決する）
HUB_DATASET_API_URL = "https://geoportal.env.go.jp/api/v3/datasets/{dataset_id}"

# 現存植生図2024 の Hub データセット ID（地域ブロック別）
VEGETATION_MAP_DATASET_IDS = {
    "hokkaido": "ceb726273cc94ccfb4fc9eab9e6d244a_0",
    "tohoku": "bc367787e89d42ba93b96c1535047ba0_0",
    "kanto": "490a48eaae6d464f8feacc50ad5bf6e5_0",
    "hokuriku": "9a6efc6acf0d4abb8d83fc25a1ae58b8_0",
    "chubu": "0d209199d8a2446cb88b805cc21844dc_0",
    "kinki": "10e54c08de264b3b84d79e1083bc4597_0",
    "chushikoku": "7ec6e383cb294d80888bf08610f4b0f2_0",
    "kyushu_okinawa": "5eaab78b57af4614be9c12b0f32e1b55_0",
}

# 現存植生図2024スタイル設定ファイル（veg2024style.qml を含む zip）の Hub データセット ID
STYLE_DATASET_ID = "368329d069ab4e70a0b1938eb050ad07"

# ArcGIS Online のアイテムデータ取得URL（Hub API で解決した itemId を埋める）
ARCGIS_ITEM_DATA_URL = (
    "https://www.arcgis.com/sharing/rest/content/items/{item_id}/data"
)

# 範囲クエリのエンドポイント（レイヤーURLに付加）
QUERY_PATH = "/query"

# FeatureServer の maxRecordCount（1リクエストで返る最大件数）
PAGE_SIZE = 2000

# レスポンス文字エンコーディング
RESPONSE_ENCODING = "utf-8-sig"
