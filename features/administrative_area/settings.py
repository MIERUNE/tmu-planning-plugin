"""
行政区域データ固有の設定
"""

LAYER_NAME = "行政区域"
LABEL_LAYER_NAME = "行政区域_自治体名"

# ベースの行政区域ポリゴン（白）のスタイル
BASE_STYLE: dict[str, dict[str, str]] = {
    "base": {
        "color": "255,255,255,120",  # 白
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    }
}

# 3クラス分類
CLASS3_STYLES: dict[str, dict[str, str]] = {
    "1": {
        "color": "128,128,128,180",  # #808080 都市型
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "2": {
        "color": "182,255,0,180",  # #B6FF00 農地緑地型
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "3": {
        "color": "0,178,33,180",  # #00B221 森林型
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
}

CLASS3_LABELS: dict[str, str] = {
    "1": "1：都市型",
    "2": "2：農地緑地型",
    "3": "3：森林型",
}

# 5クラス分類
CLASS5_STYLES: dict[str, dict[str, str]] = {
    "1": {
        "color": "0,178,33,180",  # #00B221 森林型
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "2": {
        "color": "128,128,128,180",  # #808080 都市型
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "3": {
        "color": "182,255,0,180",  # #B6FF00 農地緑地型
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "4": {
        "color": "132,216,147,180",  # #84D893 森林型やや都市より
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "5": {
        "color": "189,255,130,180",  # #BDFF82 農地緑地型やや都市より
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
}

CLASS5_LABELS: dict[str, str] = {
    "1": "1：森林型",
    "2": "2：都市型",
    "3": "3：農地緑地型",
    "4": "4：森林型やや都市より",
    "5": "5：農地緑地型やや都市より",
}

# 6クラス分類（国交DPF API利用ガイドの配色）
CLASS6_STYLES: dict[str, dict[str, str]] = {
    "1": {
        "color": "255,0,0,180",  # red
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "2": {
        "color": "231,166,224,180",  # #E7A6E0
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "3": {
        "color": "0,123,0,180",  # #007B00
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "4": {
        "color": "255,255,127,180",  # #FFFF7F
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "5": {
        "color": "77,179,0,180",  # #4DB300
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "6": {
        "color": "255,165,0,180",  # orange
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
}

CLASS6_LABELS: dict[str, str] = {
    "1": "1：豪雨が著しく増加しているが、農地Eco-DRRが期待できる",
    "2": "2：豪雨は変わらないが、洪水に対して脆弱",
    "3": "3：豪雨がやや増加しているが、農地Eco-DRRが期待できる",
    "4": "4：豪雨がやや増加しているのみ",
    "5": "5：豪雨が増加しているが、Eco-DRRが大きく期待できる",
    "6": "6：豪雨はほぼ変わらないが、洪水に対して脆弱",
}
