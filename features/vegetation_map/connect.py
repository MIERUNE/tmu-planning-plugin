"""
環境ジオポータルの接続情報
"""

# 現存植生図2024 FeatureServer レイヤーURL（地域ブロック別）
VEGETATION_MAP_API_ENDPOINTS = {
    "hokkaido": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk1gdb/FeatureServer/0",
    "tohoku": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk2gdb/FeatureServer/0",
    "kanto": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk3/FeatureServer/0",
    "hokuriku": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk4/FeatureServer/0",
    "chubu": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk5/FeatureServer/0",
    "kinki": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk6/FeatureServer/0",
    "chushikoku": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk7gdb/FeatureServer/0",
    "kyushu_okinawa": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk8gdb/FeatureServer/0",
}

# 範囲クエリのエンドポイント（レイヤーURLに付加）
QUERY_PATH = "/query"

# 現存植生図2024スタイル設定ファイルのダウンロードURL
STYLE_ZIP_URL = "https://www.arcgis.com/sharing/rest/content/items/368329d069ab4e70a0b1938eb050ad07/data"

# FeatureServer の maxRecordCount（1リクエストで返る最大件数）
PAGE_SIZE = 2000

# レスポンス文字エンコーディング
RESPONSE_ENCODING = "utf-8-sig"
