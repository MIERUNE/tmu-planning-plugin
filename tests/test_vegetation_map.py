"""
現存植生図2024（環境ジオポータル）機能のユニットテスト

通信（_request）と e-Stat クライアントはモックに置き換え、ネットワークにはアクセスしない。
前半はロジックのテスト、後半は QGIS の機能（QgsJsonUtils、メモリレイヤー、QML 適用）を使うテスト。
"""

import io
import json
import unittest
import zipfile
from unittest import mock

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsFillSymbol,
    QgsRendererCategory,
    QgsVectorLayer,
)
from qgis.PyQt.QtXml import QDomDocument

from .utilities import get_qgis_app, import_plugin_module

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()

connect = import_plugin_module("features.vegetation_map.connect")
settings = import_plugin_module("features.vegetation_map.settings")
algorithm_module = import_plugin_module(
    "features.vegetation_map.vegetation_map_algorithm"
)
workflow_module = import_plugin_module(
    "features.vegetation_map.vegetation_map_workflow"
)
real_estate_settings = import_plugin_module("features.real_estate_lib.settings")

VegetationMapAlgorithm = algorithm_module.VegetationMapAlgorithm
VegetationMapWorkflow = workflow_module.VegetationMapWorkflow

# ========================================
# 共通データ・スタブ
# ========================================

# 札幌市中心部の取得範囲（EPSG:4326）
BOUNDS = {"min_lon": 141.30, "min_lat": 43.03, "max_lon": 141.40, "max_lat": 43.09}

# FeatureServer が返す GeoJSON の例
SAMPLE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": 1,
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[141.30, 43.03], [141.31, 43.03], [141.31, 43.04], [141.30, 43.03]]
                ],
            },
            "properties": {
                "凡例コード": "010000",
                "植生自然度": "10",
                "SHAPE__Area": 12.5,
                "凡例名": "高山低木群落",
            },
        },
        {
            "type": "Feature",
            "id": 2,
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [141.32, 43.03],
                            [141.33, 43.03],
                            [141.33, 43.04],
                            [141.32, 43.03],
                        ]
                    ]
                ],
            },
            "properties": {
                "fid": 2,
                "凡例コード": "010100",
                "植生自然度": "9",
                "SHAPE__Area": 3.25,
                "凡例名": "ハイマツ群落",
            },
        },
    ],
}
SAMPLE_GEOJSON_BYTES = json.dumps(SAMPLE_GEOJSON).encode("utf-8")

# FeatureServer のレイヤー情報（{endpoint}?f=json）の例
SAMPLE_LAYER_INFO = {
    "maxRecordCount": 2000,
    "fields": [
        {"name": "fid", "type": "esriFieldTypeOID"},
        {"name": "凡例コード", "type": "esriFieldTypeString"},
        {"name": "凡例名", "type": "esriFieldTypeString"},
        {"name": "植生自然度", "type": "esriFieldTypeString"},
        {"name": "SHAPE__Area", "type": "esriFieldTypeDouble"},
        {"name": "Shape", "type": "esriFieldTypeGeometry"},
    ],
}
SAMPLE_LAYER_INFO_BYTES = json.dumps(SAMPLE_LAYER_INFO).encode("utf-8")

# Hub API（データセットのメタデータ）の応答の例
HUB_DATASET_BYTES = json.dumps(
    {"data": {"attributes": {"name": "北海道", "url": "http://svc/0"}}}
).encode("utf-8")
HUB_STYLE_BYTES = json.dumps(
    {"data": {"attributes": {"name": "スタイル", "itemId": "item123"}}}
).encode("utf-8")


def make_page(count: int, start: int = 0) -> bytes:
    """ページング確認用に、指定件数の地物を持つ GeoJSON ページを生成する"""
    features = [
        {
            "type": "Feature",
            "id": start + i,
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
            },
            "properties": {"fid": start + i, "凡例コード": "010000"},
        }
        for i in range(count)
    ]
    return json.dumps({"type": "FeatureCollection", "features": features}).encode(
        "utf-8"
    )


class FakeMessageBar:
    """messageBar().pushMessage の呼び出し（タイトル, 本文）を記録するスタブ"""

    def __init__(self):
        self.messages = []

    def pushMessage(self, title, text, level=None, duration=None):
        self.messages.append((title, text))


