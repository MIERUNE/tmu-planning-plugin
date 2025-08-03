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
    "land": QColor(128, 128, 128, 100),
    "water": QColor(0, 0, 255, 100),
    "highway": QColor(255, 0, 0, 100),
    "major_road": QColor(255, 165, 0, 100),
    "building": QColor(200, 200, 200, 100),
}

# ====================
# 地物設定定数
# ====================
LAYER_FEATURE_SETTINGS = {
    "land": {
        "features": [
            {
                "ft_code": "7401",
                "source_layer": "landforma",
                "geometry_type": "Polygon",
                "description": "湿地帯",
            },
            {
                "ft_code": "7403",
                "source_layer": "landforma",
                "geometry_type": "Polygon",
                "description": "砂礫地（領域が明瞭な場合）",
            },
        ],
        "layer_name": "国土",
        "zoom_min": 8,
        "zoom_max": 16,
    },
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
        "zoom_min": 4,
        "zoom_max": 16,
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
        "zoom_min": 14,
        "zoom_max": 16,
    },
}
