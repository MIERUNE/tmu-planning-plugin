import math
from typing import Dict, List, Tuple

from qgis.core import Qgis, QgsMessageLog


def calculate_tile_coords(
    bbox: Dict[str, float], min_zoom: int, max_zoom: int
) -> List[Tuple[int, int, int]]:
    """
    指定されたBBOXとズームレベル範囲をカバーするタイル座標(Z, X, Y)のリストを計算する。

    Args:
        bbox (Dict[str, float]): BBOX ('xmin', 'ymin', 'xmax', 'ymax'を持つ辞書)
        min_zoom (int): 計算する最小ズームレベル
        max_zoom (int): 計算する最大ズームレベル

    Returns:
        List[Tuple[int, int, int]]: タイル座標(z, x, y)のタプルリスト
    """
    all_tiles = []
    for z in range(min_zoom, max_zoom + 1):
        # BBOXの左上（北西）のタイル番号を計算
        top_left_x, top_left_y = _deg2num(bbox["ymax"], bbox["xmin"], z)
        # BBOXの右下（南東）のタイル番号を計算
        bottom_right_x, bottom_right_y = _deg2num(bbox["ymin"], bbox["xmax"], z)

        for x in range(top_left_x, bottom_right_x + 1):
            for y in range(top_left_y, bottom_right_y + 1):
                all_tiles.append((z, x, y))

        QgsMessageLog.logMessage(
            f"取得するタイル数を計算しました: Zoom: {z}, Tiles: {len(all_tiles)}",
            level=Qgis.Info,
        )

    return all_tiles


def _deg2num(lat_deg: float, lon_deg: float, zoom: int) -> Tuple[int, int]:
    """緯度経度からタイル座標(X, Y)を計算する内部関数"""
    lat_rad = math.radians(lat_deg)
    n = 2.0**zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)


# # 結果をコンソールに出力
# print("--- Tile Calculation Results ---")
# print(f"Total tiles calculated: {len(tile_results)}")
# # 最初の20件だけ表示してみる
# print(f"First 20 tiles: {tile_results[:20]}")
# print("------------------------------")