class FakeIface:
    """アルゴリズムが使う iface.messageBar() だけを持つスタブ"""

    def __init__(self):
        self.message_bar = FakeMessageBar()

    def messageBar(self):
        return self.message_bar


def make_algorithm():
    """通信と e-Stat をモックしたアルゴリズムを返す"""
    iface = FakeIface()
    algorithm = VegetationMapAlgorithm(iface)
    algorithm.estat_client = mock.Mock()
    algorithm.estat_client.fetch_municipality_polygon.return_value = None
    return algorithm, iface


def fetch_sample_fields(algorithm):
    """SAMPLE_LAYER_INFO からフィールド定義を作る"""
    with mock.patch.object(algorithm, "_request", return_value=SAMPLE_LAYER_INFO_BYTES):
        return algorithm._fetch_fields("http://svc/0")


# ========================================
# ロジックのテスト
# ========================================


class TestLogicSettings(unittest.TestCase):
    """設定（都道府県→ブロック→データセット ID）の整合性"""

    def test_all_prefectures_have_dataset_id(self):
        algorithm, _ = make_algorithm()
        for code, _name in real_estate_settings.PREFECTURE_LIST:
            self.assertIn(
                code, settings.PREFECTURE_BLOCK_MAP, f"ブロック未定義: {code}"
            )
            self.assertTrue(algorithm._get_dataset_id(code), f"ID未定義: {code}")

    def test_every_block_has_dataset_id(self):
        for block in set(settings.PREFECTURE_BLOCK_MAP.values()):
            self.assertIn(block, connect.VEGETATION_MAP_DATASET_IDS)

    def test_verified_block_assignments(self):
        # FeatureServer への点クエリで確認済みの所属
        self.assertEqual(settings.PREFECTURE_BLOCK_MAP["19"], "chubu")  # 山梨
        self.assertEqual(settings.PREFECTURE_BLOCK_MAP["20"], "chubu")  # 長野
        self.assertEqual(settings.PREFECTURE_BLOCK_MAP["15"], "hokuriku")  # 新潟
        self.assertEqual(settings.PREFECTURE_BLOCK_MAP["18"], "hokuriku")  # 福井
        self.assertEqual(settings.PREFECTURE_BLOCK_MAP["24"], "kinki")  # 三重

    def test_get_dataset_id_handles_unpadded_and_unknown_codes(self):
        algorithm, _ = make_algorithm()
        self.assertEqual(
            algorithm._get_dataset_id("1"),
            connect.VEGETATION_MAP_DATASET_IDS["hokkaido"],
        )
        self.assertIsNone(algorithm._get_dataset_id("99"))
        self.assertIsNone(algorithm._get_dataset_id(None))


class TestLogicQueryParams(unittest.TestCase):
    """範囲クエリのパラメータ組み立て"""

    def setUp(self):
        self.algorithm, _ = make_algorithm()

    def test_first_page(self):
        params = self.algorithm._build_query_params(BOUNDS)
        self.assertEqual(params["geometry"], "141.3,43.03,141.4,43.09")
        self.assertEqual(params["geometryType"], "esriGeometryEnvelope")
        self.assertEqual(params["inSR"], "4326")
        self.assertEqual(params["outSR"], "4326")
        self.assertEqual(params["outFields"], "*")
        self.assertEqual(params["resultOffset"], 0)
        self.assertEqual(params["resultRecordCount"], connect.PAGE_SIZE)
        self.assertEqual(params["f"], "geojson")
        self.assertNotIn("returnCountOnly", params)

    def test_offset_page(self):
        params = self.algorithm._build_query_params(BOUNDS, offset=4000)
        self.assertEqual(params["resultOffset"], 4000)

    def test_count_only(self):
        params = self.algorithm._build_query_params(BOUNDS, count_only=True)
        self.assertEqual(params["returnCountOnly"], "true")
        self.assertEqual(params["f"], "json")
        self.assertNotIn("resultOffset", params)
        self.assertNotIn("outFields", params)


