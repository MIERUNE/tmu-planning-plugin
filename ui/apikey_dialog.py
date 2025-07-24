import os

from qgis.core import QgsSettings
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QLineEdit, QMessageBox

from .config import API_KEY_LIST, BASE_SETTING_PATH

ui_dialog, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "apikey_keep.ui"))


class ApikeyDialog(QDialog, ui_dialog):
    def __init__(self, parent=None):
        """APIキーを入力する"""
        super().__init__(parent)
        self.setupUi(self)

        # QLineEditのリストを初期化
        self.api_key_line_edits = {}

        for api_key in API_KEY_LIST:
            line_edit: QLineEdit = self.findChild(QLineEdit, api_key["line_edit_name"])

            self.api_key_line_edits[api_key["id"]] = line_edit
            print(self.api_key_line_edits)

        self.buttonBox.accepted.connect(self.save_api_key)
        self.buttonBox.rejected.connect(self.reject)

        self.load_api_key()

    def load_api_key(self):
        """QGISの設定からAPI Keyを読み込む"""
        settings = QgsSettings()

        for api_key in API_KEY_LIST:
            line_edit: QLineEdit = self.findChild(QLineEdit, api_key["line_edit_name"])
            if line_edit:  # line_editが空でないことを確認
                setting_key = f"{BASE_SETTING_PATH}/{api_key['setting_key']}"
                api_key_value = settings.value(setting_key, "", type=str)
                line_edit.setText(api_key_value)

        print("APIキーの読み込み完了")

    def save_api_key(self):
        """API Keyの内容をQGISの設定に保存する"""
        settings = QgsSettings()
        for api_key in API_KEY_LIST:
            line_edit: QLineEdit = self.findChild(QLineEdit, api_key["line_edit_name"])
            if line_edit:
                api_key_value = line_edit.text().strip()

                setting_key = f"{BASE_SETTING_PATH}/{api_key['setting_key']}"
                settings.setValue(setting_key, api_key_value)

        QMessageBox.information(self, "保存完了", "APIキーが保存されました。")
        self.accept()
