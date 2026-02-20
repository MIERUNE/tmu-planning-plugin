"""
ベースマップ設定定数モジュール
地理院ベクトルタイルと地物設定に関する定数を管理
"""

from qgis.PyQt.QtGui import QColor

# ====================
# 地理院ベクトルタイル定数
# ====================
GSI_TILE_URL = "https://cyberjapandata.gsi.go.jp/xyz/experimental_bvmap/{z}/{x}/{y}.pbf"
GROUP_LAYER_NAME = "ベースマップ"

# ====================
# レイヤーのデフォルトカラー設定
# ====================
DEFAULT_COLOR = {
    "water": QColor(0, 0, 255, 100),
    "highway": QColor(255, 0, 0, 100),
    "major_road": QColor(255, 165, 0, 100),
    "building": QColor(200, 200, 200, 100),
}

# ====================
# ズームレベルとスケールの閾値
# ====================
ZOOM_SCALE_THRESHOLDS = {
    4: 37000000,
    7: 4600000,
    8: 2300000,
    9: 1160000,
    14: 36250,
    16: 9000,
    18: 2300,
}

# ====================
# 地物設定定数
# ====================
LAYER_FEATURE_SETTINGS = {
    "water": {
        "features": [
            {
                "ft_code": "5000",
                "source_layer": "waterarea",
                "geometry_type": "Polygon",
                "description": "水域",
            },
        ],
        "layer_name": "水域",
        "zoom_min": 9,
        "zoom_max": 16,
        "display_zoom_min": 9,
    },
    "highway": {
        "features": [
            {
                "ft_code": "52703",
                "source_layer": "road",
                "geometry_type": "Line",
                "description": "高速自動車道",
            },
            {
                "ft_code": "52704",
                "source_layer": "road",
                "geometry_type": "Line",
                "description": "高速自動車道トンネル",
            },
        ],
        "layer_name": "高速道路",
        "zoom_min": 4,
        "zoom_max": 7,
        "display_zoom_min": 7,
    },
    "major_road": {
        "features": [
            {
                "ft_code": "52701",
                "source_layer": "road",
                "geometry_type": "Line",
                "description": "主要な道路",
            }
        ],
        "layer_name": "主要道路",
        "zoom_min": 4,
        "zoom_max": 7,
        "display_zoom_min": 9,
    },
    "building": {
        "features": [
            {
                "ft_code": "3101",
                "source_layer": "building",
                "geometry_type": "Polygon",
                "description": "普通建物",
            },
            {
                "ft_code": "3102",
                "source_layer": "building",
                "geometry_type": "Polygon",
                "description": "堅ろう建物",
            },
            {
                "ft_code": "3103",
                "source_layer": "building",
                "geometry_type": "Polygon",
                "description": "高層建物",
            },
            {
                "ft_code": "3111",
                "source_layer": "building",
                "geometry_type": "Polygon",
                "description": "普通無壁舎",
            },
            {
                "ft_code": "3112",
                "source_layer": "building",
                "geometry_type": "Polygon",
                "description": "堅ろう無壁舎",
            },
        ],
        "layer_name": "建物ポリゴン",
        "zoom_min": 0,
        "zoom_max": 16,
        "display_zoom_min": 14,
    },
}