class TestLogicBounds(unittest.TestCase):
    """市区町村の取得範囲（bbox）の計算"""

    def setUp(self):
        self.algorithm, _ = make_algorithm()

    def test_bounds_from_polygon_with_buffer(self):
        self.algorithm.estat_client.fetch_municipality_polygon.return_value = (
            mock.Mock()
        )
        with mock.patch.object(
            algorithm_module,
            "calculate_municipality_bbox",
            return_value={
                "min_lon": 141.3,
                "min_lat": 43.0,
                "max_lon": 141.4,
                "max_lat": 43.1,
            },
        ):
            bounds = self.algorithm._calculate_bounds("01999")

        buffer = settings.BBOX_BUFFER_DEGREES
        self.assertAlmostEqual(bounds["min_lon"], 141.3 - buffer)
        self.assertAlmostEqual(bounds["max_lat"], 43.1 + buffer)

    def test_bounds_fallback_to_designated_city_defaults(self):
        bounds = self.algorithm._calculate_bounds("01100")  # 札幌市
        self.assertIsNotNone(bounds)
        self.assertLess(bounds["min_lon"], 141.0)

    def test_bounds_none_when_unavailable(self):
        self.assertIsNone(self.algorithm._calculate_bounds("01999"))


class TestLogicFetch(unittest.TestCase):
    """API 応答の解釈とページング"""

    def setUp(self):
        self.algorithm, _ = make_algorithm()

    def test_arcgis_error_payload_raises(self):
        error = json.dumps({"error": {"code": 400, "message": "Invalid query"}})
        with mock.patch.object(
            self.algorithm, "_request", return_value=error.encode("utf-8")
        ):
            with self.assertRaises(Exception) as ctx:
                self.algorithm._fetch_feature_count("http://svc/0", BOUNDS)
        self.assertIn("Invalid query", str(ctx.exception))

    def test_invalid_json_response_raises(self):
        with mock.patch.object(self.algorithm, "_request", return_value=b"<html>"):
            with self.assertRaises(Exception):
                self.algorithm._fetch_fields("http://svc/0")

    def test_resolve_endpoint_from_hub_api(self):
        with mock.patch.object(
            self.algorithm, "_request", return_value=HUB_DATASET_BYTES
        ) as request_mock:
            self.assertEqual(self.algorithm._resolve_endpoint("abc_0"), "http://svc/0")
        self.assertIn("abc_0", request_mock.call_args.args[0])

    def test_resolve_endpoint_raises_when_url_missing(self):
        payload = json.dumps({"data": {"attributes": {"name": "x"}}}).encode("utf-8")
        with mock.patch.object(self.algorithm, "_request", return_value=payload):
            with self.assertRaises(Exception):
                self.algorithm._resolve_endpoint("abc_0")

    def test_fetch_feature_count(self):
        with mock.patch.object(
            self.algorithm, "_request", return_value=b'{"count": 42}'
        ):
            self.assertEqual(
                self.algorithm._fetch_feature_count("http://svc/0", BOUNDS), 42
            )

    def test_fetch_fields_maps_esri_types_and_keeps_japanese_names(self):
        fields = fetch_sample_fields(self.algorithm)
        names = [f.name() for f in fields]
        self.assertEqual(
            names, ["fid", "凡例コード", "凡例名", "植生自然度", "SHAPE__Area"]
        )
        self.assertTrue(fields[fields.indexOf("fid")].isNumeric())
        self.assertFalse(fields[fields.indexOf("凡例コード")].isNumeric())
        self.assertTrue(fields[fields.indexOf("SHAPE__Area")].isNumeric())

    def test_pagination_stops_at_total(self):
        fields = fetch_sample_fields(self.algorithm)
        total = 4010
        pages = [make_page(2000, 0), make_page(2000, 2000), make_page(10, 4000)]
        with mock.patch.object(
            self.algorithm, "_request", side_effect=pages
        ) as request_mock:
            features = self.algorithm._fetch_all_features(
                "http://svc/0", BOUNDS, fields, total
            )

        self.assertEqual(len(features), total)
        self.assertEqual(request_mock.call_count, 3)
        offsets = [call.args[1]["resultOffset"] for call in request_mock.call_args_list]
        self.assertEqual(offsets, [0, 2000, 4000])

    def test_pagination_does_not_loop_when_offset_is_ignored(self):
        # サーバが常に同じ1ページ目を返しても、総件数に達した時点で終了する
        fields = fetch_sample_fields(self.algorithm)
        with mock.patch.object(
            self.algorithm, "_request", return_value=make_page(2000)
        ) as request_mock:
            features = self.algorithm._fetch_all_features(
                "http://svc/0", BOUNDS, fields, 5000
            )
        self.assertEqual(request_mock.call_count, 3)
        self.assertEqual(len(features), 6000)

    def test_pagination_raises_on_error_page(self):
        fields = fetch_sample_fields(self.algorithm)
        error = json.dumps({"error": {"message": "boom"}}).encode("utf-8")
        with mock.patch.object(self.algorithm, "_request", return_value=error):
            with self.assertRaises(Exception):
                self.algorithm._fetch_all_features("http://svc/0", BOUNDS, fields, 10)


