"""
不動産情報ライブラリAPIの接続情報
"""

# APIキーを付与するヘッダー名
REINFOLIB_API_KEY_HEADER = "Ocp-Apim-Subscription-Key"

# QGIS認証マネージャーに登録する認証設定の名前
REINFOLIB_AUTHCFG_NAME = "GreenInfraPlannerJP_Reinfolib"

# APIキーの有効性を確認するために取得するタイル（geojson、ズーム13の関東付近）
CHECK_TILE_QUERY = "?response_format=geojson&z=13&x=7272&y=3225"

# 都道府県市区町村一覧取得APIエンドポイント
AREA_LIST_API_ENDPOINT = "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT002"

# TODO:以下のような感じで機能ごとにエンドポイントを追加する
# 都市計画決定GISデータ（都市計画区域/区域区分）API
URBAN_PLANNING_AREA_API_ENDPOINT = (
    "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT001"
)

# 用途地域の都市計画決定GISデータ（用途地域）API
ZONING_DISTRICT_AREA_API_ENDPOINT = (
    "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT002"
)

# 地区計画の都市計画決定GISデータ（地区計画）API
DISTRICT_PLAN_AREA_API_ENDPOINT = (
    "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT023"
)

# 立地適正化計画区域データAPI
LOCATION_NORMALIZATION_PLAN_API_ENDPOINT = (
    "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT003"
)

# 自然公園地域データAPI
NATURE_RESERVE_AREA_API_ENDPOINT = (
    "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT019"
)

# 人口集中地区（DID）データAPI
DID_AREA_API_ENDPOINT = "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT031"

# 高度利用地区データAPI
HEIGHTENED_USE_DISTRICT_API_ENDPOINT = (
    "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT024"
)

# レスポンス文字エンコーディング
RESPONSE_ENCODING = "utf-8-sig"
