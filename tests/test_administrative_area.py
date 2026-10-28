"""
行政区域ポリゴン機能のユニットテスト（通信はモック、ネットワークにはアクセスしない）
"""

import json
import os
import unittest
from unittest import mock

from qgis.core import (
    QgsBlockingNetworkRequest,
    QgsLayerTree,
    QgsProject,
    QgsVectorLayer,
)

from .utilities import get_qgis_app, import_plugin_module

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()

connect = import_plugin_module("features.administrative_area.connect")
settings = import_plugin_module("features.administrative_area.settings")
client_module = import_plugin_module("features.administrative_area.client")
algorithm_module = import_plugin_module(
    "features.administrative_area.administrative_area_algorithm"
)
workflow_module = import_plugin_module(
    "features.administrative_area.administrative_area_workflow"
)

MlitDpfClient = client_module.MlitDpfClient
AdministrativeAreaAlgorithm = algorithm_module.AdministrativeAreaAlgorithm
AdministrativeAreaWorkflow = workflow_module.AdministrativeAreaWorkflow

# ========================================
# 共通データ・スタブ
# ========================================

TILE_URL = "https://tiles.example.invalid/sip3rd/{z}/{x}/{y}.pbf"
AUTHCFG = "abc1234"
API_KEY = "dummy-api-key"


def make_dpf_response(style) -> dict:
    """国交DPF GraphQL の正常応答を生成する（style は dict または JSON 文字列）"""
    return {
        "data": {
            "data": {
                "totalNumber": 1,
                "getDataResults": [
                    {
                        "id": "x",
                        "title": "行政区域",
                        "vectorTiles": [{"title": "default", "style": style}],
                    }
                ],
            }
        }
    }


SAMPLE_STYLE = {
    "version": 8,
    "sources": {"sip3rd": {"type": "vector", "tiles": [TILE_URL]}},
}


class FakeMessageBar:
    """messageBar().pushMessage の呼び出し（タイトル, 本文）を記録するスタブ"""

    def __init__(self):
        self.messages = []

    def pushMessage(self, title, text, level=None, duration=None):
        self.messages.append((title, text))


class FakeIface:
    """アルゴリズム・ワークフローが使う iface.messageBar() だけを持つスタブ"""

    def __init__(self):
        self.message_bar = FakeMessageBar()

    def messageBar(self):
        return self.message_bar


class FakeReply:
    """QgsBlockingNetworkRequest.reply() のスタブ"""

    def __init__(self, content: bytes = b"", http_status=200):
        self._content = content
        self._http_status = http_status

    def content(self):
        return self._content

    def attribute(self, _attribute):
        return self._http_status


def patch_network(error_code, content: bytes = b"", http_status=200):
    """client モジュールの QgsBlockingNetworkRequest をスタブに差し替える

    Returns:
        (patcher, request_mock)
    """
    request = mock.Mock()
    request.get.return_value = error_code
    request.post.return_value = error_code
    request.reply.return_value = FakeReply(content, http_status)
    request.errorMessage.return_value = "network error"
    request_cls = mock.Mock(return_value=request)
    # client 側は QgsBlockingNetworkRequest.ErrorCode を参照するため実物の enum を持たせる
    request_cls.ErrorCode = QgsBlockingNetworkRequest.ErrorCode
    patcher = mock.patch.object(client_module, "QgsBlockingNetworkRequest", request_cls)
    return patcher, request


def make_algorithm(tile_url=TILE_URL, can_access=True, authcfg=AUTHCFG):
    """認証設定と国交DPF クライアントをモックしたアルゴリズムを返す

    Returns:
        (algorithm, iface, authcfg_patch, client_patch, client_mock)
    """
    iface = FakeIface()
    algorithm = AdministrativeAreaAlgorithm(iface)
    client = mock.Mock()
    client.fetch_tile_url.return_value = tile_url
    client.can_access_tiles.return_value = can_access
    authcfg_patch = mock.patch.object(
        algorithm_module, "get_api_header_authcfg", return_value=authcfg
    )
    client_patch = mock.patch.object(
        algorithm_module, "MlitDpfClient", return_value=client
    )
    return algorithm, iface, authcfg_patch, client_patch, client


