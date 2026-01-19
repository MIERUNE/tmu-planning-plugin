"""
e-Stat APIの接続情報
"""
# メッシュタイプ別の設定
MESH_TYPE_CONFIG = {
    "3rd": {
        "search_keyword": "世界測地系(1KMメッシュ)",
        "mesh_request_params": "S",
    },
    "4th": {
        "search_keyword": "世界測地系(500Mメッシュ)",
        "mesh_request_params": "H"
    }
}

# 人口メッシュAPI
POPULATION_MESH_API_ENDPOINT = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"

# メッシュ形状データダウンロードURL
MESH_SHAPE_DOWNLOAD_URL = "https://www.e-stat.go.jp/gis/statmap-search/data"

# 統計情報一覧取得APIエンドポイント
GET_STATS_LIST_API_ENDPOINT = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList"

# ログメッセージ用プラグイン名
PLUGIN_NAME = "GreenInfraPlannerJP"

# レスポンス文字エンコーディング
RESPONSE_ENCODING = "utf-8-sig"
