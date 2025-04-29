"""
RU → pandas.DataFrame 変換 & 変数名マッピングユーティリティ
"""
from __future__ import annotations

import json, uuid, re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd
from fuzzywuzzy import process

from app.agent.tools.ru_parser import parse_ru_file            # 既存
from app.agent.tools.s3_fetcher import download_location_json  # ★ 追加ヘルパ

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
VARS_PATH = BASE_DIR / "app" / "data" / "variables_map.json"
META_PATH = BASE_DIR / "app" / "data" / "metadata.json"

# ---------------- 変数コード <-> 一般名 ---------------------------
with open(VARS_PATH, encoding="utf-8") as f:
    _VAR_MAP: Dict[str, Dict[str, str]] = json.load(f)

_CODE2NAME = {c: (_VAR_MAP[c]["jp"], _VAR_MAP[c]["en"]) for c in _VAR_MAP}
_NAME2CODE = {
    name: code
    for code, (jp, en) in _CODE2NAME.items()
    for name in (code, jp, en)
}

def resolve_variable(query: str) -> str:
    if query in _NAME2CODE:
        return _NAME2CODE[query]
    candidate, score = process.extractOne(query, _NAME2CODE.keys())
    if score >= 90:
        return _NAME2CODE[candidate]
    raise KeyError(f"変数名を特定できません: {query}")

# ---------------- RU → DataFrame ---------------------------------
def ru_to_df(path: str | Path) -> pd.DataFrame:
    parsed = parse_ru_file(str(path))
    rows = parsed["data"]["point_data"]
    df = pd.json_normalize(rows)

    # ── ヘッダー部の announced（観測時刻）を列として付与 ──
    announced = parsed["header"].get("announced")  # 例: "2025/04/20 00:05:44 GMT"
    if announced and "announced" not in df.columns:
        df.insert(0, "announced", announced)       # 先頭列に追加

    return df

# =================================================================
# lat/lon 補完  ★ 本実装
# =================================================================
def _tagid_to_latlon(tag_id: str) -> Optional[Tuple[float, float]]:
    """
    TagID → metadata.json → location_metadata(bucket/prefix) →
    location JSON を取得し lat/lon を返す。
    ローカル app/data/{prefix}.json があればそれを優先、
    無ければ S3 からダウンロード（download_location_json）。
    """
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    rec = next((m for m in meta if m["TagID"] == tag_id), None)
    if not rec:
        return None

    loc = rec["location_metadata"]           # {"bucket":..., "prefix":..., "format":"json"}
    key = f"{loc['prefix'].rstrip('/')}/location.json"

    # 1) ローカルに置いてある場合
    local = BASE_DIR / "app" / "data" / key
    if local.exists():
        j = json.loads(local.read_text(encoding="utf-8"))
        return j.get("lat"), j.get("lon")

    # 2) S3 から取得
    try:
        j = download_location_json(loc["bucket"], key)
        return j.get("lat"), j.get("lon")
    except Exception:
        return None

def ensure_latlon(df: pd.DataFrame, tag_id: str | None = None) -> pd.DataFrame:
    """
    1) DataFrame に lat/lon 列があればそのまま
    2) TagID が与えられていれば location_metadata JSON から補完
    3) どちらも無理なら ValueError
    """
    if {"lat", "lon"}.issubset(df.columns):
        return df

    # 別名 (latitude/longitude) があれば rename
    lat_col = next((c for c in df.columns if c.lower() in {"latitude", "lat"}), None)
    lon_col = next((c for c in df.columns if c.lower() in {"longitude", "lon"}), None)
    if lat_col and lon_col:
        return df.rename(columns={lat_col: "lat", lon_col: "lon"})

    # TagID 由来で補完
    if tag_id:
        ll = _tagid_to_latlon(tag_id)
        if ll:
            lat, lon = ll
            new_df = df.copy()
            new_df["lat"] = lat
            new_df["lon"] = lon
            return new_df

    raise ValueError("緯度経度を補完できません")

# ------------------------------------------------------------------
# ユーザ指定変数だけを抽出するヘルパ
# ------------------------------------------------------------------
def extract_columns(df: pd.DataFrame, vars_: list[str]) -> pd.DataFrame:
    """
    ユーザー入力（日本語 / 英語 / コード）のリストを
    すべて RU 変数コードへ解決し、該当列だけ抽出して返す。
    存在しない列があれば KeyError。
    """
    codes = [resolve_variable(v) for v in vars_]
    missing = [c for c in codes if c not in df.columns]
    if missing:
        raise KeyError(f"DataFrame に列がありません: {missing}")
    return df[codes]
