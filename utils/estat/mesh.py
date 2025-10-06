import math

def _get_primary_mesh(lat, lon):
    """
    指定された緯度経度から一次メッシュコード（4桁）を計算します。
    """
    p = math.floor(lat * 1.5)
    q = math.floor(lon - 100)
    return f"{int(p):02d}{int(q):02d}"

def get_mesh_codes_from_bbox(bbox_dict):
    """
    BBOX（辞書型）を引数として受け取り、
    その範囲をカバーする一次メッシュコードのリストを返します。
    
    Args:
        bbox_dict (dict): min_lon, min_lat, max_lon, max_lat をキーに持つ辞書
        
    Returns:
        list: メッシュコードの文字列を格納したソート済みのリスト
    """
    # BBOXをカバーするメッシュを格納するセット
    mesh_codes = set()

    # 引数で渡されたBBOXの四隅の座標をリストアップ
    points_to_check = [
        (bbox_dict["min_lat"], bbox_dict["min_lon"]),
        (bbox_dict["min_lat"], bbox_dict["max_lon"]),
        (bbox_dict["max_lat"], bbox_dict["min_lon"]),
        (bbox_dict["max_lat"], bbox_dict["max_lon"]),
    ]

    # 各コーナーのメッシュコードを計算してセットに追加
    for lat, lon in points_to_check:
        mesh_codes.add(_get_primary_mesh(lat, lon))

    # 結果をソートしてリストとして返す
    return sorted(list(mesh_codes))

# --- ここから下は実行テスト用のコード ---

# 1. 札幌市のBBOXを定義
sapporo_bbox = {
    "min_lon": 140.9575,
    "min_lat": 42.7631,
    "max_lon": 141.6525,
    "max_lat": 43.1994,
}

# 2. 作成した関数を呼び出し、結果を取得
primary_meshes = get_mesh_codes_from_bbox(sapporo_bbox)

# 3. 結果を出力
print(f"--- BBOXに含まれる一次メッシュ番号 ---")
print(f"対象BBOX: {sapporo_bbox}")
print(f"検出されたメッシュ総数: {len(primary_meshes)}")
print("------------------------------------------")
for code in primary_meshes:
    print(code)
print("------------------------------------------")
print("--- 処理完了 ---")