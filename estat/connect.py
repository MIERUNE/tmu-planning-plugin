"""
e-Stat APIの接続情報
"""

# TODO:以下のような感じで機能ごとにエンドポイントを追加する
# 人口メッシュ（1km）API
POPULATION_MESH_API_ENDPOINT = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"

# メッシュ形状データダウンロードURL
MESH_SHAPE_DOWNLOAD_URL = "https://www.e-stat.go.jp/gis/statmap-search/data"

GET_STATS_LIST_API_ENDPOINT = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList"

# ログメッセージ用プラグイン名
PLUGIN_NAME = "Green Infra Plugin"

# レスポンス文字エンコーディング
RESPONSE_ENCODING = "utf-8-sig"
