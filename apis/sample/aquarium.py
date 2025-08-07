from PyQt5.QtCore import QEventLoop, QUrl
from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import QgsNetworkAccessManager, QgsProject, QgsVectorLayer

# 1. リクエスト情報の設定
# TODO : パラメーターとAPIキーはユーザーが選択したものに置き換える
LayerSelection = 1
min_lon, min_lat, max_lon, max_lat = 140.5, 42.0, 141.5, 43.5
url_string = f"https://api.msil.go.jp/aquarium/v2/MapServer/{LayerSelection}/query?f=geojson&geometry={min_lon},{min_lat},{max_lon},{max_lat}"
api_key = (
    "10784fa6ea604de687b2052e55e03879"  # <-- 海しるのお試し用のサブスクリプションキー
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

    layer = QgsVectorLayer(response_string, "水族館", "ogr")

    # レイヤーが正しく作成されたかチェック
    if not layer.isValid():
        print("レイヤーの作成に失敗しました。GeoJSONデータを確認してください。")
    else:
        # QGISプロジェクトにレイヤーを追加
        QgsProject.instance().addMapLayer(layer)
        print("レイヤーが正常にQGISに追加されました。")


# オブジェクトを解放
reply.deleteLater()
