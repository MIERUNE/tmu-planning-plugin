"""
現存植生図2024（環境ジオポータル）の設定情報
"""

# レイヤー名の接頭辞
LAYER_NAME_PREFIX = "現存植生図2024"

# 市区町村bboxに付与するバッファ（約1km）
BBOX_BUFFER_DEGREES = 0.01

# QMLが分類に使用するフィールド名
FIELD_LEGEND_CODE = "凡例コード"

# 都道府県コード(2桁) → 地域ブロック
# 山梨・長野は中部、新潟・福井は北陸、三重は近畿（FeatureServerへの点クエリで確認済み）
PREFECTURE_BLOCK_MAP = {
    "01": "hokkaido",
    "02": "tohoku",
    "03": "tohoku",
    "04": "tohoku",
    "05": "tohoku",
    "06": "tohoku",
    "07": "tohoku",
    "08": "kanto",
    "09": "kanto",
    "10": "kanto",
    "11": "kanto",
    "12": "kanto",
    "13": "kanto",
    "14": "kanto",
    "15": "hokuriku",
    "16": "hokuriku",
    "17": "hokuriku",
    "18": "hokuriku",
    "19": "chubu",
    "20": "chubu",
    "21": "chubu",
    "22": "chubu",
    "23": "chubu",
    "24": "kinki",
    "25": "kinki",
    "26": "kinki",
    "27": "kinki",
    "28": "kinki",
    "29": "kinki",
    "30": "kinki",
    "31": "chushikoku",
    "32": "chushikoku",
    "33": "chushikoku",
    "34": "chushikoku",
    "35": "chushikoku",
    "36": "chushikoku",
    "37": "chushikoku",
    "38": "chushikoku",
    "39": "chushikoku",
    "40": "kyushu_okinawa",
    "41": "kyushu_okinawa",
    "42": "kyushu_okinawa",
    "43": "kyushu_okinawa",
    "44": "kyushu_okinawa",
    "45": "kyushu_okinawa",
    "46": "kyushu_okinawa",
    "47": "kyushu_okinawa",
}

# 地域ブロックの表示名
BLOCK_NAMES = {
    "hokkaido": "北海道",
    "tohoku": "東北",
    "kanto": "関東",
    "hokuriku": "北陸",
    "chubu": "中部",
    "kinki": "近畿",
    "chushikoku": "中四国",
    "kyushu_okinawa": "九州沖縄",
}