# ========================================
# QGIS の機能を使うテスト
# ========================================


class TestQgisParseFeatures(unittest.TestCase):
    """GeoJSON → QgsFeature の変換（QgsJsonUtils）"""

    def setUp(self):
        self.algorithm, _ = make_algorithm()
        self.fields = fetch_sample_fields(self.algorithm)

    def test_attributes_mapped_by_name(self):
        features = self.algorithm._parse_features(
            json.dumps(SAMPLE_GEOJSON), self.fields
        )
        self.assertEqual(len(features), 2)

        by_code = {f["凡例コード"]: f for f in features}
        self.assertEqual(by_code["010000"]["凡例名"], "高山低木群落")
        self.assertEqual(by_code["010000"]["植生自然度"], "10")
        self.assertAlmostEqual(by_code["010000"]["SHAPE__Area"], 12.5)
        self.assertEqual(by_code["010100"]["凡例名"], "ハイマツ群落")
        self.assertEqual(by_code["010000"]["fid"], 1)  # properties に無いので id から
        self.assertEqual(by_code["010100"]["fid"], 2)  # properties の値
        for feature in features:
            self.assertTrue(feature.geometry().isMultipart())

    def test_null_geometry_skipped(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": None, "properties": {"凡例コード": "x"}}
            ],
        }
        self.assertEqual(
            self.algorithm._parse_features(json.dumps(geojson), self.fields), []
        )


def make_qml_bytes() -> bytes:
    """凡例コードで分類するカテゴリ値レンダラーを持つ QML を生成する"""
    source = QgsVectorLayer("MultiPolygon?crs=EPSG:4326", "src", "memory")
    category = QgsRendererCategory(
        "010000", QgsFillSymbol.createSimple({"color": "0,128,0,255"}), "高山低木群落"
    )
    source.setRenderer(
        QgsCategorizedSymbolRenderer(settings.FIELD_LEGEND_CODE, [category])
    )
    document = QDomDocument()
    source.exportNamedStyle(document)
    return bytes(document.toByteArray())


