# backend/tests/test_ru_utils.py
import pandas as pd
import pytest
from app.utils.ru_utils import load_ru, load_geojson

def test_load_geojson(sample_geojson):
    geojson = load_geojson("441000205")
    assert isinstance(geojson, dict)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) > 0
    assert "coordinates" in geojson["features"][0]["geometry"]

def test_load_gzip_obs(sample_obs_ru):
    df = load_ru(sample_obs_ru)
    # 時刻＋代表的な変数列
    assert {"time", "AIRTMP", "WNDSPD_MD"}.issubset(df.columns)
    # スケール適用後、気温が plausible 範囲にあること
    assert df["AIRTMP"].dropna().between(-50, 60).all()