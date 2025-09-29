"""
海岸線データ固有の設定
"""

# 固定の緯度経度範囲（テスト用：北海道周辺）
DEFAULT_BOUNDS = {"min_lon": 140.5, "min_lat": 42.0, "max_lon": 141.5, "max_lat": 43.5}

# レイヤースタイル設定
COASTLINE_STYLE = {
    "color": "#0066CC",  # 海岸線の色（青）
    "width": 0.5,  # 線の太さ
    "opacity": 0.8,  # 透明度
}
