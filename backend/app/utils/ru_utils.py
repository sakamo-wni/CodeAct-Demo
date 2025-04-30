# backend/app/utils/ru_utils.py
"""
ru_utils.py – RU ファイル（GeoJSON / gzip 観測）→ pandas.DataFrame
・フォーマット自動判定
    - header.format == "GJSON"           → GeoJSON 地点メタ
    - header.compress_type == "gzip"     → 観測データ (KNMI_OBS_SYNOP_raw など)
・観測データは RU.py を利用し、variables_map.json のスケール / offset を適用
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List

import json
import gzip
import io
import pandas as pd
import numbers
import numpy as np
import boto3
import logging

from app.agent.tools.RU import RU, Header  # RU.py を tools 配下へ移動済み前提

# ロギング設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# AWS設定
AWS_DEFAULT_REGION = "ap-northeast-1"
S3_BUCKET = "wni-wfc-stock-ane1"  # 実際のバケット名
CLIENT_KWARGS = {}  # 必要に応じて認証情報などを設定

# 「…/backend/app/utils/ru_utils.py」から見て 3 つ親 = backend/
BACKEND_ROOT = Path(__file__).resolve().parents[2]   # /code/backend

# 変数メタ
VARIABLES_MAP: Dict[str, Dict] = json.loads(
    (BACKEND_ROOT / "app" / "data" / "variables_map.json").read_text(encoding="utf-8")
)

__all__ = ["load_ru", "ensure_latlon", "extract_columns", "resolve_variable", "load_geojson"]

# ----------------------------------------------------------------------
def _load_geojson(body: bytes) -> pd.DataFrame:
    """GeoJSON → DataFrame"""
    gjson = json.loads(body.decode("utf-8"))
    rows: List[Dict] = []
    for feat in gjson["features"]:
        lon, lat, *alt = feat["geometry"]["coordinates"]
        props = feat["properties"]
        rows.append(
            {
                **props,
                "lat": lat,
                "lon": lon,
                "alt": alt[0] if alt else None,
            }
        )
    return pd.DataFrame(rows)


def _load_gzip_observation(ru_bytes: bytes) -> pd.DataFrame:
    """gzip 観測 RU → DataFrame"""
    fp = io.BytesIO(ru_bytes)
    ru = RU()
    ru.load(fp)  # ヘッダ検出 → gzip 展開 → 構造化

    hdr: Header = ru.get_header()
    root = ru.get_root()

    # --- 観測レコードへ変換 -------------------------------------------
    # 仕様: root 構造体 直下に 'observation_date' Struct + 'point_data' Array[]
    recs: List[Dict] = []
    obs_time_struct = root.get_ref("observation_date")
    dt = obs_time_struct.get_time().replace(tzinfo=None)  # naive UTC
    pt_arr = root.get_ref("point_data")

    for pt in pt_arr:
        rec: Dict = {
            "time": dt,
            # announced (header) を各レコードに付与 ---------------
            "announced": pd.to_datetime(hdr["announced"], utc=True)
            if "announced" in hdr
            else dt,
        }
        for key in pt.keys():
            v = pt[key]

            if isinstance(v, numbers.Number):
                # ---------- 欠測コード判定 ----------
                if abs(v) >= 32000:           # 32000 系は欠測
                    rec[key] = np.nan
                    continue

                # ---------- スケール補正 ----------
                meta = VARIABLES_MAP.get(key, {})
                scale  = float(meta.get("scale", 1))
                offset = float(meta.get("offset", 0))
                val = v * scale + offset      # 例: 327 → 32.7

                # ---------- 気温の物理範囲チェック ----------
                if key == "AIRTMP" and not (-80 <= val <= 70):
                    rec[key] = np.nan          # 異常値も欠測扱い
                else:
                    rec[key] = round(val, 3)
            else:
                # 文字列・欠損はそのまま
                rec[key] = v

        recs.append(rec)

    df = pd.DataFrame(recs)
    # announced を naive UTC に統一
    if "announced" in df.columns:
        df["announced"] = pd.to_datetime(df["announced"], utc=True).dt.tz_localize(None)

    # --- 欠測行を除外 -------------------------------------------
    numeric_cols = [c for c in df.columns if df[c].dtype.kind in "fiu"]
    df = df.dropna(subset=numeric_cols, how="all")  # 全数値列が NaN の行だけ除去

    return df


# ----------------------------------------------------------------------
def load_ru(path: str | Path) -> pd.DataFrame:
    """
    RU ファイルを DataFrame にロード（フォーマット自動判定）
    """
    data = Path(path).read_bytes()

    # 1) ヘッダ抽出
    if not data.startswith(b"WN\n"):
        raise ValueError("Not an RU file")

    # header_end = b"\x04\x1a" の直前までがヘッダ
    end_idx = data.find(b"\x04\x1a")
    if end_idx == -1:
        raise ValueError("invalid RU header")
    header_part = data[: end_idx + 2].decode("ascii", errors="replace")

    # compress_type 判定
    compress = None
    for line in header_part.splitlines():
        if line.startswith("compress_type="):
            compress = line.split("=", 1)[1]
            break
    hdr_format = None
    for line in header_part.splitlines():
        if line.startswith("format="):
            hdr_format = line.split("=", 1)[1]
            break

    body = data[end_idx + 2 :]

    if hdr_format == "GJSON":
        return _load_geojson(body)
    elif compress == "gzip":
        return _load_gzip_observation(data)
    else:
        raise NotImplementedError(f"unsupported RU format: {hdr_format}, compress={compress}")


def _tagid_to_latlon(tag_id: str) -> tuple[float, float]:
    """
    tag_idから緯度経度を取得する関数
    テストではmonkeypatchで差し替える想定
    """
    from app.utils.country_resolver import find_metadata_by_tag
    meta = find_metadata_by_tag(tag_id)
    loc_df = load_ru(meta["location_metadata"]["local_path"])
    return loc_df["lat"].mean(), loc_df["lon"].mean()


def ensure_latlon(df: pd.DataFrame, tag_id: str | None = None) -> pd.DataFrame:
    """
    lat/lon が無ければ metadata.json から該当地点情報を読み込んで補完
    （flow 内から既存の ensure_latlon 呼び出しに合わせる）
    """
    if {"lat", "lon"} <= set(df.columns):
        return df

    if not tag_id:
        raise ValueError("緯度経度を補完できません")

    # テストでは monkeypatch で差し替える
    lat, lon = _tagid_to_latlon(tag_id)
    return df.assign(lat=lat, lon=lon)


def extract_columns(df: pd.DataFrame, names):
    """
    names に含まれる列だけ返す。列が無ければ KeyError
    (viz_node 互換の軽量ユーティリティ)
    """
    if isinstance(names, str):
        names = [names]

    missing = [col for col in names if col not in df.columns]
    if missing:
        raise KeyError(f"columns not found: {missing}")

    return df[names]


def resolve_variable(alias: str) -> str:
    """
    入力 alias を variables_map.json から正規コードへ解決する簡易版
    - 完全一致 (大文字小文字区別なし)
    - jp/en 名称またはコードにヒットすればコードを返す
    - 見つからなければそのまま返却（viz_node 側で KeyError にさせる）
    """
    alias_norm = alias.lower()

    # 1) 変数コード完全一致
    if alias_norm in (k.lower() for k in VARIABLES_MAP.keys()):
        return next(k for k in VARIABLES_MAP if k.lower() == alias_norm)

    # 2) jp / en 名称一致
    for code, meta in VARIABLES_MAP.items():
        if alias_norm in (
            meta.get("jp", "").lower(),
            meta.get("en", "").lower(),
        ):
            return code

    # 3) 未解決ならそのまま
    return alias


def load_geojson(tag_id: str) -> dict:
    """
    tag_idに対応するGeoJSONデータを取得する関数
    テスト用ローカルファイルがあれば先に読み込む
    なければS3から取得
    """
    project_root = Path(__file__).parents[2]
    test_file = project_root / "tests" / "data" / tag_id / "location.json"
    if test_file.exists():
        logger.debug(f"Loading local GeoJSON: {test_file}")
        data = test_file.read_bytes()
        end_idx = data.find(b"\x04\x1a")
        if end_idx == -1:
            logger.error(f"Invalid RU header in {test_file}")
            raise ValueError("Invalid RU header")
        body = data[end_idx + 2 :]
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GeoJSON in {test_file}: {e}")
            raise ValueError(f"Failed to parse GeoJSON: {e}")
    
    logger.debug(f"Fetching GeoJSON from S3: {tag_id}/location.json")
    s3 = boto3.client("s3", region_name=AWS_DEFAULT_REGION, **CLIENT_KWARGS)
    key = f"{tag_id}/location.json"
    try:
        resp = s3.get_object(Bucket=S3_BUCKET, Key=key)
        data = resp["Body"].read()
        end_idx = data.find(b"\x04\x1a")
        if end_idx == -1:
            logger.error(f"Invalid RU header in S3 object: {key}")
            raise ValueError("Invalid RU header")
        body = data[end_idx + 2 :]
        return json.loads(body.decode("utf-8"))
    except s3.exceptions.NoSuchKey:
        logger.error(f"GeoJSON not found in S3: {key}")
        raise FileNotFoundError(f"GeoJSON not found: {key}")