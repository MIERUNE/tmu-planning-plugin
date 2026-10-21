"""
utils/api_keys のユニットテスト
"""

import unittest

from qgis.core import QgsSettings

from .utilities import get_qgis_app, import_plugin_module

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()

api_keys = import_plugin_module("utils.api_keys")
config = import_plugin_module("ui.config")


def _setting_key(api_key_id: int) -> str:
    for info in config.API_KEY_LIST:
        if info["id"] == api_key_id:
            return f"{config.BASE_SETTING_PATH}/{info['setting_key']}"
    raise KeyError(api_key_id)


class TestApiKeys(unittest.TestCase):
    def setUp(self):
        self.settings = QgsSettings()
        self._backup = {
            i: self.settings.value(_setting_key(i), "", type=str) for i in (1, 2, 3, 4)
        }

    def tearDown(self):
        for i, value in self._backup.items():
            self.settings.setValue(_setting_key(i), value)

    def test_returns_stripped_value(self):
        self.settings.setValue(_setting_key(1), "  real-estate-key  ")
        self.assertEqual(api_keys.get_real_estate_api_key(), "real-estate-key")

    def test_returns_empty_when_not_set(self):
        self.settings.setValue(_setting_key(2), "")
        self.assertEqual(api_keys.get_umi_shiru_api_key(), "")

    def test_each_getter_reads_its_own_id(self):
        self.settings.setValue(_setting_key(1), "k1")
        self.settings.setValue(_setting_key(2), "k2")
        self.settings.setValue(_setting_key(3), "k3")
        self.settings.setValue(_setting_key(4), "k4")
        self.assertEqual(api_keys.get_real_estate_api_key(), "k1")
        self.assertEqual(api_keys.get_umi_shiru_api_key(), "k2")
        self.assertEqual(api_keys.get_estat_api_key(), "k3")
        self.assertEqual(api_keys.get_mlit_dpf_api_key(), "k4")

    def test_unknown_id_returns_empty(self):
        self.assertEqual(api_keys.get_saved_api_key_by_id(99), "")


if __name__ == "__main__":
    unittest.main()
