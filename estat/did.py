import gc
import glob
import os
import tempfile
import urllib.parse
import zipfile

import requests
from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsVectorLayer, QgsWkbTypes

# from .connect import DID_AREA_API_ENDPOINT, PLUGIN_NAME
DID_AREA_API_ENDPOINT = "https://www.e-stat.go.jp/gis/statmap-search/data"

# ログメッセージ用プラグイン名
PLUGIN_NAME = "Green Infra Plugin"


class DidDownloader:
    """人口集中地区(DID)のデータをダウンロードし、QGISに追加するクラス"""

    def __init__(self, prefecture_code: str, iface):
        """
        Args:
            prefecture_code (str): 対象の都道府県コード (例: "01", "13")
            iface: QGISインターフェース
        """
        self.iface = iface
        self.prefecture_code = prefecture_code
        self.layer_name = f"人口集中地区(DID)_{prefecture_code}"

    def _build_req_url(self) -> str:
        """APIリクエストURLを組み立てる"""
        # パラメーター
        params = {
            "dlserveyId": "D002005112020",
            "code": self.prefecture_code,  # TODO: 指定した都道府県コードに変更する
            "coordSys": "1",
            "format": "shape",
            "downloadType": "5",
            "datum": "2011",
        }
        # パラメーターをエンコード
        encoded_params = urllib.parse.urlencode(params)
        return f"{DID_AREA_API_ENDPOINT}?{encoded_params}"

    def get_did_area(self):
        """
        URLからZIPをダウンロードし、シェープファイルをメモリレイヤとしてQGISに追加する
        """

        

        request_url = self._build_req_url()
        QgsMessageLog.logMessage(
            f"リクエストURL: {request_url}", PLUGIN_NAME, Qgis.Info
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "data.zip")
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir)

            QgsMessageLog.logMessage(
                f"データのダウンロードを開始します: {self.prefecture_code}",
                PLUGIN_NAME,
                level=Qgis.Info,
            )

            # 人口集中地区(DID)ポリゴンデータのダウンロード
            try:
                response = requests.get(request_url, timeout=60)
                response.raise_for_status()
                with open(zip_path, "wb") as f:
                    f.write(response.content)
                QgsMessageLog.logMessage(
                    "ダウンロードが完了しました。", PLUGIN_NAME, Qgis.Info
                )
            except requests.exceptions.RequestException as e:
                QgsMessageLog.logMessage(
                    f"エラー: ダウンロードに失敗しました。\n{e}",
                    PLUGIN_NAME,
                    Qgis.Critical,
                )
                return

            # ZIPファイルを解凍
            try:
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)
                print("ZIPファイルを解凍しました。")
            except Exception as e:
                print(f"エラー: ZIPファイルの解凍に失敗しました。\n{e}")
                return

            # 解凍したフォルダからシェープファイルを検索
            shp_files = glob.glob(
                os.path.join(extract_dir, "**", "*.shp"), recursive=True
            )
            if not shp_files:
                print("警告: ZIP内にシェープファイルが見つかりませんでした。")
                return

            shp_path = shp_files[0]
            print(f"シェープファイルを検出しました: {shp_path}")

            # 4. シェープファイルを「一時的な」レイヤとして読み込む
            temp_layer = QgsVectorLayer(shp_path, "temp_layer", "ogr")
            if not temp_layer.isValid():
                print("エラー: 一時レイヤの読み込みに失敗しました。")
                return

            # 5. メモリレイヤを作成し、一時レイヤからデータをコピーする
            #   これがファイルロックを回避するための重要なステップ

            # 元レイヤの情報を取得
            crs = temp_layer.crs()
            geom_type = QgsWkbTypes.displayString(temp_layer.wkbType())

            # メモリレイヤを新規作成
            uri = f"{geom_type}?crs={crs.authid()}"
            mem_layer = QgsVectorLayer(uri, self.layer_name, "memory")

            # データのコピーを開始
            provider = mem_layer.dataProvider()

            # (a) 属性フィールド（列定義）をコピー
            provider.addAttributes(temp_layer.fields())
            mem_layer.updateFields()

            # (b) フィーチャ（図形と値）をコピー
            provider.addFeatures(temp_layer.getFeatures())
            mem_layer.updateExtents()

            # 6. 完成した「メモリレイヤ」をQGISプロジェクトに追加
            QgsProject.instance().addMapLayer(mem_layer)

            # 7. (重要) 一時レイヤの参照を削除し、ガベージコレクションを強制実行
            del temp_layer
            gc.collect()