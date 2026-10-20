"""
reference: https://github.com/felt/qgis-plugin/blob/main/felt/test/utilities.py
Common functionality used by regression tests.
"""

import atexit
import importlib
import logging
import os
import sys
import types

from qgis.core import QgsApplication
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtWidgets import QWidget
from qgis.utils import iface

from .qgis_interface import QgisInterface

LOGGER = logging.getLogger("QGIS")
QGIS_APP = None  # Static variable used to hold hand to running QGIS app
CANVAS = None
PARENT = None
IFACE = None

PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLUGIN_PKG_NAME = "tmu_planning_plugin_under_test"


def import_plugin_module(dotted_path: str):
    """
    相対インポートを含むプラグインのモジュールを読み込む
    Args:
        dotted_path (str): プラグインルートからのパス（例: "features.vegetation_map.settings"）
    Returns:
        module: 読み込んだモジュール
    """
    if PLUGIN_PKG_NAME not in sys.modules:
        package = types.ModuleType(PLUGIN_PKG_NAME)
        package.__path__ = [PLUGIN_ROOT]
        sys.modules[PLUGIN_PKG_NAME] = package
    return importlib.import_module(f"{PLUGIN_PKG_NAME}.{dotted_path}")


def get_qgis_app(cleanup=True):
    """Start one QGIS application to test against.

    :returns: Handle to QGIS app, canvas, iface and parent. If there are any
        errors the tuple members will be returned as None.
    :rtype: (QgsApplication, CANVAS, IFACE, PARENT)

    If QGIS is already running the handle to that app will be returned.
    """

    global QGIS_APP, PARENT, IFACE, CANVAS  # pylint: disable=W0603

    if iface:
        QGIS_APP = QgsApplication
        CANVAS = iface.mapCanvas()
        PARENT = iface.mainWindow()
        IFACE = iface
        return QGIS_APP, CANVAS, IFACE, PARENT

    global QGISAPP  # pylint: disable=global-variable-undefined

    try:
        QGISAPP  # pylint: disable=used-before-assignment
    except NameError:
        myGuiFlag = True  # All test will run qgis in gui mode

        # In python3 we need to convert to a bytes object (or should
        # QgsApplication accept a QString instead of const char* ?)
        try:
            argvb = list(map(os.fsencode, sys.argv))
        except AttributeError:
            argvb = sys.argv

        # Note: QGIS_PREFIX_PATH is evaluated in QgsApplication -
        # no need to mess with it here.
        QGISAPP = QgsApplication(argvb, myGuiFlag)

        QGISAPP.initQgis()
        s = QGISAPP.showSettings()
        LOGGER.debug(s)

        def debug_log_message(message, tag, level):
            """
            Prints a debug message to a log
            :param message: message to print
            :param tag: log tag
            :param level: log message level (severity)
            :return:
            """
            print("{}({}): {}".format(tag, level, message))

        QgsApplication.instance().messageLog().messageReceived.connect(
            debug_log_message
        )

        if cleanup:

            @atexit.register
            def exitQgis():  # pylint: disable=unused-variable
                """
                Gracefully closes the QgsApplication instance
                """
                try:
                    # pylint: disable=used-before-assignment
                    # pylint: disable=redefined-outer-name
                    QGISAPP.exitQgis()  # noqa
                    QGISAPP = None  # noqa
                    # pylint: enable=used-before-assignment
                    # pylint: enable=redefined-outer-name
                except NameError:
                    pass

    if PARENT is None:
        # noinspection PyPep8Naming
        PARENT = QWidget()

    if CANVAS is None:
        # noinspection PyPep8Naming
        CANVAS = QgsMapCanvas(PARENT)
        CANVAS.resize(QSize(400, 400))

    if IFACE is None:
        # QgisInterface is a stub implementation of the QGIS plugin interface
        # noinspection PyPep8Naming
        IFACE = QgisInterface(CANVAS)

    return QGISAPP, CANVAS, IFACE, PARENT
