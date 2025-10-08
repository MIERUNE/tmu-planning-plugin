"""
不動産情報ライブラリAPIの接続情報
"""

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

# ログメッセージ用プラグイン名
PLUGIN_NAME = "Green Infra Plugin"

# レスポンス文字エンコーディング
RESPONSE_ENCODING = "utf-8-sig"

# ズームレベル９のスケール閾値
ZOOM9_SCALE_THRESHOLD = 1160000
