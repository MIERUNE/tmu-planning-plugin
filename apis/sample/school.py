import json

from PyQt5.QtCore import QEventLoop, QUrl
from PyQt5.QtNetwork import QNetworkRequest, QNetworkReply
from qgis.core import QgsMessageLog, QgsNetworkAccessManager

# 1. リクエスト情報の設定
# TODO : パラメーターとAPIキーはユーザーが選択したものに置き換える
# TODO : 指定した自治体のデータに必要なタイル分を取得するようにする
API_KEY = "826caa70ecafc235546d72631891eb6d13d2028e"
STATS_DATA_ID = "0003433219"  
AREA_CODE = "01000" # 北海道
CLASS_CODE_TOTAL_POPULATION = "0" # 総人口の分類項目コード
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
            QgsMessageLog.INFO,
        )

    except json.JSONDecodeError as e:
        error_message = f"JSONのパース中にエラーが発生しました: {e}"
        print(f"Error: {error_message}")
        QgsMessageLog.logMessage(error_message, "e-Stat API", QgsMessageLog.CRITICAL)

else:
    # エラーが発生した場合の処理
    error_string = reply.errorString()
    error_message = f"ネットワークリクエスト中にエラーが発生しました: {error_string}"
    print(f"Error: {error_message}")
    QgsMessageLog.logMessage(error_message, "e-Stat API", QgsMessageLog.CRITICAL)

# リプライオブジェクトを破棄
reply.deleteLater()
