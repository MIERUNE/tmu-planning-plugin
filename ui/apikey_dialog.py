import os

from qgis.core import Qgis, QgsMessageLog, QgsSettings
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QLineEdit, QMessageBox

from .config import API_KEY_LIST, BASE_SETTING_PATH

ui_dialog, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "apikey_keep.ui"))


class ApikeyDialog(QDialog, ui_dialog):
    def __init__(self, parent=None):
        """ApikeyDialogを初期化"""
        super().__init__(parent)

        # ui_dialogが正しくロードされているか確認
        if ui_dialog is None:
            QMessageBox.critical(
                self, "エラー", "APIキーダイアログをロードできませんでした。"
            )
            self.close()
            return

        self.setupUi(self)

        # QLineEditウィジェットを辞書に保存
        self.api_key_line_edits: dict[str, QLineEdit] = {}

        self._create_line_edits_dict()

        self.buttonBox.accepted.connect(self.save_api_key)
        self.buttonBox.rejected.connect(self.reject)
        self.load_api_key()

    def _create_line_edits_dict(self):
        """API_KEY_LISTからQLineEditウィジェットを辞書データを作成"""
        for api_key_info in API_KEY_LIST:
            line_edit_name = api_key_info.get("line_edit_name")
            api_key_id = api_key_info.get("id")

            # API_KEY_LISTのオブジェクトが不完全でないかチェック
            if not line_edit_name or not api_key_id:
                QgsMessageLog.logMessage(
                    f"API_KEY_LISTに不完全なエントリがあります: {api_key_info}",
                    "GreenInfraPlanning",
                    level=Qgis.Warning,
                )
                continue

            line_edit: QLineEdit = self.findChild(QLineEdit, line_edit_name)

            if line_edit:
                self.api_key_line_edits[str(api_key_id)] = line_edit
            else:
                QgsMessageLog.logMessage(
                    f"指定されたUIウィジェットが見つかりませんでした: {api_key_info}",
                    "ApikeyDialog",
                    Qgis.Warning,
                )

    def load_api_key(self):
        """QGISの設定からAPI Keyを読み込む"""
        settings = QgsSettings()

        for api_key_info in API_KEY_LIST:
            api_key_id = api_key_info.get("id")
            if str(api_key_id) in self.api_key_line_edits:
                line_edit = self.api_key_line_edits[str(api_key_id)]
                setting_key = f"{BASE_SETTING_PATH}/{api_key_info['setting_key']}"
                api_key_value = settings.value(setting_key, "", type=str)
                line_edit.setText(api_key_value)

    def save_api_key(self):
        """API Keyの内容をQGISの設定に保存する"""
        settings = QgsSettings()
        for api_key_info in API_KEY_LIST:
            api_key_id = api_key_info.get("id")
            if str(api_key_id) in self.api_key_line_edits:
                line_edit = self.api_key_line_edits[str(api_key_id)]
                api_key_value = line_edit.text().strip()

                setting_key = f"{BASE_SETTING_PATH}/{api_key_info['setting_key']}"
                settings.setValue(setting_key, api_key_value)

        QMessageBox.information(self, "保存完了", "APIキーが保存されました。")
        self.accept()

    @staticmethod
    def get_saved_api_key_by_id(api_key_id: int) -> str:
        """保存されているAPIキー設定を取得
        Args:
            api_key_id (int): APIキーのID（1, 2, 3）
        Returns:
            str: 保存されているAPIキーの値（空文字列の場合あり）
        """
        settings = QgsSettings()
        for api_key_info in API_KEY_LIST:
            if api_key_info.get("id") == api_key_id:
                setting_key = f"{BASE_SETTING_PATH}/{api_key_info['setting_key']}"
                api_key_value = settings.value(setting_key, "", type=str)
                return api_key_value.strip() if api_key_value else ""

        return ""

    @staticmethod
    def get_real_estate_api_key() -> str:
        """不動産情報ライブラリAPIキー（ID:1）を取得
        Returns:
            str: 不動産情報ライブラリAPIキーの値
        """
        return ApikeyDialog.get_saved_api_key_by_id(1)