def mbtiles_is_available(path: str) -> bool:
    """同梱 MBTiles が実体（SQLite）として存在するか（Git LFS のポインタではないか）"""
    if not os.path.exists(path):
        return False
    with open(path, "rb") as f:
        return f.read(16).startswith(b"SQLite format 3")


CLASS_MBTILES_PATH = AdministrativeAreaAlgorithm(FakeIface())._get_mbtiles_path()
LABELS_MBTILES_PATH = os.path.join(
    os.path.dirname(CLASS_MBTILES_PATH), "labels.mbtiles"
)
HAS_LOCAL_MBTILES = mbtiles_is_available(CLASS_MBTILES_PATH) and mbtiles_is_available(
    LABELS_MBTILES_PATH
)
SKIP_REASON = "同梱 MBTiles が無い（Git LFS 未取得）ためスキップ"


# ========================================
# ロジックのテスト
# ========================================


class TestLogicClientParse(unittest.TestCase):
    """国交DPF GraphQL 応答からのタイル URL 抽出"""

    def setUp(self):
        self.client = MlitDpfClient(AUTHCFG)

    def test_tile_url_from_style_dict(self):
        with mock.patch.object(
            self.client, "_post", return_value=make_dpf_response(SAMPLE_STYLE)
        ) as post_mock:
            self.assertEqual(self.client.fetch_tile_url("data-1"), TILE_URL)
        # クエリに dataSetID と dataID が埋め込まれている
        query = post_mock.call_args.args[0]["query"]
        self.assertIn(connect.DATASET_ID, query)
        self.assertIn("data-1", query)

    def test_tile_url_from_style_json_string(self):
        response = make_dpf_response(json.dumps(SAMPLE_STYLE))
        with mock.patch.object(self.client, "_post", return_value=response):
            self.assertEqual(self.client.fetch_tile_url("data-1"), TILE_URL)

    def test_none_when_post_fails(self):
        with mock.patch.object(self.client, "_post", return_value=None):
            self.assertIsNone(self.client.fetch_tile_url("data-1"))

    def test_none_when_response_shape_is_unexpected(self):
        broken = {"data": {"data": {"getDataResults": []}}}
        with mock.patch.object(self.client, "_post", return_value=broken):
            self.assertIsNone(self.client.fetch_tile_url("data-1"))

        no_tiles = make_dpf_response({"sources": {"s": {"type": "vector"}}})
        with mock.patch.object(self.client, "_post", return_value=no_tiles):
            self.assertIsNone(self.client.fetch_tile_url("data-1"))


class TestLogicClientNetwork(unittest.TestCase):
    """通信結果（エラーコード・本文）の扱い"""

    def setUp(self):
        self.client = MlitDpfClient(AUTHCFG)

    def test_post_returns_json_and_uses_authcfg(self):
        body = json.dumps({"data": {"ok": True}}).encode("utf-8")
        patcher, request = patch_network(
            QgsBlockingNetworkRequest.ErrorCode.NoError, body
        )
        with patcher:
            self.assertEqual(self.client._post({"query": "q"}), {"data": {"ok": True}})
        request.setAuthCfg.assert_called_once_with(AUTHCFG)
        sent_body = json.loads(bytes(request.post.call_args.args[1]))
        self.assertEqual(sent_body, {"query": "q"})

    def test_post_returns_none_on_network_error(self):
        patcher, _ = patch_network(
            QgsBlockingNetworkRequest.ErrorCode.ServerExceptionError, b"", 403
        )
        with patcher:
            self.assertIsNone(self.client._post({"query": "q"}))

    def test_post_returns_none_on_empty_or_invalid_body(self):
        for content in (b"", b"<html>", b"\xef\xbb\xbf[not json"):
            patcher, _ = patch_network(
                QgsBlockingNetworkRequest.ErrorCode.NoError, content
            )
            with patcher:
                self.assertIsNone(self.client._post({"query": "q"}), content)

    def test_post_returns_none_on_graphql_errors(self):
        body = json.dumps({"errors": [{"message": "unauthorized"}]}).encode("utf-8")
        patcher, _ = patch_network(QgsBlockingNetworkRequest.ErrorCode.NoError, body)
        with patcher:
            self.assertIsNone(self.client._post({"query": "q"}))

    def test_can_access_tiles_requests_check_tile_without_auth(self):
        patcher, request = patch_network(QgsBlockingNetworkRequest.ErrorCode.NoError)
        with patcher:
            self.assertTrue(self.client.can_access_tiles(TILE_URL))
        request.setAuthCfg.assert_not_called()
        requested_url = request.get.call_args.args[0].url().toString()
        self.assertEqual(requested_url, TILE_URL.format(**connect.CHECK_TILE_ZXY))

    def test_can_access_tiles_false_when_blocked(self):
        patcher, _ = patch_network(
            QgsBlockingNetworkRequest.ErrorCode.NetworkError, b"", None
        )
        with patcher:
            self.assertFalse(self.client.can_access_tiles(TILE_URL))


