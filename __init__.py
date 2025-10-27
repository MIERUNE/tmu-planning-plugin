# プラグインのエントリーポイント


def classFactory(iface):
    from .green_infra_planner_jp import GreenInfraPlugin

    return GreenInfraPlugin(iface)
