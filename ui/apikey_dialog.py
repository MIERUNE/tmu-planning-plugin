import os

from qgis.core import Qgis, QgsSettings
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

        for api_key_info in API_KEY_LIST:
            line_edit_name = api_key_info.get("line_edit_name")
            api_key_id = api_key_info.get("id")

            # API_KEY_LISTのオブジェクトが不完全でないかチェック
            if not line_edit_name or not api_key_id:
                from qgis.core import QgsMessageLog

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
                    f"API_KEY_LISTに不完全なエントリがあります: {api_key_info}",
                    "ApikeyDialog",
                    Qgis.Warning,
                )

        self.buttonBox.accepted.connect(self.save_api_key)
        self.buttonBox.rejected.connect(self.reject)
        self.load_api_key()

    def load_api_key(self):
        """QGISの設定からAPI Keyを読み込む"""
        settings = QgsSettings()

        for api_key_info in API_KEY_LIST:
            api_key_id = api_key_info.get("id")
            if api_key_id in self.api_key_line_edits:
                line_edit = self.api_key_line_edits[api_key_id]
                setting_key = f"{BASE_SETTING_PATH}/{api_key_info['setting_key']}"
                api_key_value = settings.value(setting_key, "", type=str)
                line_edit.setText(api_key_value)

    def save_api_key(self):
        """API Keyの内容をQGISの設定に保存する"""
        settings = QgsSettings()
        for api_key_info in API_KEY_LIST:
            api_key_id = api_key_info.get("id")
            if api_key_id in self.api_key_line_edits:
                line_edit = self.api_key_line_edits[api_key_id]
                api_key_value = line_edit.text().strip()

                setting_key = f"{BASE_SETTING_PATH}/{api_key_info['setting_key']}"
                settings.setValue(setting_key, api_key_value)

        QMessageBox.information(self, "保存完了", "APIキーが保存されました。")
        self.accept()
