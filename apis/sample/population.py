import json

from PyQt5.QtCore import QEventLoop, QUrl, QVariant
from PyQt5.QtNetwork import QNetworkReply, QNetworkRequest
from qgis.core import Qgis, QgsField, QgsMessageLog, QgsNetworkAccessManager, QgsProject

# 1. リクエスト情報の設定
# TODO : パラメーターとAPIキーはユーザーが選択したものに置き換える
API_KEY = "826caa70ecafc235546d72631891eb6d13d2028e"
STATS_DATA_ID = "0003433219"
AREA_CODE = "01101"  # 北海道
CLASS_CODE_TOTAL_POPULATION = "0"  # 総人口の分類項目コード
BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
url_string = f"{BASE_URL}?appId={API_KEY}&statsDataId={STATS_DATA_ID}&cdArea={AREA_CODE}&cdCat01={CLASS_CODE_TOTAL_POPULATION}"

# 2. リクエストの作成とヘッダーの設定
url = QUrl(url_string)
request = QNetworkRequest(url)
nam = QgsNetworkAccessManager.instance()
reply = nam.get(request)

# 3. レスポンスの待機と取得
loop = QEventLoop()
reply = nam.get(request)
reply.finished.connect(loop.quit)
loop.exec_()

# 4. 応答の処理とコンソール出力
if reply.error() == QNetworkReply.NoError:
    # 応答データをバイト配列から文字列にデコード
    response_data = reply.readAll().data().decode("utf-8")
    
    try:
        # JSONデータをパース
        json_data = json.loads(response_data)

        # json_dataから@areaの値を取得
        statistical_data = json_data.get("GET_STATS_DATA", {}).get(
            "STATISTICAL_DATA", {}
        )
        data_inf = statistical_data.get("DATA_INF", {})
        value = data_inf.get("VALUE", {})

        area_code = value.get("@area") # @areaの値コード
        population_value_str = value.get("$")  # 人口データの値

        if area_code and population_value_str:
            QgsMessageLog.logMessage(
                "e-Stat APIからのJSONデータの取得に成功しました。Pythonコンソールを確認してください。",
                "e-Stat API",
                Qgis.Info,
            )

        else:
            # 必要なデータが見つからない場合
            error_message = (
                "JSONデータに @area または人口データ ($) が見つかりませんでした。"
            )
            QgsMessageLog.logMessage(error_message, "e-Stat API", Qgis.Critical)

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

# 人口データと行政区域のデータを結合
if area_code and population_value_str:
    try:
        population_value = int(population_value_str)
    except (ValueError, TypeError) as e:
        QgsMessageLog.logMessage(
            f"人口データ '{population_value_str}' を数値に変換できませんでした: {e}",
            "e-Stat API",
            Qgis.Critical,
        )
        population_value = None

    layer = QgsProject.instance().mapLayersByName("hokkaido_prefecture")
    if not layer:
        QgsMessageLog.logMessage(
            "レイヤー 'hokkaido_prefecture' が見つかりませんでした。",
            "e-Stat API",
            Qgis.Critical,
        )

    else:
        layer = layer[0]
        layer_provider = layer.dataProvider()
        layer.startEditing() 
        QgsMessageLog.logMessage(
            f"レイヤー '{layer.name()}' の編集を開始しました。", "e-Stat API", Qgis.Info
        )
        print("Editing started for layer:", layer.name())

        # 'POPULATION' フィールドが存在しない場合は追加
        if layer.fields().indexOf("POPULATION") == -1:
            success = layer_provider.addAttributes(
                [QgsField("POPULATION", QVariant.Int)]
            )
            if success:
                layer.updateFields()
                QgsMessageLog.logMessage(
                    "新しいカラム 'POPULATION' を作成しました。",
                    "e-Stat API",
                    Qgis.Info,
                )
            else:
                QgsMessageLog.logMessage(
                    "カラム 'POPULATION' の作成に失敗しました。",
                    "e-Stat API",
                    Qgis.Critical,
                )
                layer.rollBack()
                raise Exception("Failed to add new field.")

        population_field_idx = layer.fields().indexOf("POPULATION")
        administra_field_idx = layer.fields().indexOf("administra") 

        if population_field_idx == -1 or administra_field_idx == -1:
            QgsMessageLog.logMessage(
                "必要なカラム 'POPULATION' または 'administra' が見つかりません。",
                "e-Stat API",
                Qgis.Critical,
            )
            layer.rollBack()
        else:
            changes = {}
            for feature in layer.getFeatures():
                # administraカラムの値を取得（文字列として取得）
                administra_value = feature["administra"]

                if str(administra_value) == str(area_code):
                    new_value = population_value
                    QgsMessageLog.logMessage(
                        f"一致: administra='{administra_value}' に人口データ '{population_value}' を設定します。",
                        "e-Stat API",
                        Qgis.Info,
                    )
                else:
                    new_value = None
                    QgsMessageLog.logMessage(
                        f"不一致: administra='{administra_value}' にはNULLを設定します。",
                        "e-Stat API",
                        Qgis.Info,
                    )

                # 変更を辞書に格納: {フィーチャID: {フィールドインデックス: 新しい値}}
                changes[feature.id()] = {population_field_idx: new_value}

            # データプロバイダを使って変更をまとめて更新
            layer.dataProvider().changeAttributeValues(changes)
            QgsMessageLog.logMessage(
                "属性テーブルの更新が完了しました。", "e-Stat API", Qgis.Info
            )

            # 変更を確定
            layer.commitChanges()
            QgsMessageLog.logMessage(
                f"レイヤー '{layer.name()}' の編集を確定しました。",
                "e-Stat API",
                Qgis.Info,
            )
