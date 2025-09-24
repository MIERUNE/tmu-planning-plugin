"""
海しるAPIの接続情報
"""

# 海しるAPI 海岸線取得エンドポイント
COASTLINE_API_ENDPOINT = "https://api.msil.go.jp/coastline-type-ESI/v2/MapServer"

# TODO: 以下のような感じで他の海洋データAPIエンドポイントを追加する
# 海しるAPI 海岸区域取得エンドポイント
# COASTAL_AREA_API_ENDPOINT = "https://api.msil.go.jp/coastal-area/v1/MapServer"

# ログメッセージ用プラグイン名
PLUGIN_NAME = "TMU Planning Plugin"

# レスポンス文字エンコーディング
RESPONSE_ENCODING = "utf-8-sig"