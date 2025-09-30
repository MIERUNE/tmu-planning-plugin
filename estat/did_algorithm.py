import gc
import glob
import os
import tempfile
import urllib.parse
import zipfile
from typing import Optional

import requests
from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsVectorLayer, QgsWkbTypes

from .connect import DID_AREA_API_ENDPOINT, PLUGIN_NAME


class DidAlgorithm:
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

    def _create_memory_layer(self, shp_path: str) -> Optional[QgsVectorLayer]:
        """
        シェープファイルを読み込み、その内容を新しいメモリレイヤとして返すヘルパー関数。
        ファイルロックを保持するレイヤはこの関数内でのみ生存し、関数の終了時に解放される。
        """
        temp_layer = QgsVectorLayer(shp_path, "temp_copy_layer", "ogr")
        if not temp_layer.isValid():
            QgsMessageLog.logMessage(
                f"エラー: レイヤの読み込みに失敗しました: {shp_path}",
                PLUGIN_NAME,
                Qgis.Critical,
            )

            return None

        # メモリレイヤの器を作成
        crs = temp_layer.crs()
        geom_type = QgsWkbTypes.displayString(temp_layer.wkbType())
        uri = f"{geom_type}?crs={crs.authid()}"
        mem_layer = QgsVectorLayer(uri, self.layer_name, "memory")

        # データをコピー
        provider = mem_layer.dataProvider()
        provider.addAttributes(temp_layer.fields())
        mem_layer.updateFields()
        provider.addFeatures(temp_layer.getFeatures())
        mem_layer.updateExtents()

        del temp_layer
        return mem_layer

    def get_did_area(self):
        """
        人口集中地区(DID)のZipファイルをダウンロードし、シェープファイルをメモリレイヤとしてQGISに追加する。
        """
        request_url = self._build_req_url()

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # 1. ダウンロードと解凍
                zip_path = os.path.join(temp_dir, "data.zip")
                response = requests.get(request_url, stream=True, timeout=120)
                response.raise_for_status()
                with open(zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                extract_dir = os.path.join(temp_dir, "extracted")
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)

                # 2. シェープファイルの検索
                shp_files = glob.glob(
                    os.path.join(extract_dir, "**", "*.shp"), recursive=True
                )
                if not shp_files:
                    message = "警告: ZIP内にシェープファイルが見つかりませんでした。"
                    QgsMessageLog.logMessage(
                        message,
                        PLUGIN_NAME,
                        Qgis.Warning,
                    )
                    self.iface.messageBar().pushMessage(
                        message,
                        level=Qgis.Warning,
                    )
                    return
                shp_path = shp_files[0]

                # 3. ヘルパー関数を使って、安全にメモリレイヤを作成
                mem_layer = self._create_memory_layer(shp_path)
                gc.collect()

                # 4. メモリレイヤをプロジェクトに追加
                if mem_layer is not None:
                    QgsProject.instance().addMapLayer(mem_layer)

            except requests.exceptions.RequestException as e:
                message = f"エラー: ダウンロードに失敗しました。{e}"
                QgsMessageLog.logMessage(
                    message,
                    PLUGIN_NAME,
                    Qgis.Critical,
                )
                self.iface.messageBar().pushMessage(message, level=Qgis.Critical)
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"エラー: 予期せぬ問題が発生しました。{e}",
                    PLUGIN_NAME,
                    Qgis.Critical,
                )
                self.iface.messageBar().pushMessage(message, level=Qgis.Critical)
