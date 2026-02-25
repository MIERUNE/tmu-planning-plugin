"""
行政区域データ固有の設定
"""

LAYER_NAME = "行政区域"

# ベースの行政区域ポリゴン（白）のスタイル
BASE_STYLE: dict[str, dict[str, str]] = {
    "base": {
        "color": "255,255,255,120",  # 白
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    }
}

CLASS3_STYLES: dict[str, dict[str, str]] = {
    "1": {
        "color": "255,204,204,180",  # パステルピンク
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "2": {
        "color": "255,250,156,180",  # パステルイエロー
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "3": {
        "color": "204,255,153,180",  # パステルイエローグリーン
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
}

CLASS5_STYLES: dict[str, dict[str, str]] = {
    "1": {
        "color": "255,130,182,180",  # ピンク
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "2": {
        "color": "255,204,131,180",  # オレンジ
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "3": {
        "color": "130,245,255,180",  # 水色
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "4": {
        "color": "140,130,255,180",  # 紫
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "5": {
        "color": "182,255,130,180",  # グリーン
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
}
