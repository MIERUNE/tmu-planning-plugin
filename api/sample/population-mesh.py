import os
import tempfile
import zipfile
from pathlib import Path

import requests
from qgis.core import (
    QgsField,
    QgsGraduatedSymbolRenderer,
    QgsProject,
    QgsStyle,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant

API_KEY = "826caa70ecafc235546d72631891eb6d13d2028e"  # e-StatのAPIキー

stats_data_id = "8003007181"  # 取得したいデータのID（人口メッシュデータ）
population_mesh_url = (
    "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData?appId={apiId}&lang=J&statsDataId=8003007181&cdCat01=0010"
).format(apiId=API_KEY)
# population_mesh_url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData??appId={APIキー}&lang=J&statsDataId=8003007181&cdCat01=0010"
# mesh_shapefile_url = "https://www.e-stat.go.jp/gis/statmap-search/data/2020/g04-c-2020-01-1-jgd.zip" #「3次メッシュ」のシェープファイルのURL
mesh_data = "https://www.e-stat.go.jp/gis/statmap-search/data?dlserveyId=S&code=6441&coordSys=1&format=shape&downloadType=5"

temp_dir = tempfile.mkdtemp()
print(f"一時ディレクトリを作成しました: {temp_dir}")

try:
    # --- 1. メッシュ形状データのダウンロードと展開 ---
    print("メッシュ形状データをダウンロード中...")
    response_shape = requests.get(mesh_data)
    response_shape.raise_for_status()  # エラーチェック

    zip_path = os.path.join(temp_dir, "mesh.zip")
    with open(zip_path, "wb") as f:
        f.write(response_shape.content)

    print("ZIPファイルを展開中...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    shp_path = next(Path(temp_dir).glob("*.shp"))

    print(f"シェープファイルパス: {shp_path}")

    # --- 2. QGISにレイヤーとして追加 ---
    layer_name = "人口メッシュ_1km"
    # 既存の同名レイヤーを削除
    layers = QgsProject.instance().mapLayersByName(layer_name)
    if layers:
        QgsProject.instance().removeMapLayer(layers[0])

    vlayer = QgsVectorLayer(str(shp_path), layer_name, "ogr")
    if not vlayer.isValid():
        print("レイヤーの読み込みに失敗しました。")
    else:
        QgsProject.instance().addMapLayer(vlayer)
        print(f"レイヤー「{layer_name}」をQGISに追加しました。")

        # --- 3. 人口データの取得と整形 ---
        print("e-Stat APIから人口データを取得中...")
        response_pop = requests.get(population_mesh_url)
        response_pop.raise_for_status()

        # 取得したJSONデータをパース
        json_data = response_pop.json()
        stats_values = json_data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"][
            "VALUE"
        ]

        # {メッシュコード: 人口} の辞書を作成
        population_dict = {
            item["@area"]: int(item["$"])
            for item in stats_values
            if "$" in item and str(item["$"]).isnumeric()
        }

        # --- 4. データの結合 ---
        print("人口データをレイヤーに結合中...")

        # 結合先のフィールド名
        join_field_name = "population"
        key_field_name = (
            "KEY_CODE"  # e-Statのシェープファイルのメッシュコードのフィールド名
        )

        # レイヤーの編集を開始
        vlayer.startEditing()

        # 新しいフィールド（人口格納用）を追加
        if vlayer.fields().indexFromName(join_field_name) == -1:
            vlayer.dataProvider().addAttributes(
                [QgsField(join_field_name, QVariant.Int)]
            )
            vlayer.updateFields()
            print(f"フィールド「{join_field_name}」を追加しました。")

        # 各フィーチャに人口データを書き込む
        join_field_idx = vlayer.fields().indexFromName(join_field_name)
        updated_count = 0
        for feature in vlayer.getFeatures():
            mesh_code = feature[key_field_name]
            if mesh_code in population_dict:
                population_value = population_dict[mesh_code]
                vlayer.changeAttributeValue(
                    feature.id(), join_field_idx, population_value
                )
                updated_count += 1

        # 編集を確定
        vlayer.commitChanges()
        print(f"{updated_count} 個のメッシュに人口データを結合しました。")

        # --- 5. 可視化（段階分けレンダリング） ---
        print("レイヤーのスタイルを設定中...")

        target_field = join_field_name

        # 5段階に分類
        class_count = 5

        # レンダラーを作成
        renderer = QgsGraduatedSymbolRenderer(target_field)
        renderer.setClassAttribute(target_field)

        # カラーランプを選択
        color_ramp = QgsStyle.defaultStyle().colorRamp(
            "Viridis"
        )  # Blues, Redsなども利用可能
        renderer.setSourceColorRamp(color_ramp)

        # データを分類
        renderer.updateClasses(vlayer, QgsGraduatedSymbolRenderer.Jenks, class_count)

        # レイヤーにレンダラーを適用
        vlayer.setRenderer(renderer)
        vlayer.triggerRepaint()  # 地図を再描画

        print("処理が完了しました！")

except requests.exceptions.RequestException as e:
    print(f"エラー: データ取得に失敗しました。URLやAPIキーを確認してください。\n{e}")
except Exception as e:
    print(f"予期せぬエラーが発生しました: {e}")

finally:
    # 一時フォルダのクリーンアップは行わないので、手動で削除してください
    # import shutil; shutil.rmtree(temp_dir) # 自動削除したい場合はこの行を有効化
    print("スクリプトを終了します。")
