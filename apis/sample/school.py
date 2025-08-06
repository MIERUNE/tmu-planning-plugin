from PyQt5.QtCore import QEventLoop, QUrl
from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import QgsNetworkAccessManager

# 1. リクエスト情報の設定
# TODO : パラメーターとAPIキーはユーザーが選択したものに置き換える
# TODO : 指定した自治体のデータに必要なタイル分を取得するようにする
url_string = "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT006?response_format=geojson&z=13&x=7272&y=3225"  # 千葉県
api_key = (
    "b112ca22671841f5b8f82727f2ffdaf3"  # <-- ここに実際のAPIキーを入力してください
)

# 2. リクエストの作成とヘッダーの設定
url = QUrl(url_string)
request = QNetworkRequest(url)

# ヘッダーにAPIキーを設定します
# キーとバリューはバイト文字列 (b"") にする必要があります
request.setRawHeader(b"Ocp-Apim-Subscription-Key", api_key.encode("utf-8"))

# 3. APIリクエストの実行
nam = QgsNetworkAccessManager.instance()
reply = nam.get(request)

# 4. レスポンスの待機と取得
loop = QEventLoop()
reply.finished.connect(loop.quit)
loop.exec_()

# エラーチェック
if reply.error():
    print(f"エラーが発生しました: {reply.errorString()}")
# （前のコードから続く...）
else:
    # 正常に取得できた場合、レスポンスをUTF-8でデコードして表示
    response_data = reply.readAll()
    response_string = response_data.data().decode("utf-8-sig")

    layer = QgsVectorLayer(response_string, "学校", "ogr")

    # レイヤーが正しく作成されたかチェック
    if not layer.isValid():
        print("レイヤーの作成に失敗しました。GeoJSONデータを確認してください。")
        # デバッグ用に受信したテキストを表示してみるのも有効です
        # print(response_string)
    else:
        # QGISプロジェクトにレイヤーを追加
        QgsProject.instance().addMapLayer(layer)
        print("レイヤーが正常にQGISに追加されました。")


# オブジェクトを解放
reply.deleteLater()
