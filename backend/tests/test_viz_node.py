# backend/tests/test_viz_node.py
import matplotlib
matplotlib.use("Agg")

from pathlib import Path
import pytest
from app.agent.tools.viz_node import viz_node

SAMPLE = Path(__file__).parent / "data" / "sample.ru"

# sample.ru に実在する時刻列（例: announced）を確認
# なければ observation time 等、実データに存在する列へ変更してください。
ANNOUNCED_COL = "announced"

# -------------------------------
# バーグラフ生成を検証（lat/lon不要）
# -------------------------------
def test_viz_bar():
    out = viz_node.func(
        [str(SAMPLE)],
        chart="bar",
        x=ANNOUNCED_COL,
        y="AIRTMP"
    )
    p = Path(out)
    assert p.exists() and p.stat().st_size > 0 and p.suffix == ".png"

# -------------------------------
# マップチャート生成を検証
# -------------------------------
def test_viz_map():
    # lat/lon が無いので ensure_latlon がそのまま ValueError を返す
    with pytest.raises(ValueError, match="緯度経度を補完できません"):
        viz_node.func(
            [str(SAMPLE)],
            chart="map",
            x=ANNOUNCED_COL,
            y="AIRTMP"
        )

def test_viz_map_with_loc(monkeypatch):
    from app.utils import ru_utils

    # テスト用地点 JSON を読み取って lat/lon を返す関数に差し替え
    def _latlon_from_testfile(tid: str):
        import re
        from pathlib import Path
        loc_path = Path(__file__).parent / f"{tid}" / "location.json"
        text = loc_path.read_text(encoding="utf-8", errors="ignore")

        # lon, lat が順に並ぶ最初の coordinates を捕捉
        m = re.search(r'coordinates"\s*:\s*\[\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)', text)
        if not m:
            raise ValueError("lat/lon を抽出できません")
        lon, lat = map(float, m.groups())
        return lat, lon

    monkeypatch.setattr(ru_utils, "_tagid_to_latlon", _latlon_from_testfile)

    out = viz_node.func([str(SAMPLE)], "map", tag_id="441000205")
    assert Path(out).exists() and Path(out).stat().st_size > 0
