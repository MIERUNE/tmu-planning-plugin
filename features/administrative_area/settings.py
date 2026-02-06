"""
行政区域データ固有の設定
"""

LAYER_NAME = "行政区域class3"

CLASS3_STYLES: dict[str, dict[str, str]] = {
    "1": {
        "color": "255,204,204,180",
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "2": {
        "color": "255,255,147,180",
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
    "3": {
        "color": "204,255,153,180",
        "outline_color": "120,120,120,255",
        "outline_width": "0.7",
    },
}