class TestLogicFetchTileUrl(unittest.TestCase):
    """タイル URL の取得とキャッシュ"""

    def test_success_is_cached_per_data_id(self):
        algorithm, _, authcfg_patch, client_patch, client = make_algorithm()
        with authcfg_patch, client_patch:
            self.assertEqual(algorithm._fetch_tile_url("d1", API_KEY), TILE_URL)
            self.assertEqual(algorithm._fetch_tile_url("d1", API_KEY), TILE_URL)
            self.assertEqual(algorithm._fetch_tile_url("d2", API_KEY), TILE_URL)
        # 同じ dataID へは 1 回しか問い合わせない
        self.assertEqual(client.fetch_tile_url.call_count, 2)

    def test_failure_is_cached_too(self):
        algorithm, _, authcfg_patch, client_patch, client = make_algorithm(
            tile_url=None
        )
        with authcfg_patch, client_patch:
            self.assertIsNone(algorithm._fetch_tile_url("d1", API_KEY))
            self.assertIsNone(algorithm._fetch_tile_url("d1", API_KEY))
        self.assertEqual(client.fetch_tile_url.call_count, 1)

    def test_clear_cache_allows_refetch(self):
        algorithm, _, authcfg_patch, client_patch, client = make_algorithm()
        with authcfg_patch, client_patch:
            algorithm._fetch_tile_url("d1", API_KEY)
            algorithm.clear_tile_url_cache()
            algorithm._fetch_tile_url("d1", API_KEY)
        self.assertEqual(client.fetch_tile_url.call_count, 2)

    def test_inaccessible_tile_source_is_treated_as_failure(self):
        algorithm, _, authcfg_patch, client_patch, _ = make_algorithm(can_access=False)
        with authcfg_patch, client_patch:
            self.assertIsNone(algorithm._fetch_tile_url("d1", API_KEY))

    def test_no_request_without_authcfg(self):
        # APIキー未設定などで認証設定が作れない場合は通信しない
        algorithm, _, authcfg_patch, client_patch, client = make_algorithm(authcfg=None)
        with authcfg_patch, client_patch as client_cls:
            self.assertIsNone(algorithm._fetch_tile_url("d1", ""))
        client_cls.assert_not_called()


def patch_local_fallback(algorithm, available: bool):
    """ローカルの class.mbtiles を同梱しているかを判定する"""
    return mock.patch.object(algorithm, "has_local_fallback", return_value=available)


