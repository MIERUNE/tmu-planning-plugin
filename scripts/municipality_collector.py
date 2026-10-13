"""
全国47都道府県の市区町村データを収集するスクリプトです。
"""

import json
from pathlib import Path
from typing import List, Tuple, Dict, Any

from qgis.PyQt.QtCore import QEventLoop, QUrl, QByteArray
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest
from qgis.core import QgsNetworkAccessManager

# =============================================================================
# 設定値
# =============================================================================

API_KEY = ""  # 不動産情報ライブラリAPIキーを入力してください
BASE_URL = "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT002"
RESPONSE_ENCODING = "utf-8-sig"

# 全国47都道府県
ALL_PREFECTURES = [
    ("01", "北海道"),
    ("02", "青森県"),
    ("03", "岩手県"),
    ("04", "宮城県"),
    ("05", "秋田県"),
    ("06", "山形県"),
    ("07", "福島県"),
    ("08", "茨城県"),
    ("09", "栃木県"),
    ("10", "群馬県"),
    ("11", "埼玉県"),
    ("12", "千葉県"),
    ("13", "東京都"),
    ("14", "神奈川県"),
    ("15", "新潟県"),
    ("16", "富山県"),
    ("17", "石川県"),
    ("18", "福井県"),
    ("19", "山梨県"),
    ("20", "長野県"),
    ("21", "岐阜県"),
    ("22", "静岡県"),
    ("23", "愛知県"),
    ("24", "三重県"),
    ("25", "滋賀県"),
    ("26", "京都府"),
    ("27", "大阪府"),
    ("28", "兵庫県"),
    ("29", "奈良県"),
    ("30", "和歌山県"),
    ("31", "鳥取県"),
    ("32", "島根県"),
    ("33", "岡山県"),
    ("34", "広島県"),
    ("35", "山口県"),
    ("36", "徳島県"),
    ("37", "香川県"),
    ("38", "愛媛県"),
    ("39", "高知県"),
    ("40", "福岡県"),
    ("41", "佐賀県"),
    ("42", "長崎県"),
    ("43", "熊本県"),
    ("44", "大分県"),
    ("45", "宮崎県"),
    ("46", "鹿児島県"),
    ("47", "沖縄県"),
]

# =============================================================================
# 全国対応データ収集クラス
# =============================================================================


