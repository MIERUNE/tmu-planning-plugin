"""
現存植生図2024（環境ジオポータル）データの取得機能モジュール
"""

import json
import traceback
from typing import Dict, List, Optional

from qgis.core import (
    Qgis,
    QgsBlockingNetworkRequest,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsJsonUtils,
    QgsMessageLog,
    QgsVariantUtils,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QMetaType, QUrl, QUrlQuery
from qgis.PyQt.QtNetwork import QNetworkRequest

from ...utils.estat.bbox import calculate_municipality_bbox
from ...utils.estat.client import AdministrativeAreaClient
from ...utils.settings import CITY_DEFAULT_BOUNDS, PLUGIN_NAME
from .connect import (
    PAGE_SIZE,
    QUERY_PATH,
    RESPONSE_ENCODING,
    STYLE_ZIP_URL,
    VEGETATION_MAP_API_ENDPOINTS,
)
from .settings import (
    BBOX_BUFFER_DEGREES,
    BLOCK_NAMES,
    LAYER_NAME_PREFIX,
    PREFECTURE_BLOCK_MAP,
)
from .style import VegetationMapStyle

# ArcGIS のフィールド型 → QMetaType（未定義の型は文字列として扱う）
ESRI_TYPE_TO_QMETATYPE = {
    "esriFieldTypeOID": QMetaType.Type.LongLong,
    "esriFieldTypeInteger": QMetaType.Type.Int,
    "esriFieldTypeSmallInteger": QMetaType.Type.Int,
    "esriFieldTypeBigInteger": QMetaType.Type.LongLong,
    "esriFieldTypeDouble": QMetaType.Type.Double,
    "esriFieldTypeSingle": QMetaType.Type.Double,
    "esriFieldTypeString": QMetaType.Type.QString,
}

# レイヤー定義に含まれるが属性として持たないフィールド型
ESRI_SKIP_TYPES = ("esriFieldTypeGeometry", "esriFieldTypeBlob", "esriFieldTypeRaster")


class VegetationMapAlgorithm:
    """現存植生図2024データ取得クラス"""

    def __init__(self, iface):
        self.iface = iface
        self.estat_client = AdministrativeAreaClient(PLUGIN_NAME)
        self.style = VegetationMapStyle(self._download_style_zip)

    # ========================================
    # 取得条件の決定
    # ========================================

    def _get_endpoint(self, prefecture_code: Optional[str]) -> Optional[str]:
        """
        都道府県コードから地域ブロックの FeatureServer レイヤーURLを取得する
        Args:
            prefecture_code (str, optional): 都道府県コード（2桁）
        Returns:
            str: レイヤーURL。対応するブロックが無い場合は None
        """
        if not prefecture_code:
            return None
        block_key = PREFECTURE_BLOCK_MAP.get(str(prefecture_code).zfill(2))
        if block_key is None:
            return None
        return VEGETATION_MAP_API_ENDPOINTS.get(block_key)

    def _get_block_name(self, prefecture_code: Optional[str]) -> str:
        """都道府県コードから地域ブロックの表示名を取得する"""
        if not prefecture_code:
            return "不明"
        block_key = PREFECTURE_BLOCK_MAP.get(str(prefecture_code).zfill(2))
        if block_key is None:
            return "不明"
        return BLOCK_NAMES.get(block_key, "不明")

    def _calculate_bounds(self, municipality_code: str) -> Optional[Dict[str, float]]:
        """
        市区町村のbboxを取得し、バッファを追加した境界範囲を計算する
        Args:
            municipality_code (str): 市区町村コード（5桁）
        Returns:
            dict: {"min_lon", "min_lat", "max_lon", "max_lat"}。計算できない場合は None
        """
        municipality_layer = self.estat_client.fetch_municipality_polygon(
            municipality_code
        )
        bbox = (
            calculate_municipality_bbox(municipality_layer)
            if municipality_layer is not None
            else None
        )

        if not bbox:
            # 行政区域が取得できない場合は政令指定都市のデフォルト境界範囲を使用
            bbox = CITY_DEFAULT_BOUNDS.get(municipality_code)
            if not bbox:
                return None

        return {
            "min_lon": bbox["min_lon"] - BBOX_BUFFER_DEGREES,
            "min_lat": bbox["min_lat"] - BBOX_BUFFER_DEGREES,
            "max_lon": bbox["max_lon"] + BBOX_BUFFER_DEGREES,
            "max_lat": bbox["max_lat"] + BBOX_BUFFER_DEGREES,
        }

    # ========================================
    # API アクセス
    # ========================================

    def _request(self, url: str, params: Dict[str, object]) -> bytes:
        """
        GETリクエストを実行してレスポンス本文を返す
        Args:
            url (str): リクエスト先URL
            params (dict): クエリパラメータ
        Returns:
            bytes: レスポンス本文
        Raises:
            Exception: 通信失敗、HTTPエラー、空レスポンス時
        """
        query = QUrlQuery()
        for key, value in params.items():
            query.addQueryItem(key, str(value))
        qurl = QUrl(url)
        qurl.setQuery(query)

        request = QNetworkRequest(qurl)
        blocking_request = QgsBlockingNetworkRequest()
        error_code = blocking_request.get(request)

        if error_code != QgsBlockingNetworkRequest.ErrorCode.NoError:
            http_status = blocking_request.reply().attribute(
                QNetworkRequest.Attribute.HttpStatusCodeAttribute
            )
            raise Exception(
                f"API接続に失敗しました: {blocking_request.errorMessage()} "
                f"(HTTPステータス: {http_status})"
            )

        data = bytes(blocking_request.reply().content())
        if not data:
            raise Exception(f"APIからのレスポンスが空です: {qurl.toString()}")
        return data

    def _request_json(self, url: str, params: Dict[str, object]) -> dict:
        """
        GETリクエストを実行してJSONとして返す
        ArcGIS REST はエラーも HTTP 200 で {"error": ...} として返すため、ここで例外にする
        """
        raw = self._request(url, params)
        try:
            payload = json.loads(raw.decode(RESPONSE_ENCODING))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise Exception(f"APIレスポンスの解析に失敗しました: {e}") from e

        if isinstance(payload, dict) and "error" in payload:
            error = payload["error"]
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise Exception(f"APIエラー応答: {message}")
        return payload

    def _build_query_params(
        self, bounds: Dict[str, float], offset: int = 0, count_only: bool = False
    ) -> Dict[str, object]:
        """
        範囲クエリのパラメータを組み立てる
        Args:
            bounds (dict): 取得範囲（EPSG:4326）
            offset (int): ページングのオフセット
            count_only (bool): True なら件数のみ取得
        Returns:
            dict: クエリパラメータ
        """
        params: Dict[str, object] = {
            "where": "1=1",
            "geometry": (
                f"{bounds['min_lon']},{bounds['min_lat']},"
                f"{bounds['max_lon']},{bounds['max_lat']}"
            ),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
        }
        if count_only:
            params["returnCountOnly"] = "true"
            params["f"] = "json"
        else:
            params["outFields"] = "*"
            params["outSR"] = "4326"
            params["resultOffset"] = offset
            params["resultRecordCount"] = PAGE_SIZE
            params["f"] = "geojson"
        return params

    def _fetch_fields(self, endpoint: str) -> QgsFields:
        """
        FeatureServer のレイヤー情報からフィールド定義を作る（日本語名はそのまま保持）
        Args:
            endpoint (str): レイヤーURL
        Returns:
            QgsFields: フィールド定義
        """
        layer_info = self._request_json(endpoint, {"f": "json"})
        fields = QgsFields()
        for field_def in layer_info.get("fields") or []:
            name = field_def.get("name")
            esri_type = field_def.get("type", "")
            if not name or esri_type in ESRI_SKIP_TYPES:
                continue
            qtype = ESRI_TYPE_TO_QMETATYPE.get(esri_type, QMetaType.Type.QString)
            fields.append(QgsField(name, qtype))
        return fields

    def _fetch_feature_count(self, endpoint: str, bounds: Dict[str, float]) -> int:
        """
        範囲内の地物数を取得する
        Args:
            endpoint (str): レイヤーURL
            bounds (dict): 取得範囲
        Returns:
            int: 地物数
        """
        payload = self._request_json(
            endpoint + QUERY_PATH, self._build_query_params(bounds, count_only=True)
        )
        return int(payload.get("count", 0))

    def _download_style_zip(self) -> bytes:
        """
        公式スタイル設定ファイル（QML を含む zip）をダウンロードする
        Returns:
            bytes: zip の内容
        """
        return self._request(STYLE_ZIP_URL, {})

    # ========================================
    # レイヤー構築
    # ========================================

    def _parse_features(self, geojson_text: str, fields: QgsFields) -> List[QgsFeature]:
        """
        GeoJSON を QgsFeature に変換する
        GeoJSON の properties はレイヤー定義と順序が異なるため、フィールド名で対応づける
        Args:
            geojson_text (str): GeoJSON 文字列
            fields (QgsFields): レイヤーのフィールド定義
        Returns:
            List[QgsFeature]: 地物（空ジオメトリは除外）
        """
        source_fields = QgsJsonUtils.stringToFields(geojson_text)
        source_features = QgsJsonUtils.stringToFeatureList(geojson_text, source_fields)

        index_map = []
        for source_index in range(source_fields.count()):
            target_index = fields.indexOf(source_fields[source_index].name())
            if target_index >= 0:
                index_map.append((source_index, target_index))
        fid_index = fields.indexOf("fid")

        features = []
        for source_feature in source_features:
            geometry = source_feature.geometry()
            if geometry.isNull() or geometry.isEmpty():
                continue
            geometry.convertToMultiType()

            feature = QgsFeature(fields)
            feature.setGeometry(geometry)
            source_attributes = source_feature.attributes()
            for source_index, target_index in index_map:
                feature.setAttribute(target_index, source_attributes[source_index])
            # properties に fid が無い場合は Feature の id で補完する
            if fid_index >= 0 and QgsVariantUtils.isNull(feature.attribute(fid_index)):
                feature.setAttribute(fid_index, source_feature.id())
            features.append(feature)
        return features

    def _fetch_all_features(
        self,
        endpoint: str,
        bounds: Dict[str, float],
        fields: QgsFields,
        total: int,
    ) -> List[QgsFeature]:
        """
        範囲クエリをページングして全地物を取得する
        総件数に達した時点で終了するため、サーバがオフセットを無視しても無限ループにならない
        Args:
            endpoint (str): レイヤーURL
            bounds (dict): 取得範囲
            fields (QgsFields): レイヤーのフィールド定義
            total (int): 総件数
        Returns:
            List[QgsFeature]: 取得した地物
        """
        features: List[QgsFeature] = []
        offset = 0

        while offset < total:
            raw = self._request(
                endpoint + QUERY_PATH, self._build_query_params(bounds, offset=offset)
            )
            geojson_text = raw.decode(RESPONSE_ENCODING)

            payload = json.loads(geojson_text)
            if isinstance(payload, dict) and "error" in payload:
                raise Exception(f"APIエラー応答: {payload['error']}")
            page_count = len(payload.get("features") or [])
            if page_count == 0:
                break

            features.extend(self._parse_features(geojson_text, fields))
            offset += page_count

            if page_count < PAGE_SIZE:
                break

        return features

    # ========================================
    # workflow から呼び出されるパブリックメソッド
    # ========================================

    def create_layer(
        self,
        prefecture_code: Optional[str],
        municipality_code: str,
        municipality_name: Optional[str],
    ) -> Optional[QgsVectorLayer]:
        """
        現存植生図2024 を市区町村の範囲で取得し、スタイルを適用したメモリレイヤーを返す
        Args:
            prefecture_code (str, optional): 都道府県コード（2桁）
            municipality_code (str): 市区町村コード（5桁）
            municipality_name (str, optional): 市区町村名
        Returns:
            QgsVectorLayer: 取得に成功した場合はレイヤーオブジェクト。失敗時は None
        """
        endpoint = self._get_endpoint(prefecture_code)
        if endpoint is None:
            self.iface.messageBar().pushMessage(
                "警告",
                f"都道府県コード「{prefecture_code}」に対応する"
                f"{LAYER_NAME_PREFIX}の地域ブロックが見つかりません。",
                level=Qgis.MessageLevel.Warning,
            )
            return None

        display_name = (
            f"{municipality_name}（{municipality_code}）"
            if municipality_name
            else municipality_code
        )

        # 取得範囲の計算
        bounds = self._calculate_bounds(municipality_code)
        if not bounds:
            self.iface.messageBar().pushMessage(
                "エラー",
                f"市区町村「{display_name}」の範囲を取得できませんでした。",
                level=Qgis.MessageLevel.Warning,
            )
            return None

        try:
            # 件数の確認
            total = self._fetch_feature_count(endpoint, bounds)
            if total == 0:
                self.iface.messageBar().pushMessage(
                    "情報",
                    f"市区町村「{display_name}」の範囲には"
                    f"{LAYER_NAME_PREFIX}のデータが存在しません。",
                    level=Qgis.MessageLevel.Info,
                )
                return None

            # フィールド定義と地物の取得
            fields = self._fetch_fields(endpoint)
            features = self._fetch_all_features(endpoint, bounds, fields, total)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"{e}\n{traceback.format_exc()}",
                PLUGIN_NAME,
                level=Qgis.MessageLevel.Critical,
            )
            self.iface.messageBar().pushMessage(
                "API接続エラー",
                f"{LAYER_NAME_PREFIX}の取得に失敗しました。{e}",
                level=Qgis.MessageLevel.Critical,
            )
            return None

        if not features:
            self.iface.messageBar().pushMessage(
                "情報",
                f"市区町村「{display_name}」の範囲には"
                f"{LAYER_NAME_PREFIX}のデータが存在しません。",
                level=Qgis.MessageLevel.Info,
            )
            return None

        # メモリレイヤーの作成
        layer_name = f"{LAYER_NAME_PREFIX}_{display_name}"
        layer = QgsVectorLayer("MultiPolygon?crs=EPSG:4326", layer_name, "memory")
        provider = layer.dataProvider()
        if provider is None:
            self.iface.messageBar().pushMessage(
                "エラー",
                f"{LAYER_NAME_PREFIX}のレイヤー作成に失敗しました。",
                level=Qgis.MessageLevel.Critical,
            )
            return None
        provider.addAttributes(fields.toList())
        layer.updateFields()
        provider.addFeatures(features)
        layer.updateExtents()

        # スタイルの設定
        if not self.style.apply(layer):
            self.iface.messageBar().pushMessage(
                "警告",
                f"{LAYER_NAME_PREFIX}のスタイル適用に失敗したため、既定のシンボルで表示します。",
                level=Qgis.MessageLevel.Warning,
            )

        return layer
