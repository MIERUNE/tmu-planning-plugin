"""
国土交通データプラットフォーム（国交DPF）APIの接続情報
"""

# 利用者向けAPIのエンドポイント
MLIT_DPF_API_ENDPOINT = "https://data-platform.mlit.go.jp/api/v1/"

# APIキーを付与するヘッダー名
MLIT_DPF_API_KEY_HEADER = "apikey"

# QGIS認証マネージャーに登録する認証設定の名前
MLIT_DPF_AUTHCFG_NAME = "GreenInfraPlannerJP_MLIT_DPF"

# 豪雨発生の変化と土地利用に基づく全国自治体の類型化（カタログ：sip3rd）
DATASET_ID = "sip3rd_gi"
DATA_IDS = {
    # 3クラス・5クラス分類
    "class3_5": "0bccc80b-c676-4ae2-85e5-373836f5130b",
    # 6クラス分類
    "class6": "93e40aa0-58b6-4db0-84b4-eb738415c436",
}

# ベクトルタイルのURLを取得するGraphQLクエリ（{dataset_id}・{data_id}を埋め込んで使う）
VECTOR_TILES_QUERY = """
query {{
  data(dataSetID: "{dataset_id}", dataID: "{data_id}") {{
    totalNumber
    getDataResults {{
      id
      title
      vectorTiles {{ title style }}
    }}
  }}
}}
"""

# ベクトルタイルの配信ズームレベル
TILE_ZOOM_MIN = 6
TILE_ZOOM_MAX = 12
