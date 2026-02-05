"""
行政区域データ固有の設定
"""

from qgis.PyQt.QtGui import QColor


LAYER_NAME = "行政区域 class3"


CLASS3_STYLE = {
    "stroke_color": QColor(255, 68, 68),
    "stroke_width": 1.5,  
    "fill_color": QColor(255, 204, 204, 26),  
    "opacity": 0.7,  
}