class NationwideCollector:
    """全国47都道府県対応のデータ収集クラス"""

    def __init__(self):
        self.all_data = {}
        self.output_file = Path.home() / "Desktop" / "municipalities_nationwide.json"
        self.progress_file = Path.home() / "Desktop" / "collection_progress.txt"
        self.success_count = 0
        self.error_count = 0
        self.total_municipalities = 0

    def get_municipalities(
        self, prefecture_code: str, api_key: str, base_url: str
    ) -> List[Tuple[str, str]]:
        """市区町村データ取得"""
        url_string = f"{base_url}?area={prefecture_code}&sc={api_key}"

        try:
            response_data = self._fetch_api_data(url_string, api_key)
            if response_data is None or response_data.isEmpty():
                return []

            data = self._decode_response(response_data, prefecture_code)
            if data is None:
                return []

            municipalities = self._parse_municipalities(data, prefecture_code)
            if municipalities:
                municipalities.sort(key=lambda x: x[0])
                return municipalities
            else:
                return []

        except Exception as e:
            print(f"   ❌ エラー: {str(e)}")
            return []

    def _fetch_api_data(self, url_string: str, api_key: str) -> QByteArray:
        """APIからデータを取得"""
        url = QUrl(url_string)
        request = QNetworkRequest(url)
        request.setRawHeader(b"Ocp-Apim-Subscription-Key", api_key.encode("utf-8"))

        nam = QgsNetworkAccessManager.instance()
        reply = nam.get(request)
        loop = QEventLoop()
        reply.finished.connect(loop.quit)
        loop.exec()

        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                http_status = reply.attribute(
                    QNetworkRequest.Attribute.HttpStatusCodeAttribute
                )
                raise Exception(f"HTTP {http_status}: {reply.errorString()}")
            return reply.readAll()
        finally:
            reply.deleteLater()

    def _decode_response(
        self, response_data: QByteArray, prefecture_code: str
    ) -> Dict[str, Any]:
        """レスポンスデータをデコード"""
        try:
            response_string = response_data.data().decode(RESPONSE_ENCODING)
            return json.loads(response_string)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _parse_municipalities(self, data, prefecture_code) -> List[Tuple[str, str]]:
        """APIレスポンスから市区町村データを抽出"""
        municipalities = []

        try:
            if (
                isinstance(data, dict)
                and "data" in data
                and isinstance(data["data"], list)
            ):
                for item in data["data"]:
                    if isinstance(item, dict):
                        muni_code = (
                            item.get("市区町村コード")
                            or item.get("id")
                            or item.get("code")
                        )
                        muni_name = item.get("市区町村名") or item.get("name")

                        if muni_code and muni_name:
                            municipalities.append((str(muni_code), str(muni_name)))

            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        muni_code = (
                            item.get("市区町村コード")
                            or item.get("id")
                            or item.get("code")
                        )
                        muni_name = item.get("市区町村名") or item.get("name")

                        if muni_code and muni_name:
                            municipalities.append((str(muni_code), str(muni_name)))

        except Exception:
            pass

        return municipalities

    def collect_single_prefecture(
        self, prefecture_code: str, prefecture_name: str, index: int, total: int
    ):
        """単一都道府県のデータを収集"""
        print(f"[{index:2d}/{total}] 📍 {prefecture_code}: {prefecture_name}", end=" ")

        municipalities = self.get_municipalities(prefecture_code, API_KEY, BASE_URL)

        # データを蓄積
        self.all_data[prefecture_code] = municipalities

        # 結果表示
        if municipalities:
            count = len(municipalities)
            print(f"✅ {count}件")
            self.success_count += 1
            self.total_municipalities += count
        else:
            print("⚠️ データなし")
            self.error_count += 1

        # 進捗保存
        self.save_progress(
            index, total, prefecture_code, prefecture_name, len(municipalities)
        )

        # 10都道府県ごとに中間保存
        if index % 10 == 0 or index == total:
            self.save_intermediate(index, total)

        return len(municipalities)

    def save_progress(
        self,
        index: int,
        total: int,
        prefecture_code: str,
        prefecture_name: str,
        count: int,
    ):
        """進捗をテキストファイルに保存"""
        try:
            status = "✅" if count > 0 else "⚠️"
            progress_text = f"[{index:2d}/{total}] {status} {prefecture_code}: {prefecture_name} - {count}件\n"

            with open(self.progress_file, "a", encoding="utf-8") as f:
                f.write(progress_text)

        except Exception:
            pass

    def save_intermediate(self, current_index: int, total: int):
        """中間保存"""
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(self.all_data, f, ensure_ascii=False, indent=2)

            print(
                f"   💾 中間保存 [{current_index}/{total}]: {len(self.all_data)}都道府県 {self.total_municipalities}件"
            )

        except Exception as e:
            print(f"   ❌ 中間保存エラー: {e}")

    def collect_all_prefectures(self):
        """全47都道府県を収集"""
        print("🚀 全国47都道府県のデータ収集開始")
        print("=" * 70)
        print(f"📡 API URL: {BASE_URL}")
        print(f"🔑 API Key: {API_KEY[:8]}...")
        print("=" * 70)

        # 進捗ファイルを初期化
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                f.write("全国市区町村データ収集進捗\n")
                f.write("=" * 50 + "\n")
        except Exception:
            pass

        # 全都道府県を処理
        total = len(ALL_PREFECTURES)
        for i, (prefecture_code, prefecture_name) in enumerate(ALL_PREFECTURES, 1):
            self.collect_single_prefecture(prefecture_code, prefecture_name, i, total)

            # API負荷軽減のため少し待機（1秒）
            if i < total:  # 最後以外
                import time

                time.sleep(1)

        # 最終結果
        self.show_final_results()

    def show_final_results(self):
        """最終結果を表示"""
        print("\n" + "=" * 70)
        print("🎉 全国データ収集完了！")
        print("=" * 70)
        print(f"   ✅ 成功都道府県: {self.success_count}/47")
        print(f"   ⚠️  失敗都道府県: {self.error_count}/47")
        print(f"   📈 総市区町村数: {self.total_municipalities:,}件")
        print(f"   📁 保存先: {self.output_file}")
        print(f"   📋 進捗ログ: {self.progress_file}")

        # ファイルサイズ表示
        if self.output_file.exists():
            file_size = self.output_file.stat().st_size
            print(
                f"   💾 ファイルサイズ: {file_size:,} bytes ({file_size / 1024:.1f} KB)"
            )

        # 地域別統計
        self.show_regional_statistics()

    def show_regional_statistics(self):
        """地域別統計を表示"""
        print("\n📊 地域別統計:")

        regions = {
            "北海道・東北": ["01", "02", "03", "04", "05", "06", "07"],
            "関東": ["08", "09", "10", "11", "12", "13", "14"],
            "中部": ["15", "16", "17", "18", "19", "20", "21", "22", "23"],
            "近畿": ["24", "25", "26", "27", "28", "29", "30"],
            "中国": ["31", "32", "33", "34", "35"],
            "四国": ["36", "37", "38", "39"],
            "九州・沖縄": ["40", "41", "42", "43", "44", "45", "46", "47"],
        }

        for region_name, prefecture_codes in regions.items():
            region_count = 0
            region_prefectures = 0

            for code in prefecture_codes:
                if code in self.all_data:
                    municipalities = self.all_data[code]
                    if municipalities:
                        region_count += len(municipalities)
                        region_prefectures += 1

            print(
                f"   {region_name}: {region_prefectures}/{len(prefecture_codes)}都道府県 {region_count}件"
            )

    def verify_and_show_sample(self):
        """データ検証とサンプル表示"""
        print("\n🔍 データ検証:")

        # いくつかの都道府県のサンプルを表示
        sample_prefectures = ["01", "13", "27", "40"]  # 北海道、東京、大阪、福岡

        for code in sample_prefectures:
            if code in self.all_data:
                municipalities = self.all_data[code]
                pref_name = dict(ALL_PREFECTURES).get(code, f"都道府県{code}")

                if municipalities:
                    print(f"\n   📋 {code} {pref_name} ({len(municipalities)}件):")
                    for i, (muni_code, muni_name) in enumerate(municipalities[:5]):
                        print(f"      {muni_code}: {muni_name}")
                    if len(municipalities) > 5:
                        print(f"      ... 他{len(municipalities) - 5}件")
                else:
                    print(f"\n   ⚠️  {code} {pref_name}: データなし")


# =============================================================================
# 実行関数
# =============================================================================


def run_nationwide_collection():
    """全国収集を実行"""
    collector = NationwideCollector()

    print("全国47都道府県 市区町村データ収集")
    print("=" * 70)

    # 確認メッセージ
    print("⚠️  注意: 全47都道府県のデータ収集には時間がかかります")
    print("   - 各都道府県間で1秒の間隔を空けます")
    print("   - 10都道府県ごとに中間保存を行います")
    print("   - 進捗はファイルにも保存されます")
    print("=" * 70)

    # 収集開始
    collector.collect_all_prefectures()

    # データ検証
    collector.verify_and_show_sample()


# =============================================================================
# 実行
# =============================================================================

print("市区町村データ取得スクリプト（全国47都道府県対応）")
print("=" * 70)

# 全国収集実行
run_nationwide_collection()
