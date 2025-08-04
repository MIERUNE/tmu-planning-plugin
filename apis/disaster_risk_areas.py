import os
import tempfile

from PyQt5.QtCore import QEventLoop, QUrl
from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import QgsNetworkAccessManager

# 1. リクエスト情報の設定
# TODO : パラメーターとAPIキーはユーザーが選択したものに置き換える
# url_string = "https://www.reinfolib.mlit.go.jp/ex-api/external/XPT001?response_format=geojson&z=13&x=7312&y=3008&from=20223&to=20234"
response_format = "pbf"  # または "geojson"

url_string = f"https://www.reinfolib.mlit.go.jp/ex-api/external/XKT016?response_format={response_format}&z=11&x=1819&y=806"  # 千葉県
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
    # APIの応答がBOM付きUTF-8の場合があるため、'utf-8-sig' を推奨
    # response_string = response_data.data().decode("utf-8-sig")

    if response_format == "geojson":
        # GeoJSONの場合
        response_string = response_data.data().decode("utf-8-sig")
        layer = QgsVectorLayer(response_string, "災害危険区域タイル", "ogr")

    elif response_format == "pbf":
        # PBF (バイナリベクトルタイル) の場合
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(suffix=".pbf", delete=False) as tmp_file:
            tmp_file.write(response_data.data())
            tmp_file_path = tmp_file.name

        uri = f"{tmp_file_path}|layername=geojson"  # QGISのPBFプロバイダは通常このようにURIを構成
        layer = QgsVectorLayer(uri, "災害危険区域タイル", "mvt")

        # # 一時ファイルからレイヤーを作成
        # layer = QgsVectorLayer(tmp_file_path, "災害危険区域タイル", "ogr")
        # # レイヤーの読み込み後に一時ファイルを削除
        # layer.loaded.connect(lambda: os.remove(tmp_file_path))

        # レイヤーが有効な場合のみ、シグナルを接続
        if layer.isValid():
            # クロージャを使ってtmp_file_pathを関数に渡す
            def on_layer_added_and_cleanup(added_layer):
                if added_layer.source() == uri:
                    print(
                        f"レイヤー '{added_layer.name()}' が読み込まれました。一時ファイル '{tmp_file_path}' を削除します。"
                    )
                    os.remove(tmp_file_path)
                    QgsProject.instance().layersAdded.disconnect(
                        on_layer_added_and_cleanup
                    )

            QgsProject.instance().layersAdded.connect(on_layer_added_and_cleanup)

        # else:
        #     print(f"対応していない応答形式: {response_format}")
        #     layer = None  # 無効なレイヤーとしておく
        else:
            # レイヤー作成失敗時には一時ファイルを即座に削除
            os.remove(tmp_file_path)
            print("レイヤーの作成に失敗したため、一時ファイルを削除しました。")
            layer = None  # `None`を代入

    # レイヤーが正しく作成されたかチェック
    if layer and layer.isValid():
        # QGISプロジェクトにレイヤーを追加
        QgsProject.instance().addMapLayer(layer)
        print("レイヤーが正常にQGISに追加されました。")
        print(f"レイヤー名: {layer.name()}")
    else:
        print("レイヤーの作成に失敗しました。受信したデータを確認してください。")


# オブジェクトを解放
reply.deleteLater()
