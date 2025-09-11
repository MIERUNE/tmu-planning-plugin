import requests
import json

# -------------------------------------------------------------------------
# 設定項目：ご自身のe-Stat APIキー（appId）に書き換えてください
# -------------------------------------------------------------------------
# e-StatのAPIキーは、以下のURLから利用者登録をすることで取得できます。
# https://www.e-stat.go.jp/api/api-dev/
app_id = ""
# -------------------------------------------------------------------------


# APIリクエストURLを構築
# statsDataId: 0003445079 (国勢調査 2020年 人口集中地区)
# cdArea: 01100 (北海道札幌市)
# cdCat01: 0000A (総人口)
url = (
    f"https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData?"
    f"appId={app_id}&"
    f"lang=J&"
    f"statsDataId=0003445079&"
    f"limit=10&"
    f"cdArea=01100&"
    f"cdCat02=0"
)

print(f"リクエストURL: {url}")
print("-" * 30)

try:
    # APIにリクエストを送信
    response = requests.get(url)
    # エラーがあれば例外を発生させる
    response.raise_for_status()

    # レスポンスをJSON形式で解析
    data = response.json()

    # 取得したデータを整形してコンソールに出力
    # indent=2: 見やすいようにインデントをつけます
    # ensure_ascii=False: 日本語が文字化けしないようにします
    pretty_json = json.dumps(data, indent=2, ensure_ascii=False)
    print("--- APIレスポンス (全体) ---")
    print(pretty_json)

    # 必要な統計データ部分を抽出して表示
    print("\n--- 抽出した統計データ ---")
    statistical_data = data.get('GET_STATS_DATA', {}).get('STATISTICAL_DATA', {})
    data_values = statistical_data.get('DATA_INF', {}).get('VALUE', [])

    # APIのレスポンスは、データが1件の場合に辞書、複数件の場合にリストを返すため、
    # 常にリストとして扱えるように型をチェックして変換します。
    if isinstance(data_values, dict):
        data_values = [data_values]

    if not data_values:
        result_info = data.get('GET_STATS_DATA', {}).get('RESULT', {})
        error_msg = result_info.get('ERROR_MSG', 'データが見つかりませんでした。')
        print(f"エラー: {error_msg}")
    else:
        # 地域コードと地域名を対応付ける辞書を作成
        area_map = {}
        class_objects = statistical_data.get('CLASS_INF', {}).get('CLASS_OBJ', [])
        
        # CLASS_OBJもデータが1件の場合に辞書となるケースに対応します。
        if isinstance(class_objects, dict):
            class_objects = [class_objects]

        for class_obj in class_objects:
            # CLASSがリストではない場合に対応
            if isinstance(class_obj, dict) and class_obj.get('@id') == 'area':
                classes = class_obj.get('CLASS', [])
                if isinstance(classes, dict):
                    classes = [classes]
                for category in classes:
                    if isinstance(category, dict):
                        area_map[category.get('@code')] = category.get('@name')

        # データを一つずつ表示
        for value_data in data_values:
            area_code = value_data.get('@area')
            area_name = area_map.get(area_code, '不明な地域')
            value = value_data.get('$')
            unit = value_data.get('@unit')
            print(f"地域: {area_name} ({area_code}) | 人口: {value} {unit}")

except requests.exceptions.RequestException as e:
    print(f"\n[エラー] ネットワーク接続に問題がある可能性があります: {e}")
except json.JSONDecodeError:
    print("\n[エラー] APIレスポンスの解析に失敗しました。不正なJSONデータです。")
except Exception as e:
    print(f"\n[エラー] 予期せぬエラーが発生しました: {e}")

