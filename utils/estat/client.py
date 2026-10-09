"""
e-Stat API - 行政区域データ取得ユーティリティ
"""

import glob
import os
import shutil
import tempfile
import zipfile
from typing import Optional

import requests
from qgis.PyQt.QtCore import QUrl, QUrlQuery
from qgis.core import Qgis, QgsMessageLog, QgsVectorLayer


class AdministrativeAreaClient:
    """
    e-Stat APIを使用した行政区域データの取得クライアント
    """

    def __init__(self, plugin_name: str = "GreenInfraPlannerJP"):
        """
        Args:
            plugin_name (str): ログ出力用のプラグイン名
        """
        self.plugin_name = plugin_name
        self.api_config = {
            "base_url": "https://www.e-stat.go.jp/gis/statmap-search/data",
            "default_params": {
                "dlserveyId": "A002005212020",  # 国勢調査2020年
                "coordSys": "1",  # 世界測地系
                "format": "shape",  # シェープファイル形式
                "downloadType": "5",  # 市区町村レベル
                "datum": "2011",  # 測地系2011（JGD2011）
            },
        }

    def fetch_municipality_polygon(
        self, municipality_code: str
    ) -> Optional[QgsVectorLayer]:
        """
        市区町村コードから行政区域データを取得
        Args:
            municipality_code (str): 市区町村コード
        Returns:
            QgsVectorLayer: ポリゴンレイヤー、または None（取得失敗時）
        """
        url = self._build_url(municipality_code)
        temp_dir = tempfile.mkdtemp()

        try:
            response = self._download_data(url)
            if not response:
                return None

            # ZIPファイルを保存・解凍
            layer = self._extract_and_load_shapefile(
                response, temp_dir, municipality_code
            )
            return layer

        except Exception as e:
            error_msg = f"行政区域データ取得エラー: {str(e)}"
            QgsMessageLog.logMessage(error_msg, self.plugin_name, level=Qgis.Critical)
            return None
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _build_url(self, municipality_code: str) -> str:
        """
        e-Stat API用のURLを構築
        Args:
            municipality_code (str): 市区町村コード
        Returns:
            str: 構築されたURL
        """
        params = self.api_config["default_params"].copy()
        params["code"] = municipality_code

        query = QUrlQuery()
        for key, value in params.items():
            query.addQueryItem(key, str(value))

        url = QUrl(self.api_config["base_url"])
        url.setQuery(query)
        return url.toString()

    def _download_data(self, url: str) -> Optional[bytes]:
        """
        e-Stat APIからデータをダウンロード
        Args:
            url (str): ダウンロードURL
        Returns:
            bytes: ダウンロードしたデータ、または None（失敗時）
        """
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            QgsMessageLog.logMessage(
                f"行政区域データのダウンロードに失敗しました: {str(e)}",
                self.plugin_name,
                level=Qgis.Critical,
            )
            return None

    def _extract_and_load_shapefile(
        self, zip_data: bytes, temp_dir: str, municipality_code: str
    ) -> Optional[QgsVectorLayer]:
        """
        ZIPファイルを解凍してシェープファイルを読み込み
        Args:
            zip_data (bytes): ZIPファイルのデータ
            temp_dir (str): 一時ディレクトリパス
            municipality_code (str): 市区町村コード
        Returns:
            QgsVectorLayer: レイヤー、または None（失敗時）
        """
        zip_path = os.path.join(temp_dir, "municipality.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_data)

        # ZIPファイルを解凍
        extract_dir = os.path.join(temp_dir, "extracted")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # シェープファイルを検索
        shp_files = glob.glob(os.path.join(extract_dir, "**", "*.shp"), recursive=True)
        if not shp_files:
            QgsMessageLog.logMessage(
                "シェープファイルが見つかりません",
                self.plugin_name,
                level=Qgis.Critical,
            )
            return None

        # 最初のシェープファイルからレイヤーを作成
        shp_path = shp_files[0]
        layer = QgsVectorLayer(
            shp_path, f"temp_municipality_{municipality_code}", "ogr"
        )

        if not layer.isValid():
            QgsMessageLog.logMessage(
                "シェープファイルの読み込みに失敗",
                self.plugin_name,
                level=Qgis.Critical,
            )
            return None

        return layer