class TestLogicSourceUri(unittest.TestCase):
    """データソース URI の決定（国交DPF 優先、取得できなければローカル MBTiles）"""

    def test_xyz_uri_when_tile_url_available(self):
        algorithm, iface, authcfg_patch, client_patch, client = make_algorithm()
        with authcfg_patch, client_patch:
            uri = algorithm._get_source_uri("class3", API_KEY)
        self.assertIn("type=xyz", uri)
        self.assertIn(f"zmin={connect.TILE_ZOOM_MIN}", uri)
        self.assertIn(f"zmax={connect.TILE_ZOOM_MAX}", uri)
        client.fetch_tile_url.assert_called_once_with(connect.DATA_IDS["class3_5"])
        self.assertEqual(iface.message_bar.messages, [])

    def test_class6_uses_its_own_data_id(self):
        algorithm, _, authcfg_patch, client_patch, client = make_algorithm()
        with authcfg_patch, client_patch:
            algorithm._get_source_uri("class6", API_KEY)
        client.fetch_tile_url.assert_called_once_with(connect.DATA_IDS["class6"])

    def test_fallback_to_mbtiles_with_single_warning_when_fetch_fails(self):
        algorithm, iface, authcfg_patch, client_patch, _ = make_algorithm(tile_url=None)
        with authcfg_patch, client_patch, patch_local_fallback(algorithm, True):
            for class_type in ("class3", "class5", "base"):
                uri = algorithm._get_source_uri(class_type, API_KEY)
                self.assertEqual(uri, f"type=mbtiles&url={CLASS_MBTILES_PATH}")
        # APIキーがあるのに取得できなかった場合の警告は、1 回の実行で 1 件だけ
        self.assertEqual(len(iface.message_bar.messages), 1)
        self.assertEqual(iface.message_bar.messages[0][0], "警告")
        self.assertIn("ローカルデータ", iface.message_bar.messages[0][1])

    def test_fallback_without_api_key_is_silent(self):
        # APIキー未設定時の通知は呼び出し側がまとめて出すため、ここでは出さない
        algorithm, iface, authcfg_patch, client_patch, _ = make_algorithm(authcfg=None)
        with authcfg_patch, client_patch, patch_local_fallback(algorithm, True):
            uri = algorithm._get_source_uri("class3", "")
        self.assertEqual(uri, f"type=mbtiles&url={CLASS_MBTILES_PATH}")
        self.assertEqual(iface.message_bar.messages, [])

    def test_no_fallback_without_local_mbtiles(self):
        # class.mbtiles を同梱しない版（公式リポジトリ用）は、取得できなければ None
        algorithm, iface, authcfg_patch, client_patch, _ = make_algorithm(tile_url=None)
        with authcfg_patch, client_patch, patch_local_fallback(algorithm, False):
            for class_type in ("class3", "class5", "base"):
                self.assertIsNone(algorithm._get_source_uri(class_type, API_KEY))
        # 警告は呼び出し側（ワークフロー）が出す
        self.assertEqual(iface.message_bar.messages, [])

    def test_xyz_uri_without_local_mbtiles(self):
        # 取得できればローカルデータの有無に関係なく国交DPFのタイルを使う
        algorithm, _, authcfg_patch, client_patch, _ = make_algorithm()
        with authcfg_patch, client_patch, patch_local_fallback(algorithm, False):
            self.assertIn("type=xyz", algorithm._get_source_uri("base", API_KEY))

    def test_has_local_fallback_follows_file_existence(self):
        algorithm, _, _, _, _ = make_algorithm()
        with mock.patch.object(algorithm_module.os.path, "isfile", return_value=True):
            self.assertTrue(algorithm.has_local_fallback())
        with mock.patch.object(algorithm_module.os.path, "isfile", return_value=False):
            self.assertFalse(algorithm.has_local_fallback())

    def test_class6_has_no_fallback(self):
        algorithm, iface, authcfg_patch, client_patch, _ = make_algorithm(tile_url=None)
        with authcfg_patch, client_patch:
            self.assertIsNone(algorithm._get_source_uri("class6", API_KEY))
        self.assertEqual(iface.message_bar.messages, [])

    def test_clear_cache_resets_notification(self):
        algorithm, iface, authcfg_patch, client_patch, _ = make_algorithm(tile_url=None)
        with authcfg_patch, client_patch, patch_local_fallback(algorithm, True):
            algorithm._get_source_uri("base", API_KEY)
            algorithm.clear_tile_url_cache()
            algorithm._get_source_uri("base", API_KEY)
        self.assertEqual(len(iface.message_bar.messages), 2)


