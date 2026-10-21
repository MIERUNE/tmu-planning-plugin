"""
保存済みのAPIキーの取得
"""

from qgis.core import QgsSettings

from ..ui.config import API_KEY_LIST, BASE_SETTING_PATH


def get_saved_api_key_by_id(api_key_id: int) -> str:
    """保存されているAPIキー設定を取得
    Args:
        api_key_id (int): APIキーのID（1, 2, 3, 4）
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


def get_real_estate_api_key() -> str:
    """不動産情報ライブラリAPIキー（ID:1）を取得"""
    return get_saved_api_key_by_id(1)


def get_umi_shiru_api_key() -> str:
    """海しるAPIキー（ID:2）を取得"""
    return get_saved_api_key_by_id(2)


def get_estat_api_key() -> str:
    """e-Stat APIキー（ID:3）を取得"""
    return get_saved_api_key_by_id(3)


def get_mlit_dpf_api_key() -> str:
    """国土交通データプラットフォームAPIキー（ID:4）を取得"""
    return get_saved_api_key_by_id(4)
