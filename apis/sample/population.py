import json

from PyQt5.QtCore import QEventLoop, QUrl
from PyQt5.QtNetwork import QNetworkReply, QNetworkRequest
from qgis.core import (
    Qgis,
    QgsCategorizedSymbolRenderer,
    QgsField,
    QgsMessageLog,
    QgsNetworkAccessManager,
    QgsProject,
    QgsSymbol,
    QgsRendererRange,
    QgsGraduatedSymbolRenderer
)
from qgis.PyQt.QtCore import QVariant

# 1. リクエスト情報の設定
# TODO : パラメーターとAPIキーはユーザーが選択したものに置き換える
# TODO : 指定した自治体のデータに必要なタイル分を取得するようにする
API_KEY = "826caa70ecafc235546d72631891eb6d13d2028e"
STATS_DATA_ID = "0003433219"
AREA_CODE = "01000"  # 北海道
CLASS_CODE_TOTAL_POPULATION = "0"  # 総人口の分類項目コード
BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
url_string = f"{BASE_URL}?appId={API_KEY}&statsDataId={STATS_DATA_ID}&cdArea={AREA_CODE}&cdCat01={CLASS_CODE_TOTAL_POPULATION}"


# 2. リクエストの作成とヘッダーの設定
url = QUrl(url_string)
request = QNetworkRequest(url)

# 3. APIリクエストの実行
nam = QgsNetworkAccessManager.instance()
reply = nam.get(request)

# 4. レスポンスの待機と取得
loop = QEventLoop()
# 応答を待つためのスロットを接続
reply = nam.get(request)
reply.finished.connect(loop.quit)
loop.exec_()

population_data = None

# 5. 応答の処理とコンソール出力
# if reply.error() == QNetworkRequest.NoError:
if reply.error() == QNetworkReply.NoError:
    # 応答データをバイト配列から文字列にデコード
    response_data = reply.readAll().data().decode("utf-8")

    # JSONデータをパース
    try:
        json_data = json.loads(response_data)

        # 取得したJSONデータを整形してコンソールに出力
        # コンソールに表示されるデータが膨大になる可能性があるため、一部抜粋または整形して表示するのが良いでしょう
        # 今回は簡略化のため、そのまま表示します
        print("=====================================================================")
        print("e-Stat APIからの応答データ (JSON):")
        print("=====================================================================")
        print(json.dumps(json_data, indent=2, ensure_ascii=False))
        print("=====================================================================")

        # データ取得の成功をQGISのメッセージログに表示
        QgsMessageLog.logMessage(
            "e-Stat APIからのJSONデータの取得に成功しました。Pythonコンソールを確認してください。",
            "e-Stat API",
            Qgis.Info,
        )

    except json.JSONDecodeError as e:
        error_message = f"JSONのパース中にエラーが発生しました: {e}"
        print(f"Error: {error_message}")
        QgsMessageLog.logMessage(error_message, "e-Stat API", Qgis.Critical)

else:
    # エラーが発生した場合の処理
    error_string = reply.errorString()
    error_message = f"ネットワークリクエスト中にエラーが発生しました: {error_string}"
    print(f"Error: {error_message}")
    QgsMessageLog.logMessage(error_message, "e-Stat API", Qgis.Critical)

# リプライオブジェクトを破棄
reply.deleteLater()

# --- 2. 取得した人口データをQGISレイヤーに結合して可視化する部分 ---
if population_data is not None:
    # QGISのプロジェクトから北海道のレイヤーを取得
    # レイヤー名が異なる場合は、この行を修正してください
    layer_name = "hokkaido_prefecture"
    layers = QgsProject.instance().mapLayersByName(layer_name)

    if layers:
        layer = layers[0]

        # 編集モードを開始
        layer.startEditing()

        # 属性フィールド「population」が存在するか確認し、なければ追加
        population_field_name = "POPULATION"
        if layer.fields().indexOf(population_field_name) == -1:
            layer.addAttribute(QgsField(population_field_name, QVariant.Int))
            layer.updateFields()
            QgsMessageLog.logMessage(
                f"レイヤーに新しいフィールド '{population_field_name}' を追加しました。",
                "e-Stat API",
                Qgis.Info,
            )

        # フィーチャを更新
        for feature in layer.getFeatures():
            # レイヤーの属性テーブルにある都道府県コード（例: 'PREF_CODE'）をキーにフィーチャを特定
            # レイヤーの実際の属性名に合わせて 'PREF_CODE' を変更してください
            if feature["PREF_CODE"] == AREA_CODE:
                feature[population_field_name] = population_data
                layer.updateFeature(feature)
                QgsMessageLog.logMessage(
                    f"フィーチャ '{feature['N03_001']}' に人口データを書き込みました。",
                    "e-Stat API",
                    Qgis.Info,
                )
                break  # 北海道のフィーチャが見つかったのでループを抜ける

        # 編集モードをコミット
        layer.commitChanges()

        # --- 3. 可視化の設定 ---
        # データの範囲を定義
        min_pop = 1000000
        max_pop = 6000000

        # 段階的な色分けシンボルを作成
        symbol_low = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol_low.setColor(Qgis.color("lightskyblue"))

        symbol_mid = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol_mid.setColor(Qgis.color("deepskyblue"))

        symbol_high = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol_high.setColor(Qgis.color("darkblue"))

        # categories = [
        #     QgsRendererCategory(0, min_pop, symbol_low, f"人口 {min_pop:,}人未満"),
        #     QgsRendererCategory(
        #         min_pop, max_pop, symbol_mid, f"人口 {min_pop:,}人以上{max_pop:,}人未満"
        #     ),
        #     QgsRendererCategory(
        #         max_pop, population_data, symbol_high, f"人口 {max_pop:,}人以上"
        #     ),
        # ]
        # QgsRendererRangeオブジェクトを作成
        ranges = [
            QgsRendererRange(0, min_pop, symbol_low, f"人口 {min_pop:,}人未満"),
            QgsRendererRange(
                min_pop, max_pop, symbol_mid, f"人口 {min_pop:,}人以上{max_pop:,}人未満"
            ),
            QgsRendererRange(
                max_pop, population_data + 1, symbol_high, f"人口 {max_pop:,}人以上"
            ),
        ]

        # GraduatedSymbolRendererを使用してレンダラーを設定
        renderer = QgsGraduatedSymbolRenderer(population_field_name, ranges)
        layer.setRenderer(renderer)
        layer.triggerRepaint()

        # カテゴライズされたシンボルレンダラーを設定
        renderer = QgsCategorizedSymbolRenderer(population_field_name, ranges)
        layer.setRenderer(renderer)
        layer.triggerRepaint()

        QgsMessageLog.logMessage(
            "レイヤーの可視化を更新しました。人口に応じて地図が色分けされます。",
            "e-Stat API",
            Qgis.Info,
        )

    else:
        QgsMessageLog.logMessage(
            f"指定されたレイヤー名 '{layer_name}' がQGISプロジェクトに見つかりません。レイヤーパネルを確認してください。",
            "e-Stat API",
            Qgis.Warning,
        )
