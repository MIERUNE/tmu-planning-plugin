# GreenInfraPlannerJP

## 1. 概要

このプラグインは、国土交通データプラットフォームや各省庁のオープンデータを QGIS 上で統合的に可視化し、グリーンインフラ計画の策定を支援することを目的としています。

- **主な技術**: QGIS 3, Python 3.9+, PyQGIS, `uv`
- **連携 API**: 国土地理院, 不動産情報ライブラリ, 海しる API, e-Stat API, ハザードマップポータルサイト

---

## 2. 主な機能

本プラグインが提供する機能を API ソース別に整理します。

### 国土地理院（GSI ベクトルタイル）

**実装**: `basemap/basemap_algorithm.py`

- ベースマップ表示（高速道路 / 水域 / 道路 / 建物）
- タイル取得 URL: `https://cyberjapandata.gsi.go.jp/xyz/experimental_bvmap/{z}/{x}/{y}.pbf`

### 行政区域ポリゴン

**実装**: `administrative_area/`

- 行政区域データの表示（MBTiles 形式のローカルデータを使用）
- 3 種類の表示モードに対応:

| モード     | 説明                             | 属性フィールド |
| ---------- | -------------------------------- | -------------- |
| ベース(白) | 行政区域を白色で表示             | -              |
| class3     | 3 区分の行政区域分類で色分け表示 | `class3info`   |
| class5     | 5 区分の行政区域分類で色分け表示 | `class5nofo`   |

- データソース: ローカル MBTiles ファイル（`features/administrative_area/data/class.mbtiles`）
- ベースマップグループ内の「行政区域」サブグループに追加

### 国土交通省 不動産情報ライブラリ（MLIT Reinfolib）

**実装**: `real_estate_lib/`

| 機能                    | エンドポイント | アルゴリズム                               |
| ----------------------- | -------------- | ------------------------------------------ |
| 都市計画区域 / 区域区分 | `XKT001`       | `urban_planning_algorithm.py`              |
| 用途地域                | `XKT002`       | `zoning_district_algorithm.py`             |
| 地区計画                | `XKT023`       | `district_plan_algorithm.py`               |
| 立地適正化計画区域      | `XKT003`       | `location_normalization_plan_algorithm.py` |
| 自然公園地域            | `XKT019`       | `nature_reserve_algorithm.py`              |
| 高度利用地区            | `XKT024`       | `high_utilization_zone_algorithm.py`       |
| 人口集中地区            | `XKT031`       | `did_algorithm.py`                         |
| 市区町村一覧            | `XIT002`       | `area/area_algorithm.py`                   |

### ハザードマップポータルサイト

**実装**: `hazard_map_portal/`

| 機能                             | データ形式   | アルゴリズム                     |
| -------------------------------- | ------------ | -------------------------------- |
| 洪水浸水想定区域（想定最大規模） | ラスタタイル | `flood_hazard_area_algorithm.py` |

- タイル取得 URL: `https://disaportaldata.gsi.go.jp/raster/01_flood_l2_shinsuishin_data/{z}/{x}/{y}.png`
- 国土交通省ハザードマップポータルサイトが提供する洪水浸水想定区域（想定最大規模）のラスタタイルデータを表示

### 海しる API

**実装**: `umi_shiru/`

| 機能                   | エンドポイント                             | アルゴリズム                             |
| ---------------------- | ------------------------------------------ | ---------------------------------------- |
| 海岸線（ESI 区分付き） | `/coastline-type-ESI/v2/MapServer/1/query` | `coastline/coastline_algorithm.py`       |
| 漁港区域               | `/fishing-port-area/v2/MapServer/3/query`  | `fishing_port/fishing_port_algorithm.py` |
| 港湾区域               | `/port-area/v2/MapServer/3/query`          | `port_area/port_area_algorithm.py`       |

### e-Stat API

**実装**: `estat/population_mesh_algorithm.py`

- 人口メッシュ（500m / 1km メッシュ単位）

---

## 3. アーキテクチャ

本プラグインは、以下の階層化アーキテクチャ（Layered Architecture） に基づいて設計しています。

#### レイヤー構成

```
┌─────────────────────────────────────┐
│  UI Layer (ui/)                     │  ← ユーザーインタラクション
├─────────────────────────────────────┤
│  Workflow Layer (workflows/)        │  ← 処理フローの制御・調整
├─────────────────────────────────────┤
│  API Client Layer                   │  ← 外部APIとの通信
│  (umi_shiru/, real_estate_lib/)     │
├─────────────────────────────────────┤
│  Algorithm Layer (*_algorithm.py)   │  ← データ処理・レイヤー生成
├─────────────────────────────────────┤
│  Settings Layer (*_settings.py)     │  ← スタイル定義・設定管理
└─────────────────────────────────────┘
```

