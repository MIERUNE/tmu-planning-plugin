from PyQt5.QtCore import QEventLoop, QUrl
from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsNetworkAccessManager,
    QgsProject,
    QgsVectorLayer,
)

# # 1. リクエスト情報の設定
# # TODO : パラメーターとAPIキーはユーザーが選択したものに置き換える
# # TODO : 指定した自治体のデータに必要なタイル分を取得するようにする
# url_string = "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT006?response_format=geojson&z=13&x=7272&y=3225"  # 千葉県
# api_key = (
#     "b112ca22671841f5b8f82727f2ffdaf3"  # <-- ここに実際のAPIキーを入力してください
# )


class UrbanPlanningAreaAlgorithm:
    """都市計画区域の取得と可視化を行うクラス"""

    def __init__(self, iface):
        self.iface = iface

    def fetch_and_load_layer(
        self, api_key: str, municipality_code: str, base_url: str, plugin_name: str
    ) -> bool:
        """
        APIから都市計画区域データを取得し、QGISにレイヤーとして追加する
        Args:
            api_key (str): APIキー
            municipality_code (str): 市区町村コード
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        reply = None
        try:
            # 引数のbase_urlを使ってURLを組み立てる
            url_string = f"{base_url}?z=11&x=1819&y=806&response_format=geojson"
            request = QNetworkRequest(QUrl(url_string))
            request.setRawHeader(b"Ocp-Apim-Subscription-Key", api_key.encode("utf-8"))

            # APIリクエストの実行
            nam = QgsNetworkAccessManager.instance()
            reply = nam.get(request)

            # レスポンスの待機と取得
            loop = QEventLoop()
            reply.finished.connect(loop.quit)
            loop.exec_()

            # エラーチェック
            if reply.error():
                error_message = f"APIリクエスト失敗: {reply.errorString()}"
                QgsMessageLog.logMessage(
                    error_message, plugin_name, level=Qgis.Critical
                )
                return False
            else:
                # 正常に取得できた場合、レスポンスをUTF-8でデコードして表示
                response_data = reply.readAll()
                response_string = response_data.data().decode("utf-8-sig")

                layer_name = f"都市計画区域_{municipality_code}"
                layer = QgsVectorLayer(response_string, layer_name, "ogr")

                # レイヤーが正しく作成されたかチェック
                if not layer.isValid():
                    QgsMessageLog.logMessage(
                        "レイヤーの作成に失敗しました。",
                        plugin_name,
                        level=Qgis.Warning,
                    )
                    return False
                else:
                    QgsProject.instance().addMapLayer(layer)
                    QgsMessageLog.logMessage(
                        f"レイヤー「{layer_name}」を追加しました。",
                        plugin_name,
                        level=Qgis.Info,
                    )
                    return True
        except Exception as e:  # 予期せぬエラーも考慮
            QgsMessageLog.logMessage(
                f"予期せぬエラー: {str(e)}", plugin_name, level=Qgis.Critical
            )
            return False

        finally:  # このブロックも忘れずに
            if reply:
                reply.deleteLater()
