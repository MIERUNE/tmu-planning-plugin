"""
e-Stat API - 行政区域bbox計算ユーティリティ
"""

from typing import Dict, Optional

from qgis.core import QgsVectorLayer


def calculate_municipality_bbox(layer: QgsVectorLayer) -> Optional[Dict[str, float]]:
    """
    行政区域ポリゴンレイヤーからbboxを計算
    Args:
        layer (QgsVectorLayer): 行政区域ポリゴンレイヤー
    Returns:
        dict: bbox座標 {'min_lon', 'min_lat', 'max_lon', 'max_lat'} または None
    """
    if layer is None or not layer.isValid():
        return None

    # ポリゴンからbboxを取得
    extent = layer.extent()
    bbox = {
        "min_lon": extent.xMinimum(),
        "min_lat": extent.yMinimum(),
        "max_lon": extent.xMaximum(),
        "max_lat": extent.yMaximum(),
    }

    return bbox
