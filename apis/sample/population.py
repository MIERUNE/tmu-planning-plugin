import json

from PyQt5.QtCore import QEventLoop, QUrl, QVariant
from PyQt5.QtNetwork import QNetworkReply, QNetworkRequest
from qgis.core import Qgis, QgsField, QgsMessageLog, QgsNetworkAccessManager, QgsProject


# ログメッセージをシンプルに出力するヘルパー関数
def log(message, level=Qgis.Info):
    """QGISのメッセージログにメッセージを出力します。"""
    QgsMessageLog.logMessage(message, "e-Stat API", level)


# --- 1. e-Stat APIからデータを取得する関数 ---
def get_estat_population_data(api_key, stats_data_id, area_code, class_code):
    """e-Stat APIから人口データを取得し、JSONを返す"""

    base_url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    url_string = f"{base_url}?appId={api_key}&statsDataId={stats_data_id}&cdArea={area_code}&cdCat01={class_code}"
    url = QUrl(url_string)
    request = QNetworkRequest(url)

    # ネットワークリクエストを実行
    nam = QgsNetworkAccessManager.instance()
    reply = nam.get(request)

    # レスポンスの待機と取得
    loop = QEventLoop()
    reply = nam.get(request)
    reply.finished.connect(loop.quit)
    loop.exec_()

    if reply.error() != QNetworkReply.NoError:
        error_string = reply.errorString()
        log(
            f"ネットワークリクエスト中にエラーが発生しました: {error_string}",
            Qgis.Critical,
        )
        return None

    response_data = reply.readAll().data().decode("utf-8")
    reply.deleteLater()

    try:
        json_data = json.loads(response_data)

        log("e-Stat APIからのJSONデータの取得に成功しました。", Qgis.Info)
        return json_data

    except json.JSONDecodeError as e:
        error_message = f"JSONのパース中にエラーが発生しました: {e}"
        log(error_message, Qgis.Critical)
        return None


# --- 2. 取得した人口データをQGISのレイヤーに結合する関数 ---
def update_population_to_layer(layer_name, area_code, population_value):
    """指定されたレイヤーの属性テーブルを人口データで更新します。"""
    if population_value is None:
        QgsMessageLog.logMessage(
            "人口データが無効なため、レイヤーの更新をスキップします。",
            "e-Stat API",
            Qgis.Critical,
        )
        return

    # レイヤーを取得
    layers = QgsProject.instance().mapLayersByName("hokkaido_prefecture")
    if not layers:
        log("レイヤー 'hokkaido_prefecture' が見つかりませんでした。", Qgis.Critical)
        return

    layer = layers[0]
    layer_provider = layer.dataProvider()

    # レイヤーの編集を開始
    if not layer.isEditable():
        layer.startEditing()
        log(f"レイヤー '{layer.name()}' の編集を開始しました。", Qgis.Info)

    # 'POPULATION' フィールドが存在しない場合は追加
    if layer.fields().indexOf("POPULATION") == -1:
        success = layer_provider.addAttributes([QgsField("POPULATION", QVariant.Int)])
        if success:
            layer.updateFields()
            QgsMessageLog.logMessage(
                "新しいカラム 'POPULATION' を作成しました。",
                "e-Stat API",
                Qgis.Info,
            )
        else:
            log("カラム 'POPULATION' の作成に失敗しました。", Qgis.Critical)
            layer.rollBack()
            raise Exception("Failed to add new field.")

    population_field_idx = layer.fields().indexOf("POPULATION")
    administra_field_idx = layer.fields().indexOf("area_code")

    # administraフィールドが存在しない場合はreturn
    if population_field_idx == -1 or administra_field_idx == -1:
        log("必要なカラム 'POPULATION' または 'area_code' が見つかりません。", Qgis.Critical)
        layer.rollBack()
        return

    changes = {}
    for feature in layer.getFeatures():
        # administraカラムの値を取得（文字列として取得）
        administra_value = feature["area_code"]
        if str(administra_value) == str(area_code):
            changes[feature.id()] = {population_field_idx: population_value}
            log(f"一致: area_code='{administra_value}' に人口データ '{population_value}' を設定します。", Qgis.Info)
        else:
            changes[feature.id()] = {population_field_idx: None}

    # 変更をまとめて適用し
    if changes:
        layer.dataProvider().changeAttributeValues(changes)
        layer.commitChanges()
        log("属性テーブルの更新と変更の確定が完了しました。", Qgis.Info)
    else:
        log("更新するデータが見つかりませんでした。", Qgis.Warning)


# --- 3. メイン処理の実行 ---
def main():
    # TODO : パラメーターとAPIキーはユーザーが選択したものに置き換える
    API_KEY = "826caa70ecafc235546d72631891eb6d13d2028e"
    STATS_DATA_ID = "0003433219"
    AREA_CODE = "01101"  # 北海道
    CLASS_CODE = "0"  # 総人口の分類項目コード

    # 1. APIから人口データを取得
    json_data = get_estat_population_data(API_KEY, STATS_DATA_ID, AREA_CODE, CLASS_CODE)
    if not json_data:
        return

    # 2. JSONデータから必要な値を取り出す
    population_value = None
    try:
        statistical_data = json_data.get("GET_STATS_DATA", {}).get(
            "STATISTICAL_DATA", {}
        )
        value_data = statistical_data.get("DATA_INF", {}).get("VALUE", {})

        # データの取得と数値への変換
        get_area_code = value_data.get("@area")
        population_value_str = value_data.get("$")

        if get_area_code and population_value_str:
            if str(get_area_code) == str(AREA_CODE):
                population_value = int(population_value_str)
                log(f"人口データ取得成功: {population_value}人", Qgis.Info)
            else:
                log(
                    f"取得した地域コード'{get_area_code}'が指定と一致しません。",
                    Qgis.Warning,
                )
        else:
            log("JSONから必要なデータが見つかりませんでした。", Qgis.Warning)

    except (ValueError, TypeError) as e:
        log(f"人口データを数値に変換できませんでした: {e}", Qgis.Critical)

    # 3. 取得した人口データをQGISレイヤーに反映
    layer_to_update = "hokkaido_prefecture"
    update_population_to_layer(layer_to_update, AREA_CODE, population_value)


# スクリプトを実行
main()
