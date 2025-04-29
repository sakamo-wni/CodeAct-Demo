# app/agent/tools/viz_node.py
from __future__ import annotations
import re, uuid
from pathlib import Path
from typing import List, Optional

import pandas as pd
import matplotlib
matplotlib.use("Agg")           # ヘッドレス環境用
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from langchain.tools import tool

from app.utils.ru_utils import (
    load_ru,
    ensure_latlon,
    extract_columns,
    resolve_variable,
)

# --------------------------------------------------------------------
_TMP = Path("tmp")
_TMP.mkdir(exist_ok=True)

def _png_path() -> Path:
    return _TMP / f"{pd.Timestamp.utcnow():%Y%m%d-%H%M%S}-{uuid.uuid4().hex}.png"

def _save(fig) -> str:
    path = _png_path()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return str(path)

def _guess_tag_id(path: str) -> Optional[str]:
    m = re.search(r"\b(\d{9})\b", path)
    return m.group(1) if m else None
# --------------------------------------------------------------------


@tool("viz_ru")
def viz_node(
    ru_files: List[str],
    chart: str,
    tag_id: str | None = None,
    variables: List[str] | None = None,
    x: str | None = None,
    y: str | None = None,
) -> str:
    """
    RU ファイル群を可視化し PNG ファイルパスを返す。

    Args
    ----
    ru_files  : 取得済み RU ファイルのローカルパス（複数可）
    chart     : "scatter" | "bar" | "map"
    tag_id    : タグID（任意）
    variables : 可視化に使う気象変数コード／日本語／英語（任意）
    x, y      : 軸に使う列名（scatter / bar 用）
    """
    # ------ 1. RU → DataFrame --------------------------------------
    df = pd.concat([load_ru(p) for p in ru_files], ignore_index=True)

    # ------ 2. 変数名をコードに正規化 --------------------------------
    def _resolve(name: str | None) -> str | None:
        if not name:
            return None
        if name in df.columns:
            return name
        try:
            return resolve_variable(name)
        except Exception:
            return name  # そのまま返して存在確認へ

    x = _resolve(x)
    y = _resolve(y)
    variables = [_resolve(v) for v in variables] if variables else None

    # ------ 3. 変数列抽出（lat/lon 不要のグラフの場合に限定） ---------
    if variables:
        df = extract_columns(df, variables)

    # ------ 4. map: lat/lon を必須とし、無ければ明示エラー ----------
    if chart == "map":
        df = ensure_latlon(df, tag_id or _guess_tag_id(ru_files[0]))
        fig = plt.figure()
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.coastlines()
        ax.scatter(df["lon"], df["lat"], s=10, transform=ccrs.PlateCarree())
        return _save(fig)

    # ------ 5. scatter & bar: 指定列が無ければ即エラー ---------------
    for col, label in [(x, "x"), (y, "y")]:
        if col and col not in df.columns:
            raise ValueError(f"列が見つかりません: {label}='{col}'")

    if chart == "scatter":
        fig, ax = plt.subplots()
        ax.scatter(df[x], df[y], s=10)
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        return _save(fig)

    if chart == "bar":
        fig, ax = plt.subplots()
        ax.bar(df[x], df[y])
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        return _save(fig)

    raise ValueError(f"未知の chart 種: {chart}")