# ========================================
# QGIS の機能を使うテスト
# ========================================


class TestQgisCreateLayer(unittest.TestCase):
    """create_administrative_area_layer（ベクトルタイルレイヤー生成とスタイル適用）"""

    def test_xyz_layer_has_filtered_styles(self):
        algorithm, _, authcfg_patch, client_patch, _ = make_algorithm()
        with authcfg_patch, client_patch:
            result = algorithm.create_administrative_area_layer("class3", API_KEY)

        self.assertIsNotNone(result)
        polygon_layer, _label_layer = result
        self.assertTrue(polygon_layer.isValid())
        self.assertEqual(polygon_layer.name(), f"{settings.LAYER_NAME}_class3")
        self.assertEqual(polygon_layer.providerType(), "xyzvectortiles")

        styles = polygon_layer.renderer().styles()
        self.assertEqual(len(styles), len(settings.CLASS3_STYLES))
        expressions = {s.filterExpression() for s in styles}
        self.assertEqual(
            expressions, {f"class3info = {v}" for v in settings.CLASS3_STYLES}
        )

    def test_base_layer_has_no_filter(self):
        algorithm, _, authcfg_patch, client_patch, _ = make_algorithm()
        with authcfg_patch, client_patch:
            polygon_layer, _ = algorithm.create_administrative_area_layer(
                "base", API_KEY
            )
        styles = polygon_layer.renderer().styles()
        self.assertEqual(len(styles), 1)
        self.assertEqual(styles[0].filterExpression(), "")

    def test_class6_returns_none_without_tile_url(self):
        algorithm, _, authcfg_patch, client_patch, _ = make_algorithm(tile_url=None)
        with authcfg_patch, client_patch:
            self.assertIsNone(
                algorithm.create_administrative_area_layer("class6", API_KEY)
            )

    @unittest.skipUnless(HAS_LOCAL_MBTILES, SKIP_REASON)
    def test_fallback_layer_from_local_mbtiles(self):
        algorithm, iface, authcfg_patch, client_patch, _ = make_algorithm(authcfg=None)
        with authcfg_patch, client_patch:
            result = algorithm.create_administrative_area_layer("class5", "")

        self.assertIsNotNone(result)
        polygon_layer, label_layer = result
        self.assertTrue(polygon_layer.isValid())
        self.assertEqual(polygon_layer.providerType(), "mbtilesvectortiles")
        self.assertEqual(
            len(polygon_layer.renderer().styles()), len(settings.CLASS5_STYLES)
        )
        self.assertEqual(iface.message_bar.messages, [])

        # ラベルレイヤーは labels.mbtiles から作られ、N03_004 でラベリングする
        self.assertIsNotNone(label_layer)
        self.assertTrue(label_layer.isValid())
        self.assertEqual(label_layer.name(), settings.LABEL_LAYER_NAME)
        label_styles = label_layer.labeling().styles()
        self.assertEqual(len(label_styles), 1)
        self.assertEqual(label_styles[0].labelSettings().fieldName, "N03_004")
        self.assertTrue(label_layer.hasScaleBasedVisibility())

    def test_label_layer_none_when_file_missing(self):
        algorithm, _, _, _, _ = make_algorithm()
        with mock.patch.object(algorithm_module.os.path, "exists", return_value=False):
            self.assertIsNone(algorithm._create_label_layer())


