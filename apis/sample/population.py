import json

from PyQt5.QtCore import QEventLoop, QUrl
from PyQt5.QtNetwork import QNetworkReply, QNetworkRequest
from qgis.core import Qgis, QgsMessageLog, QgsNetworkAccessManager, QgsProject

# 1. リクエスト情報の設定
# TODO : パラメーターとAPIキーはユーザーが選択したものに置き換える
# TODO : 指定した自治体のデータに必要なタイル分を取得するようにする
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

# 4. レスポンスの待機と取得
loop = QEventLoop()
# 応答を待つためのスロットを接続
reply = nam.get(request)
reply.finished.connect(loop.quit)
loop.exec_()

# 5. 応答の処理とコンソール出力
if reply.error() == QNetworkReply.NoError:
    # 応答データをバイト配列から文字列にデコード
    response_data = reply.readAll().data().decode("utf-8")

    # JSONデータをパース
    try:
        json_data = json.loads(response_data)

        # json_dataから@areaの値を取得
        statistical_data = json_data.get("GET_STATS_DATA", {}).get(
            "STATISTICAL_DATA", {}
        )
        data_inf = statistical_data.get("DATA_INF", {})
        value = data_inf.get("VALUE", {})

        # @area の値を取得
        area_code = value.get("@area")
        print(f"Area Code from JSON: {area_code}")
        # 人口データの値を取得
        population_value_str = value.get("$")
        print(f"Population Value: {population_value_str}")

        if area_code and population_value_str:
            # データ取得の成功をQGISのメッセージログに表示
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


layer = QgsProject.instance().mapLayersByName("hokkaido_prefecture")
if not layer:
    QgsMessageLog.logMessage(
        "レイヤー 'hokkaido_prefecture' が見つかりませんでした。",
        "e-Stat API",
        Qgis.Critical,
    )


layer = layer[0]
layer_provider = layer.dataProvider()
layer.startEditing()
print("Editing started for layer:", layer.name())
