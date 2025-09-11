import gc  # ガベージコレクションをインポート
import glob
import os
import tempfile
import zipfile

import requests
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes

# --- 設定 ---
# ユーザー指定のダウンロードURL
url = "https://www.e-stat.go.jp/gis/statmap-search/data?dlserveyId=D002005112020&code=01&coordSys=1&format=shape&downloadType=5&datum=2011"
layer_name = "downloaded_did"
# --- 設定ここまで ---


def download_and_add_layer_to_qgis_memory(zip_url, output_layer_name):
    """
    URLからZIPをダウンロードし、シェープファイルをメモリレイヤとしてQGISに追加する関数
    これにより、一時ファイルのロック問題を回避する
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, "data.zip")
        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir)

        print(f"一時ディレクトリを作成しました: {temp_dir}")

        # 1. URLからZIPファイルをダウンロード
        try:
            print(f"ダウンロードを開始します: {zip_url}")
            response = requests.get(zip_url, timeout=120)
            response.raise_for_status()
            with open(zip_path, "wb") as f:
                f.write(response.content)
            print("ダウンロードが完了しました。")
        except requests.exceptions.RequestException as e:
            print(f"エラー: ダウンロードに失敗しました。\n{e}")
            return

        # 2. ZIPファイルを解凍
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            print("ZIPファイルを解凍しました。")
        except Exception as e:
            print(f"エラー: ZIPファイルの解凍に失敗しました。\n{e}")
            return

        # 3. 解凍したフォルダからシェープファイルを検索
        shp_files = glob.glob(os.path.join(extract_dir, "**", "*.shp"), recursive=True)
        if not shp_files:
            print("警告: ZIP内にシェープファイルが見つかりませんでした。")
            return

        shp_path = shp_files[0]
        print(f"シェープファイルを検出しました: {shp_path}")

        # 4. シェープファイルを「一時的な」レイヤとして読み込む
        temp_layer = QgsVectorLayer(shp_path, "temp_layer", "ogr")
        if not temp_layer.isValid():
            print("エラー: 一時レイヤの読み込みに失敗しました。")
            return

        # 5. メモリレイヤを作成し、一時レイヤからデータをコピーする
        #   これがファイルロックを回避するための重要なステップ

        # 元レイヤの情報を取得
        crs = temp_layer.crs()
        geom_type = QgsWkbTypes.displayString(temp_layer.wkbType())

        # メモリレイヤを新規作成
        uri = f"{geom_type}?crs={crs.authid()}"
        mem_layer = QgsVectorLayer(uri, output_layer_name, "memory")

        # データのコピーを開始
        provider = mem_layer.dataProvider()

        # (a) 属性フィールド（列定義）をコピー
        provider.addAttributes(temp_layer.fields())
        mem_layer.updateFields()

        # (b) フィーチャ（図形と値）をコピー
        provider.addFeatures(temp_layer.getFeatures())
        mem_layer.updateExtents()

        # 6. 完成した「メモリレイヤ」をQGISプロジェクトに追加
        QgsProject.instance().addMapLayer(mem_layer)
        print(
            f"✅ 成功: レイヤ '{output_layer_name}' を【メモリレイヤとして】地図に追加しました。"
        )

        # 7. (重要) 一時レイヤの参照を削除し、ガベージコレクションを強制実行
        del temp_layer
        gc.collect()

    # このwithブロックを抜けるとき、ファイルロックが確実に解除されているため、
    # 一時フォルダを問題なく削除できる
    print("--- 処理が完了しました ---")


# --- メイン処理の実行 ---
download_and_add_layer_to_qgis_memory(url, layer_name)
