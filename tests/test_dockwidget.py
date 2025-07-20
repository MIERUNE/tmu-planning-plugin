import unittest

from ui.dockwidget import GreenInfraPlanningDockwidget

from .utilities import get_qgis_app

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestDialog(unittest.TestCase):
    def test_menu(self):
        dockwidget = GreenInfraPlanningDockwidget()

        assert dockwidget.isVisible() is False
        dockwidget.show()
        assert dockwidget.isVisible() is True
        dockwidget.hide()
        assert dockwidget.isVisible() is False


if __name__ == "__main__":
    unittest.main()
