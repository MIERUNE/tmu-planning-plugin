"""
現存植生図2024 の公式スタイル（QML）の取得と適用
"""

import io
import traceback
import zipfile
from typing import Callable, List, Optional

from qgis.core import (
    Qgis,
    QgsCategorizedSymbolRenderer,
    QgsExpression,
    QgsExpressionNodeBinaryOperator,
    QgsExpressionNodeColumnRef,
    QgsExpressionNodeLiteral,
    QgsMapLayer,
    QgsMessageLog,
    QgsRendererCategory,
    QgsRuleBasedRenderer,
    QgsVectorLayer,
)
from qgis.PyQt.QtXml import QDomDocument

from ...utils.settings import PLUGIN_NAME
from .settings import FIELD_LEGEND_CODE


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

    @staticmethod
    def _legend_code_from_filter(filter_expression: str) -> Optional[str]:
        """
        ルールのフィルタ式が「"凡例コード" = '値'」の形なら値を返す
        Args:
            filter_expression (str): ルールのフィルタ式
        Returns:
            str: 凡例コードの値。想定外の式なら None
        """
        expression = QgsExpression(filter_expression)
        node = expression.rootNode()
        if (
            expression.hasParserError()
            or not isinstance(node, QgsExpressionNodeBinaryOperator)
            or node.op() != QgsExpressionNodeBinaryOperator.BinaryOperator.boEQ
        ):
            return None

        left, right = node.opLeft(), node.opRight()
        if (
            not isinstance(left, QgsExpressionNodeColumnRef)
            or left.name() != FIELD_LEGEND_CODE
            or not isinstance(right, QgsExpressionNodeLiteral)
        ):
            return None
        return str(right.value())

    def _collect_categories(
        self, rule: "QgsRuleBasedRenderer.Rule", categories: List[QgsRendererCategory]
    ) -> bool:
        """
        ルールを再帰的に走査してカテゴリに変換する
        Args:
            rule (QgsRuleBasedRenderer.Rule): 走査するルール
            categories (list): 変換結果の追加先
        Returns:
            bool: すべてのルールが変換できた場合 True
        """
        for child in rule.children():
            has_filter = bool(child.filterExpression())
            symbol = child.symbol()

            # フィルタもシンボルも持たないルールはグループとして子を辿る
            if not has_filter and symbol is None and child.children():
                if not self._collect_categories(child, categories):
                    return False
                continue

            # ELSE、別フィールド、複合式、シンボル無しの葉、入れ子付きの葉は変換しない
            if child.isElse() or symbol is None or child.children():
                return False
            legend_code = self._legend_code_from_filter(child.filterExpression())
            if legend_code is None:
                return False

            categories.append(
                QgsRendererCategory(legend_code, symbol.clone(), child.label())
            )
        return True

    def _to_categorized(
        self, renderer: QgsRuleBasedRenderer
    ) -> Optional[QgsCategorizedSymbolRenderer]:
        """
        凡例コードごとのルールベースレンダラーをカテゴリ値レンダラーに変換する
        Args:
            renderer (QgsRuleBasedRenderer): 公式 QML のレンダラー
        Returns:
            QgsCategorizedSymbolRenderer: 変換結果。想定外の構造なら None
        """
        root_rule = renderer.rootRule()
        if root_rule is None:
            return None
        categories: List[QgsRendererCategory] = []
        if not self._collect_categories(root_rule, categories) or not categories:
            return None
        return QgsCategorizedSymbolRenderer(FIELD_LEGEND_CODE, categories)

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

            # 描画負荷を下げるため、ルールベースならカテゴリ値に変換する（見た目は変わらない）
            renderer = layer.renderer()
            if isinstance(renderer, QgsRuleBasedRenderer):
                categorized = self._to_categorized(renderer)
                if categorized is not None:
                    layer.setRenderer(categorized)
                else:
                    QgsMessageLog.logMessage(
                        "スタイルが想定外の構造のため、ルールベースのまま適用します",
                        PLUGIN_NAME,
                        level=Qgis.MessageLevel.Info,
                    )

            layer.triggerRepaint()
            return True

        except Exception as e:
            QgsMessageLog.logMessage(
                f"スタイルの適用に失敗しました: {e}\n{traceback.format_exc()}",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Warning,
            )
            return False
