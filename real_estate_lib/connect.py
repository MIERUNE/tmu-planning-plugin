"""
不動産情報ライブラリAPIの接続情報
"""

# 都道府県市区町村一覧取得APIエンドポイント
AREA_LIST_API_ENDPOINT = "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT002"

# TODO:以下のような感じで機能ごとにエンドポイントを追加する
# 不動産価格（取引価格・成約価格）情報取得API
REAL_ESTATE_PRICE_API_ENDPOINT = "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT001"

# ログメッセージ用プラグイン名
PLUGIN_NAME = "Green Infra Plugin"

# レスポンス文字エンコーディング
RESPONSE_ENCODING = "utf-8-sig"