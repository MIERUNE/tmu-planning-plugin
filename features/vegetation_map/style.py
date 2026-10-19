"""
現存植生図2024 の公式スタイル（QML）の取得と適用
"""

import io
import traceback
import zipfile
from typing import Callable

from qgis.core import Qgis, QgsMapLayer, QgsMessageLog, QgsVectorLayer
from qgis.PyQt.QtXml import QDomDocument

from ...utils.settings import PLUGIN_NAME


class VegetationMapStyle:
    """公式スタイル設定ファイルを取得し、レイヤーに適用する"""

    def __init__(self, fetch_style_zip: Callable[[], bytes]):
        """
        Args:
            fetch_style_zip (Callable[[], bytes]): スタイル zip の内容を返す関数（通信はアルゴリズム側）
        """
        self.fetch_style_zip = fetch_style_zip

    def _extract_qml(self, zip_bytes: bytes) -> bytes:
        """
        zip から QML を取り出す
        Args:
            zip_bytes (bytes): スタイル zip の内容
        Returns:
            bytes: QML の内容
        Raises:
            Exception: QML が含まれていない、または QGIS スタイル形式でない場合
        """
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            qml_names = [n for n in zf.namelist() if n.lower().endswith(".qml")]
            if not qml_names:
                raise Exception("スタイル zip に QML が含まれていません")
            qml_bytes = zf.read(qml_names[0])

        if b"<qgis" not in qml_bytes[:4096]:
            raise Exception("取得したファイルが QGIS スタイル形式ではありません")
        return qml_bytes

    def apply(self, layer: QgsVectorLayer) -> bool:
        """
        公式 QML（シンボル設定のみ）をレイヤーに適用する
        Args:
            layer (QgsVectorLayer): 対象レイヤー
        Returns:
            bool: 適用できた場合 True
        """
        try:
            qml_bytes = self._extract_qml(self.fetch_style_zip())

            document = QDomDocument()
            if not document.setContent(qml_bytes):
                raise Exception("QML の解析に失敗しました")

            ok, message = layer.importNamedStyle(
                document, QgsMapLayer.StyleCategory.Symbology
            )
            if not ok:
                raise Exception(message)

            layer.triggerRepaint()
            return True

        except Exception as e:
            QgsMessageLog.logMessage(
                f"スタイルの適用に失敗しました: {e}\n{traceback.format_exc()}",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Warning,
            )
            return False
