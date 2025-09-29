import glob
import os
import shutil
import tempfile
import zipfile

import requests
from qgis.core import Qgis, QgsMessageLog, QgsVectorLayer

MUNICIPALITY_POLYGON_API_ENDPOINT = "https://www.e-stat.go.jp/gis/statmap-search/data?dlserveyId=A002005212020&coordSys=1&format=shape&downloadType=5&datum=2011"
PLUGIN_NAME = "Green Infra Plugin"


def fetch_and_calculate_bbox(municipality_code: str):
    """
    指定された市区町村コードの行政区域ポリゴンをe-Statからダウンロードし、BBOXを計算して返す関数
    Args:
        municipality_code (str): 5桁の市区町村コード

    Returns:
        dict: 成功時にBBOXの辞書 {'xmin': float, ...} を返す
        None: 失敗時にNoneを返す
    """
    QgsMessageLog.logMessage(
        f"市区町村コード: {municipality_code} のBBOXを計算します...",
        PLUGIN_NAME,
        level=Qgis.Info,
    )
    if not municipality_code or len(municipality_code) != 5:
        QgsMessageLog.logMessage(
            f"無効な市区町村コードです: {municipality_code}",
            PLUGIN_NAME,
            level=Qgis.Critical,
        )
        return None

    url = f"{MUNICIPALITY_POLYGON_API_ENDPOINT}&code={municipality_code}"
    temp_dir = tempfile.mkdtemp()

    try:
        # 行政区域ポリゴンデータのダウンロード
        zip_path = os.path.join(temp_dir, "data.zip")

        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except requests.exceptions.RequestException as e:
            QgsMessageLog.logMessage(
                f"エラー: ダウンロードに失敗しました。 {e}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return None

        # ZIPファイルの解凍
        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            # TODO :PR提出時に削除
            QgsMessageLog.logMessage(
                f"ZIPファイルを解凍しました: {extract_dir}",
                PLUGIN_NAME,
                level=Qgis.Info,
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"エラー: 解凍中に問題が発生しました。 {e}",
                PLUGIN_NAME,
                level=Qgis.Critical,
            )
            return None

        # 解凍されたシェープファイルを検索
        shp_files = glob.glob(os.path.join(extract_dir, "**", "*.shp"), recursive=True)
        if not shp_files:
            QgsMessageLog.logMessage(
                "警告: ZIPファイル内にシェープファイルが見つかりませんでした。",
                PLUGIN_NAME,
                level=Qgis.Warning,
            )
            return None

        # TODO :PR提出時に削除
        QgsMessageLog.logMessage(
            f"{len(shp_files)}個のシェープファイルを検出しました。BBOXを計算します...",
            PLUGIN_NAME,
            level=Qgis.Info,
        )

        for shp_path in shp_files:
            layer = QgsVectorLayer(shp_path, os.path.basename(shp_path), "ogr")

            if layer.isValid():
                bbox = layer.extent()
                result_bbox = {
                    "xmin": bbox.xMinimum(),
                    "ymin": bbox.yMinimum(),
                    "xmax": bbox.xMaximum(),
                    "ymax": bbox.yMaximum(),
                }

                QgsMessageLog.logMessage(
                    f"レイヤ '{layer.name()}' のBBOXを計算しました: {result_bbox}",
                    PLUGIN_NAME,
                    level=Qgis.Info,
                )
                return result_bbox
            else:
                print(f"警告: レイヤとして読み込めませんでした: {shp_path}")

            # ループの最後にレイヤオブジェクトを削除
            del layer

    finally:
        # 全ての処理が終わった後、最後に一時フォルダを強制的に削除
        shutil.rmtree(temp_dir, ignore_errors=True)