def make_style_zip(qml_bytes: bytes) -> bytes:
    """QML を含むスタイル zip を生成する"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("veg2024style.qml", qml_bytes)
    return buffer.getvalue()


class TestQgisStyle(unittest.TestCase):
    """公式 QML の取得と適用"""

    def setUp(self):
        self.algorithm, _ = make_algorithm()
        self.layer = QgsVectorLayer("MultiPolygon?crs=EPSG:4326", "veg", "memory")

    def test_qml_in_zip_is_applied(self):
        # Hub API で itemId を解決 → arcgis.com から zip を取得
        zip_bytes = make_style_zip(make_qml_bytes())
        with mock.patch.object(
            self.algorithm, "_request", side_effect=[HUB_STYLE_BYTES, zip_bytes]
        ) as request_mock:
            self.assertTrue(self.algorithm.style.apply(self.layer))

        self.assertEqual(request_mock.call_count, 2)
        self.assertIn("item123", request_mock.call_args_list[1].args[0])
        self.assertEqual(self.layer.renderer().type(), "categorizedSymbol")

    def test_zip_without_qml_fails(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("readme.txt", "x")

        with mock.patch.object(
            self.algorithm, "_request", side_effect=[HUB_STYLE_BYTES, buffer.getvalue()]
        ):
            self.assertFalse(self.algorithm.style.apply(self.layer))
        self.assertEqual(self.layer.renderer().type(), "singleSymbol")

    def test_invalid_qml_content_fails(self):
        with mock.patch.object(
            self.algorithm,
            "_request",
            side_effect=[HUB_STYLE_BYTES, make_style_zip(b"this is not xml")],
        ):
            self.assertFalse(self.algorithm.style.apply(self.layer))

    def test_download_failure_returns_false(self):
        with mock.patch.object(
            self.algorithm, "_request", side_effect=Exception("API接続に失敗しました")
        ):
            self.assertFalse(self.algorithm.style.apply(self.layer))


class TestQgisCreateLayer(unittest.TestCase):
    """create_layer の一連の流れ（メモリレイヤー生成と公式 QML の適用）"""

    def test_create_layer_success(self):
        algorithm, iface = make_algorithm()
        # Hub(URL解決) → 件数 → レイヤー情報 → GeoJSON → Hub(スタイル itemId) → zip の順に応答する
        responses = [
            HUB_DATASET_BYTES,
            b'{"count": 2}',
            SAMPLE_LAYER_INFO_BYTES,
            SAMPLE_GEOJSON_BYTES,
            HUB_STYLE_BYTES,
            make_style_zip(make_qml_bytes()),
        ]
        with mock.patch.object(algorithm, "_request", side_effect=responses):
            layer = algorithm.create_layer("01", "01100", "札幌市")

        self.assertIsNotNone(layer)
        self.assertEqual(layer.name(), "現存植生図2024_札幌市（01100）")
        self.assertEqual(layer.featureCount(), 2)
        self.assertEqual(layer.crs().authid(), "EPSG:4326")
        self.assertGreaterEqual(layer.fields().indexOf(settings.FIELD_LEGEND_CODE), 0)
        self.assertEqual(layer.renderer().type(), "categorizedSymbol")
        self.assertEqual(iface.message_bar.messages, [])

    def test_create_layer_returns_none_when_no_features(self):
        algorithm, iface = make_algorithm()
        with mock.patch.object(
            algorithm,
            "_request",
            side_effect=[HUB_DATASET_BYTES, b'{"count": 0}', SAMPLE_LAYER_INFO_BYTES],
        ) as request_mock:
            self.assertIsNone(algorithm.create_layer("01", "01100", "札幌市"))
        # 件数が 0 なので地物取得のリクエストは発生しない
        self.assertEqual(request_mock.call_count, 3)
        self.assertEqual(iface.message_bar.messages[0][0], "情報")

    def test_create_layer_returns_none_on_network_error(self):
        algorithm, iface = make_algorithm()
        with mock.patch.object(
            algorithm, "_request", side_effect=Exception("API接続に失敗しました")
        ):
            self.assertIsNone(algorithm.create_layer("01", "01100", "札幌市"))
        self.assertEqual(iface.message_bar.messages[0][0], "API接続エラー")

    def test_create_layer_returns_none_for_unknown_prefecture(self):
        algorithm, iface = make_algorithm()
        with mock.patch.object(algorithm, "_request") as request_mock:
            self.assertIsNone(algorithm.create_layer("99", "99999", "不明"))
        request_mock.assert_not_called()
        self.assertEqual(iface.message_bar.messages[0][0], "警告")


class TestQgisWorkflow(unittest.TestCase):
    """ワークフロー（プロジェクトへのレイヤー追加）"""

    def test_execute_adds_layer(self):
        workflow = VegetationMapWorkflow(FakeIface())
        layer = QgsVectorLayer("MultiPolygon?crs=EPSG:4326", "veg", "memory")
        workflow.algorithm = mock.Mock()
        workflow.algorithm.create_layer.return_value = layer

        with mock.patch("qgis.core.QgsProject.instance") as project_mock:
            self.assertTrue(workflow.execute("13", "13101", "千代田区"))
        project_mock.return_value.addMapLayer.assert_called_once_with(layer)

    def test_execute_returns_false_when_algorithm_fails(self):
        workflow = VegetationMapWorkflow(FakeIface())
        workflow.algorithm = mock.Mock()
        workflow.algorithm.create_layer.return_value = None

        with mock.patch("qgis.core.QgsProject.instance") as project_mock:
            self.assertFalse(workflow.execute("13", "13101", "千代田区"))
        project_mock.return_value.addMapLayer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
