# プラグインのエントリーポイント


def classFactory(iface):
    from .green_infra_plugin import GreenInfraPlugin

    return GreenInfraPlugin(iface)
