import requests
import zipfile
import tempfile
import os
import glob
import shutil # フォルダを強制的に削除するためにインポート
from qgis.core import QgsVectorLayer

# --- 設定項目 ---
url = "https://www.e-stat.go.jp/gis/statmap-search/data?dlserveyId=A002005212020&code=14214&coordSys=1&format=shape&downloadType=5&datum=2011"
# --- 設定はここまで ---

def calculate_bbox_from_zip_url(url):
    """
    一時フォルダを手動で管理し、URLからZIPをダウンロードしてBBOXを計算する関数
    """
    # 1. 一時フォルダを手動で作成
    temp_dir = tempfile.mkdtemp()
    print(f"一時フォルダを作成しました: {temp_dir}")
    
    try:
        zip_path = os.path.join(temp_dir, 'data.zip')
        extract_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)

        # ... (ダウンロードと解凍のコードは変更なし) ...
        try:
            print(f"ダウンロードを開始します: {url}")
            response = requests.get(url, stream=True, timeout=120)
            response.raise_for_status()
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("ダウンロードが完了しました。")
        except requests.exceptions.RequestException as e:
            print(f"エラー: ダウンロードに失敗しました。 {e}")
            return

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            print(f"ZIPファイルを解凍しました: {extract_dir}")
        except Exception as e:
            print(f"エラー: 解凍中に問題が発生しました。 {e}")
            return
            
        shp_files = glob.glob(os.path.join(extract_dir, '**', '*.shp'), recursive=True)
        if not shp_files:
            print("警告: ZIPファイル内にシェープファイルが見つかりませんでした。")
            return

        print(f"{len(shp_files)}個のシェープファイルを検出しました。BBOXを計算します...")

        for shp_path in shp_files:
            layer = QgsVectorLayer(shp_path, os.path.basename(shp_path), "ogr")

            if layer.isValid():
                bbox = layer.extent()
                print("---------------------------------")
                print(f"✅ レイヤ '{layer.name()}' のBBOXを計算しました。")
                print(f"  CRS: {layer.crs().authid()}")
                print(f"  xmin: {bbox.xMinimum()}")
                print(f"  ymin: {bbox.yMinimum()}")
                print(f"  xmax: {bbox.xMaximum()}")
                print(f"  ymax: {bbox.yMaximum()}")
                print("---------------------------------")
            else:
                 print(f"警告: レイヤとして読み込めませんでした: {shp_path}")

            # ★★★ 重要 ★★★
            # ループの最後にレイヤオブジェクトを削除
            del layer

    finally:
        # 2. 全ての処理が終わった後、最後に一時フォルダを強制的に削除
        # try...finally構文により、途中でエラーが発生しても必ず実行される
        print(f"一時フォルダを削除します: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("--- 処理が完了しました ---")

# --- メイン処理の実行 ---
calculate_bbox_from_zip_url(url)