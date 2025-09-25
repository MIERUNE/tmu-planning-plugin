"""
都市計画区域データの取得機能モジュール
"""

import urllib.parse
from typing import Optional

from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsNetworkAccessManager,
    QgsProject,
    QgsVectorTileLayer,
)
from qgis.PyQt.QtCore import QEventLoop, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtWidgets import QMessageBox

from ..connect import PLUGIN_NAME, URBAN_PLANNING_AREA_API_ENDPOINT


class UrbanPlanningAlgorithm:
    """都市計画区域データ取得クラス"""

    def __init__(self, iface):
        self.iface = iface

    def _check_api_connection(self, api_key: str) -> bool:
        """APIキーの有効性を確認するための事前接続チェック"""
        # 接続テストとしてズームレベル0のタイルをリクエスト
        test_url = (
            URBAN_PLANNING_AREA_API_ENDPOINT
            + "?response_format=geojson&z=13&x=7272&y=3225"
        )

        request = QNetworkRequest(QUrl(test_url))
        request.setRawHeader(b"Ocp-Apim-Subscription-Key", api_key.encode("utf-8"))

        nam = QgsNetworkAccessManager.instance()
        reply = nam.get(request)

        loop = QEventLoop()
        reply.finished.connect(loop.quit)
        loop.exec_()

        http_status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)

        if reply.error():
            QgsMessageLog.logMessage(
                f"API接続に失敗しました: {reply.errorString()} (HTTPステータス: {http_status})",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            reply.deleteLater()
            return False

        QgsMessageLog.logMessage(
            "APIキーの有効性を確認しました (HTTP 200)", PLUGIN_NAME, level=Qgis.Info
        )
        reply.deleteLater()
        return True

    def get_urban_planning_area(self, api_key: str) -> Optional[QgsVectorTileLayer]:
        """
        指定した市区町村の都市計画区域データをAPIから取得する
        Args:
            api_key (str): APIキー
        Returns:
            QgsVectorTileLayer : 追加に成功した場合はレイヤーオブジェクト
        """
        # 接続チェック
        if not self._check_api_connection(api_key):
            # 失敗した場合はユーザーに通知して処理を中断
            QMessageBox.critical(
                self.iface.mainWindow(),
                "API接続エラー",
                "APIサーバーへの接続に失敗しました。\n\n"
                "APIキーが正しいか、インターネット接続が有効か確認してください。",
            )
            return None

        # パラメーターをエンコード
        params = {"response_format": "pbf", "z": "{z}", "x": "{x}", "y": "{y}"}
        encoded_params = urllib.parse.urlencode(params, safe="{}")

        # QGIS用にエンコード
        encoded_for_qgis = encoded_params.replace("=", "%3D").replace("&", "%26")
        encoded_tile_url = f"{URBAN_PLANNING_AREA_API_ENDPOINT}?{encoded_for_qgis}"

        # ベクトルタイルレイヤーのURLを作成
        get_real_estate_url = (
            f"type=xyz"
            f"&url={encoded_tile_url}"
            f"&zmax=15"
            f"&zmin=11"
            f"&http-header:Ocp-Apim-Subscription-Key={api_key}"
        )

        layer_name = "都市計画区域"
        urban_planning_layer = QgsVectorTileLayer(get_real_estate_url, layer_name)

        # if not urban_planning_layer.isValid():
        #     # ログにエラーメッセージを記録
        #     error_message = "ベクトルタイルレイヤーの読み込みに失敗しました。またはAPIキーが無効です。"
        #     QgsMessageLog.logMessage(error_message, PLUGIN_NAME, level=Qgis.Critical)
        #     self.iface.messageBar().pushMessage(
        #         "エラー", error_message, level=Qgis.Critical
        #     )

        #     user_message = (
        #         "都市計画区域レイヤーの読み込みに失敗しました。\n\n"
        #         "以下の点を確認してください:\n"
        #         "  ・インターネットに接続されていること\n"
        #         "  ・設定したAPIキーが正しいこと"
        #     )
        #     # 警告(Warning)より深刻なエラー(Critical)が適切
        #     QMessageBox.critical(
        #         self.iface.mainWindow(),  # 親ウィンドウの指定
        #         "レイヤー読み込みエラー",     # ダイアログのタイトル
        #         user_message              # 表示メッセージ
        #     )
        #     return None

        # QGISプロジェクトにレイヤーを追加
        QgsProject.instance().addMapLayer(urban_planning_layer)
        QgsMessageLog.logMessage(
            f"レイヤー '{layer_name}' を追加しました。", PLUGIN_NAME, level=Qgis.Info
        )

        return urban_planning_layer
