import pandas as pd
import pytest
from app.utils.ru_utils import load_ru

@pytest.mark.skip(reason="地点メタは RU ではなく location.json で扱うためスキップ")
def test_load_geojson():
    pass

def test_load_gzip_obs(sample_obs_ru):
    df = load_ru(sample_obs_ru)
    # 時刻＋代表的な変数列
    assert {"time", "AIRTMP", "WNDSPD_MD"}.issubset(df.columns)
    # スケール適用後、気温が plausible 範囲にあること
    assert df["AIRTMP"].dropna().between(-50, 60).all()