- **workflows/**: 各機能のエントリーポイント。UI からの要求を受け、複数のモジュールを協調させて処理を完遂
- **\*\_algorithm.py**: データ処理ロジックと QGIS レイヤー生成（ビジネスロジック層）
- **\*\_settings.py**: レイヤースタイル定義（スタイルルール、色、透明度など）
- **client.py / connect.py**: 外部 API 通信専用モジュール（エラーハンドリング、リトライ処理含む）

---

## 4. 主要なワークフロー

「海岸線」を例に挙げると、レイヤーがマップ上に表示されるまでの処理の流れは以下の通りです。

1. UI (dockwidget.py): ユーザーが実行ボタンをクリック。
2. 司令塔 (coastline_workflow.py): UI からリクエストを受け取り、必要なパラメータを準備。
3. API 接続 (UmiShiruApiClient): workflows からの指示で、海しる API にデータ取得リクエストを送信。
4. アルゴリズム (CoastlineAlgorithm): 取得した GeoJSON データを元に、QGIS レイヤーを作成し、スタイルを適用。
5. UI: 作成されたレイヤーを QGIS プロジェクトに追加し、ユーザーに表示。

---

## 5. 開発環境のセットアップ

### 前提条件：Git LFS のインストール

このプロジェクトは **Git LFS** を使用しています。クローン前にインストールしてください。

```
# インストール（macOS）
brew install git-lfs

# 初期化
git lfs install

# クローン後にインストールした場合LFS ファイルを手動で取得
git lfs pull
```

詳細は [Git LFS 公式サイト](https://git-lfs.github.com/) を参照してください。

開発には `uv`を使用した仮想環境の構築を推奨します。

### ステップ 1: 仮想環境の作成

QGIS にバンドルされている Python を指定して仮想環境を作成します。

```
# macOS の場合
uv venv --python /Applications/QGIS.app/Contents/MacOS/bin/python3 --system-site-packages

# Windows の場合（QGISのバージョン/パスに応じて要調整）
uv venv --python "C:\Program Files\QGIS 3.28.2\apps\Python39\python.exe" --system-site-packages
```

_`--system-site-packages`オプションにより、QGIS の PyQGIS ライブラリ等を引き継ぎます。_

### ステップ 2: 仮想環境の有効化

```
# macOS / Linux
source .venv/bin/activate

# Windows (Command Prompt)
.venv\Scripts\activate
```

### ステップ 3: 開発用ライブラリのインストール

型チェックやコード品質管理ツールをインストールします。

```
uv sync
```

### ステップ 4: VSCode の設定

- Python インタープリターとして、作成した仮想環境（例: `.venv/bin/python`）を選択してください。
- `ruff`による Lint/Format が自動で設定されます。

---

## 6. プロジェクト構造

ディレクトリ構成と各ファイルの役割を説明します。

```
tmu-planning-plugin/
├── green_infra_planner_jp.py       # プラグインのメインクラス（エントリーポイント）
├── metadata.txt                    # プラグインのメタデータ（名前、バージョンなど）
├── pyproject.toml                  # プロジェクト設定・依存関係管理（uv用）
│
├── ui/                             # ユーザーインターフェース
│   ├── dockwidget.py              # メインウィジェット（機能選択・実行ボタン）
│   ├── apikey_dialog.py           # APIキー設定ダイアログ
│   └── *.ui                       # Qt Designer UIファイル
│
├── features/                       # 機能モジュール
│   ├── basemap/                   # 国土地理院ベースマップ機能
│   │   ├── basemap_algorithm.py   # ベクトルタイルレイヤー生成
│   │   ├── basemap_settings.py    # スタイル設定
│   │   └── basemap_workflow.py    # ベースマップワークフロー
│   │
│   ├── administrative_area/       # 行政区域ポリゴン機能
│   │   ├── administrative_area_algorithm.py  # MBTilesレイヤー生成
│   │   ├── administrative_area_workflow.py    # 行政区域ワークフロー
│   │   ├── settings.py            # class3/class5スタイル定義
│   │   └── data/                  # ローカルデータ
│   │       └── class.mbtiles      # 行政区域MBTilesファイル
│   │
│   ├── hazard_map_portal/         # ハザードマップポータルサイト連携
│   │   ├── flood_hazard_area_algorithm.py  # 洪水浸水想定区域レイヤー生成
│   │   └── hazard_map_workflow.py          # ハザードマップワークフロー
│   │
│   ├── real_estate_lib/           # 不動産情報ライブラリAPI連携
│   │   ├── connect.py             # API接続・認証
│   │   ├── algorithms/            # 各種アルゴリズム
│   │   │   ├── urban_planning_algorithm.py
│   │   │   ├── zoning_district_algorithm.py
│   │   │   ├── district_plan_algorithm.py
│   │   │   ├── location_normalization_plan_algorithm.py
│   │   │   ├── nature_reserve_algorithm.py
│   │   │   ├── high_utilization_zone_algorithm.py
│   │   │   └── did_algorithm.py
│   │   └── workflows/             # ワークフロー
│   │       ├── area_workflow.py   # 行政区域取得
│   │       └── land_use_layer_workflow.py  # 土地利用レイヤー取得
│   │
│   ├── umi_shiru/                 # 海しるAPI連携
│   │   ├── client.py              # API接続・認証
│   │   └── workflows/
│   │       ├── coastline_workflow.py      # 海岸線データ処理
│   │       ├── fishing_port_workflow.py   # 漁港区域データ処理
│   │       └── port_area_workflow.py      # 港湾区域データ処理
│   │
│   └── estat/                     # e-Stat API連携
│       ├── connect.py             # 統計データ接続
│       └── population_mesh_workflow.py  # 人口メッシュ処理
│
├── utils/                          # 共通ユーティリティ
│   └── estat/                     # e-Stat関連ヘルパー
│
├── scripts/                        # 開発補助スクリプト
│   └── municipality_collector.py  # 市区町村データ収集ツール
│
├── tests/                          # ユニットテスト
│   ├── qgis_interface.py          # QGISインターフェースモック
│   └── test_*.py                  # 各機能のテスト
│
└── imgs/                           # 画像リソース
    └── icon.svg                   # プラグインアイコン
```

---

## 7. 外部 API エンドポイント

本プラグインが連携する主要な API エンドポイントです。

#### 不動産情報ライブラリ（MLIT Reinfolib）

- 都市計画区域 / 区域区分: `XKT001`
- 用途地域: `XKT002`
- 立地適正化計画区域: `XKT003`
- 自然公園地域: `XKT019`
- 高度利用地区: `XKT024`
- 地区計画: `XKT023`
- 人口集中地区: `XKT031`

#### ハザードマップポータルサイト

- 洪水浸水想定区域（想定最大規模）: `https://disaportaldata.gsi.go.jp/raster/01_flood_l2_shinsuishin_data/{z}/{x}/{y}.png`

#### 海しる API

- 海岸線: `/coastline-type-ESI/v2/MapServer/1/query`
- 漁港区域: `/fishing-port-area/v2/MapServer/3/query`
- 港湾区域: `/port-area/v2/MapServer/3/query`

#### e-Stat API

- 人口メッシュ

### API キーの取得方法

#### 不動産情報ライブラリ

1. [国土交通省 不動産情報ライブラリ](https://www.reinfolib.mlit.go.jp/)にアクセス
2. アカウント作成後、API 利用申請
3. 発行されたキーをプラグイン設定ダイアログに入力

#### 海しる API

1. [海しる 開発者向けサイト](https://www.msil.go.jp/)にアクセス
2. 利用規約を確認の上、API 利用申請
3. 発行されたキーをプラグイン設定ダイアログに入力

#### e-Stat API

1. [e-Stat API 登録ページ](https://www.e-stat.go.jp/api/)にアクセス
2. アカウント作成後、API 利用申請
3. 発行されたキーをプラグイン設定ダイアログに入力

#### ハザードマップポータルサイト

- API キー不要（公開ラスタタイル）

---

## 8. 開発ガイドライン

#### インポート

相対インポートを使用してください。

```python
# ✅ 推奨
from .utils import DataLoader
from ..umi_shiru.client import UmiShiruApiClient

# ❌ 非推奨
from green_infra_planner_jp.utils import DataLoader
```

#### 型ヒントとドキュメント

可能な限り型アノテーションと docstring（Google スタイル）を記述してください。

```python
from typing import Optional

def fetch_data(url: str, timeout: int = 10) -> dict:
    """指定したURLからデータを取得します。

    Args:
        url (str): データ取得先のURL
        timeout (int, optional): タイムアウト秒数。デフォルトは10

    Returns:
        dict: 取得したデータ

    Raises:
        ValueError: URLが無効な場合
    """
    ...

def get_municipality_code(name: str) -> Optional[str]:
    """市区町村名からコードを取得します。

    Args:
        name (str): 市区町村名

    Returns:
        Optional[str]: 市区町村コード（見つからない場合はNone）
    """
    ...
```

#### コード品質

`ruff` を使用してコードの品質を保ってください。

```bash
# リント実行
ruff check .

# 自動フォーマット
ruff format .
```
