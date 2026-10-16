"""
QGIS認証マネージャーを使ったAPIキー認証の共通処理
"""

from typing import Optional

from qgis.core import Qgis, QgsApplication, QgsAuthMethodConfig, QgsMessageLog

from .settings import PLUGIN_NAME


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
