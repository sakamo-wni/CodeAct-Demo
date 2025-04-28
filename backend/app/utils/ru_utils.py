"""
RU → pandas.DataFrame 変換 & 変数名マッピングユーティリティ
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from fuzzywuzzy import process

from app.agent.tools.ru_parser import parse_ru_file  # 既存パーサ
BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
VARS_PATH = BASE_DIR / "app" / "data" / "variables_map.json"

# ------------------------------
# 変数名マッピングテーブルをロード
# ------------------------------
with open(VARS_PATH, encoding="utf-8") as f:
    _VAR_MAP: Dict[str, Dict[str, str]] = json.load(f)

# コード ➜ 一般名（jp / en）・逆引き用 dict 生成
_CODE2NAME = {
    code: (_VAR_MAP[code]["jp"], _VAR_MAP[code]["en"]) for code in _VAR_MAP
}
_NAME2CODE = {
    name: code
    for code, (jp, en) in _CODE2NAME.items()
    for name in (code, jp, en)
}

def resolve_variable(query: str) -> str:
    """
    ユーザー入力（日本語 / 英語 / コード）を RU 変数コードへ正規化する。
    fuzzywuzzy で 90%以上一致した最上位を採用。
    """
    if query in _NAME2CODE:
        return _NAME2CODE[query]

    # あいまい検索
    candidate, score = process.extractOne(query, _NAME2CODE.keys())
    if score >= 90:
        return _NAME2CODE[candidate]

    raise KeyError(f"変数名を特定できません: {query}")

# ------------------------------
# RU → DataFrame
# ------------------------------
def ru_to_df(path: str | Path) -> pd.DataFrame:
    """
    RU ファイル1本 → DataFrame
    """
    parsed = parse_ru_file(str(path))
    rows = parsed["data"]["point_data"]
    return pd.json_normalize(rows)

# ------------------------------
# lat/lon 補完
# ------------------------------
def ensure_latlon(df: pd.DataFrame, tag_id: str | None = None) -> pd.DataFrame:
    """
    DataFrame に lat / lon 列が無ければ TagID の地点メタデータから補完する。
    """
    if {"lat", "lon"}.issubset(df.columns):
        return df

    # variables_map.json で同義語を探す
    alt_lat = next((c for c in df.columns if c.lower() in {"latitude", "lat"}), None)
    alt_lon = next((c for c in df.columns if c.lower() in {"longitude", "lon"}), None)

    if alt_lat and alt_lon:
        df = df.rename(columns={alt_lat: "lat", alt_lon: "lon"})
        return df

    # TagID から metadata.json を検索
    if tag_id:
        meta_path = BASE_DIR / "app" / "data" / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        rec = next((m for m in meta if m["TagID"] == tag_id), None)
        if rec:
            # location_metadata のファイル（JSON）をロード
            loc_file = (BASE_DIR / "tmp" /
                        f"{uuid.uuid4()}.loc.json")  # 一時保存
            # （本実装では S3 → tmp へ DL する）
            # ... 省略 ...
            loc_json = json.loads(loc_file.read_text())
            df["lat"] = loc_json["lat"]
            df["lon"] = loc_json["lon"]
            return df

    raise ValueError("緯度経度を補完できません")

# ------------------------------
# 変数抽出ユーティリティ
# ------------------------------
def extract_columns(df: pd.DataFrame, vars_: List[str]) -> pd.DataFrame:
    """
    ユーザー指定変数を DataFrame から抽出（自動コード解決付き）。
    """
    codes = [resolve_variable(v) for v in vars_]
    missing = [c for c in codes if c not in df.columns]
    if missing:
        raise KeyError(f"DataFrame に存在しない列: {missing}")
    return df[["time", "lat", "lon", *codes]]