class TestQgisWorkflow(unittest.TestCase):
    """ワークフロー（『行政区域』サブグループへのレイヤー追加）"""

    def setUp(self):
        QgsProject.instance().clear()
        self.group = QgsProject.instance().layerTreeRoot().addGroup("ベースマップ")
        self.iface = FakeIface()
        self.workflow = AdministrativeAreaWorkflow(self.iface)
        self.workflow.algorithm = mock.Mock()
        # 既定はローカルデータを同梱した版（お客さん提出用）。同梱しない版のテストでは False にする
        self.workflow.algorithm.has_local_fallback.return_value = True
        # ワークフロー内で QgsSettings から読む APIキーを固定値に差し替える
        # （テスト実行環境の保存キーに依存させない。未設定テストでは return_value を "" にする）
        self.api_key_patch = mock.patch.object(
            workflow_module, "get_mlit_dpf_api_key", return_value=API_KEY
        )
        self.get_api_key = self.api_key_patch.start()

    def tearDown(self):
        self.api_key_patch.stop()
        QgsProject.instance().clear()

    @staticmethod
    def make_layers(with_label=True):
        polygon = QgsVectorLayer("Polygon?crs=EPSG:4326", "行政区域_class3", "memory")
        label = (
            QgsVectorLayer("Point?crs=EPSG:4326", settings.LABEL_LAYER_NAME, "memory")
            if with_label
            else None
        )
        return polygon, label

    def layer_names_in_sub_group(self):
        sub_group = self.group.findGroup("行政区域")
        self.assertIsNotNone(sub_group)
        return [
            child.layer().name()
            for child in sub_group.children()
            if QgsLayerTree.isLayer(child)
        ]

    def test_execute_adds_polygon_and_label_to_sub_group(self):
        self.workflow.algorithm.create_administrative_area_layer.return_value = (
            self.make_layers()
        )

        self.assertTrue(self.workflow.execute("class3", self.group))

        # ワークフロー内で取得したAPIキーをアルゴリズムに渡す
        self.workflow.algorithm.create_administrative_area_layer.assert_called_once_with(
            class_type="class3", api_key=API_KEY
        )
        self.assertEqual(
            self.layer_names_in_sub_group(),
            ["行政区域_class3", settings.LABEL_LAYER_NAME],
        )
        self.assertEqual(len(QgsProject.instance().mapLayers()), 2)
        self.assertEqual(self.iface.message_bar.messages[0][0], "成功")

    def test_execute_replaces_existing_layers_with_same_name(self):
        for _ in range(2):
            self.workflow.algorithm.create_administrative_area_layer.return_value = (
                self.make_layers()
            )
            self.workflow.execute("class3", self.group)

        # 2 回実行しても同名レイヤーは重複しない
        self.assertEqual(
            self.layer_names_in_sub_group(),
            ["行政区域_class3", settings.LABEL_LAYER_NAME],
        )
        self.assertEqual(len(QgsProject.instance().mapLayers()), 2)

    def test_execute_without_label_layer(self):
        self.workflow.algorithm.create_administrative_area_layer.return_value = (
            self.make_layers(with_label=False)
        )
        self.assertTrue(self.workflow.execute("base", self.group))
        self.assertEqual(self.layer_names_in_sub_group(), ["行政区域_class3"])

    def test_execute_without_group_adds_to_root(self):
        self.workflow.algorithm.create_administrative_area_layer.return_value = (
            self.make_layers()
        )
        self.assertTrue(self.workflow.execute("class3"))
        self.assertIsNone(self.group.findGroup("行政区域"))
        self.assertEqual(len(QgsProject.instance().mapLayers()), 2)

    def test_execute_returns_false_when_algorithm_fails(self):
        self.workflow.algorithm.create_administrative_area_layer.return_value = None
        self.assertFalse(self.workflow.execute("class6", self.group))
        self.assertIsNone(self.group.findGroup("行政区域"))
        self.assertEqual(self.iface.message_bar.messages[0][0], "警告")

    def test_execute_returns_false_when_layer_invalid(self):
        invalid = QgsVectorLayer("/path/does/not/exist.gpkg", "行政区域_class3", "ogr")
        self.workflow.algorithm.create_administrative_area_layer.return_value = (
            invalid,
            None,
        )
        self.assertFalse(self.workflow.execute("class3", self.group))
        self.assertEqual(self.iface.message_bar.messages[0][0], "エラー")

    def test_reset_clears_algorithm_cache(self):
        self.workflow.reset()
        self.workflow.algorithm.clear_tile_url_cache.assert_called_once_with()

    # --- APIキー未設定時（ローカルデータへのフォールバック） ---

    def warnings(self):
        return [m[1] for m in self.iface.message_bar.messages if m[0] == "警告"]

    def test_without_api_key_falls_back_with_single_warning(self):
        self.get_api_key.return_value = ""
        # 同名レイヤーは置き換えられるため、呼び出しごとに新しいレイヤーを返す
        self.workflow.algorithm.create_administrative_area_layer.side_effect = (
            lambda **kwargs: self.make_layers()
        )

        self.workflow.reset()
        for class_type in ("class3", "class5", "base"):
            self.assertTrue(self.workflow.execute(class_type, self.group))

        # キー空のままアルゴリズムを呼び、アルゴリズム側でローカルデータにフォールバックする
        calls = self.workflow.algorithm.create_administrative_area_layer.call_args_list
        self.assertEqual(len(calls), 3)
        for call in calls:
            self.assertEqual(call.kwargs["api_key"], "")

        # 警告は最後の base のときに1件だけ
        self.assertEqual(
            self.warnings(),
            [
                "国土交通DPFのAPIキーが未設定のため、行政区域はローカルデータを使用しました。"
            ],
        )

    def test_without_api_key_skips_class6_and_warns_once_at_base(self):
        self.get_api_key.return_value = ""
        self.workflow.algorithm.create_administrative_area_layer.side_effect = (
            lambda **kwargs: self.make_layers()
        )

        self.workflow.reset()
        self.assertFalse(self.workflow.execute("class6", self.group))
        # class6 の時点では警告を出さず、アルゴリズムも呼ばない
        self.workflow.algorithm.create_administrative_area_layer.assert_not_called()
        self.assertEqual(self.iface.message_bar.messages, [])

        self.assertTrue(self.workflow.execute("base", self.group))
        self.assertEqual(
            self.warnings(),
            [
                "国土交通DPFのAPIキーが未設定のため、行政区域はローカルデータを使用しました。"
                "6クラス分類はAPIキーが必要なためスキップしました。"
            ],
        )

    def test_reset_clears_class6_skipped(self):
        self.get_api_key.return_value = ""
        self.workflow.algorithm.create_administrative_area_layer.side_effect = (
            lambda **kwargs: self.make_layers()
        )

        self.workflow.reset()
        self.workflow.execute("class6", self.group)
        self.workflow.reset()
        self.workflow.execute("base", self.group)

        self.assertEqual(len(self.warnings()), 1)
        self.assertNotIn("6クラス分類", self.warnings()[0])

    # --- ローカルデータを同梱しない版（公式リポジトリ用） ---

    def test_without_api_key_and_local_data_skips_all_with_single_warning(self):
        self.get_api_key.return_value = ""
        self.workflow.algorithm.has_local_fallback.return_value = False

        self.workflow.reset()
        for class_type in ("class3", "class5", "class6", "base"):
            self.assertFalse(self.workflow.execute(class_type, self.group))

        # アルゴリズムは呼ばず、レイヤーも追加しない
        self.workflow.algorithm.create_administrative_area_layer.assert_not_called()
        self.assertIsNone(self.group.findGroup("行政区域"))
        # 警告は最後の base のときに1件だけ（他のAPIと同じ「スキップします」）
        self.assertEqual(
            self.warnings(),
            [
                "国土交通DPFのAPIキーが未設定のため、行政区域データの取得をスキップします。"
            ],
        )

    def test_fetch_failure_warns_once_per_run(self):
        # 国交DPFから取得できないと全レイヤーで失敗するが、警告は1件にまとめる
        self.workflow.algorithm.has_local_fallback.return_value = False
        self.workflow.algorithm.create_administrative_area_layer.return_value = None

        self.workflow.reset()
        for class_type in ("class3", "class5", "class6", "base"):
            self.assertFalse(self.workflow.execute(class_type, self.group))
        self.assertEqual(self.warnings(), ["行政区域レイヤーの取得に失敗しました。"])

        # 次の可視化では再度警告する
        self.workflow.reset()
        self.workflow.execute("base", self.group)
        self.assertEqual(len(self.warnings()), 2)


if __name__ == "__main__":
    unittest.main()
