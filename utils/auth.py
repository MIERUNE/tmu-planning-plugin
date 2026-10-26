"""
QGIS認証マネージャーを使ったAPIキー認証の共通処理
"""

from typing import Optional

from qgis.core import Qgis, QgsApplication, QgsAuthMethodConfig, QgsMessageLog
from qgis.gui import QgisInterface

from .settings import PLUGIN_NAME


def resolve_api_header_authcfg(
    iface: QgisInterface, name: str, header: str, api_key: str, api_label: str
) -> Optional[str]:
    """APIキーをQGIS認証マネージャーの認証設定（APIHeader）に登録し、認証設定IDを返す

    登録できなかった場合は警告メッセージを出す。APIキー未設定の場合は何も出さずに None を返す。

    Args:
        iface (QgisInterface): QGISインターフェース（警告メッセージの表示に使う）
        name (str): 認証設定の名前
        header (str): APIキーを入れるヘッダー名
        api_key (str): APIキー（未設定なら空文字）
        api_label (str): 警告メッセージに表示するAPI名
    Returns:
        Optional[str]: 認証設定ID。APIキー未設定または登録失敗時は None
    """
    if not api_key:
        return None

    authcfg = get_api_header_authcfg(name, header, api_key)
    if authcfg is None:
        message = (
            f"{api_label}APIキーの認証設定を作成できませんでした。"
            "QGISの認証マネージャー（マスターパスワード）の設定を確認してください。"
        )
        QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.MessageLevel.Warning)
        iface.messageBar().pushMessage("警告", message, level=Qgis.MessageLevel.Warning)
    return authcfg


def get_api_header_authcfg(name: str, header: str, api_key: str) -> Optional[str]:
    """APIキーをヘッダーに付与する認証設定（APIHeader）を取得または作成する

    同名の認証設定があれば再利用し、キーが変わっていれば更新する。

    Args:
        name (str): 認証設定の名前（プラグイン内で一意にする）
        header (str): APIキーを入れるヘッダー名
        api_key (str): APIキー
    Returns:
        Optional[str]: 認証設定ID（authcfg）。作成・更新できない場合は None
    """
    if not api_key:
        return None

    auth_manager = QgsApplication.authManager()
    if auth_manager is None:
        QgsMessageLog.logMessage(
            "QGIS認証マネージャーを取得できませんでした。",
            PLUGIN_NAME,
            level=Qgis.MessageLevel.Warning,
        )
        return None

    for authcfg, available_config in auth_manager.availableAuthMethodConfigs().items():
        if available_config.name() != name:
            continue

        config = QgsAuthMethodConfig()
        auth_manager.loadAuthenticationConfig(authcfg, config, True)
        if config.method() == "APIHeader" and config.config(header) == api_key:
            return authcfg

        config.setMethod("APIHeader")
        config.setConfigMap({header: api_key})
        if auth_manager.updateAuthenticationConfig(config):
            return authcfg

        QgsMessageLog.logMessage(
            f"認証設定の更新に失敗しました: {name}",
            PLUGIN_NAME,
            level=Qgis.MessageLevel.Warning,
        )
        return None

    config = QgsAuthMethodConfig("APIHeader")
    config.setName(name)
    config.setConfig(header, api_key)
    if auth_manager.storeAuthenticationConfig(config):
        return config.id()

    QgsMessageLog.logMessage(
        f"認証設定の作成に失敗しました（マスターパスワードが未設定の可能性があります）: {name}",
        PLUGIN_NAME,
        level=Qgis.MessageLevel.Warning,
    )
    return None
