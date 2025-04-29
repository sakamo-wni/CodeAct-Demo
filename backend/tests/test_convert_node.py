# backend/tests/test_convert_node.py
#
# 変換ノードのユニットテスト
#  - CSV / JSON が正しく生成されるか
#  - 生成された CSV の内容が壊れていないか
# ---------------------------------------------------------------------

# GUI バックエンドを使わないよう固定
import matplotlib
matplotlib.use("Agg")

from pathlib import Path
import pandas as pd
from app.agent.tools.convert_node import convert_node

# サンプル RU
SAMPLE = Path(__file__).parent / "data" / "sample.ru"

# --------------------------------------------------
# 1) CSV が生成されるか
# --------------------------------------------------
def test_convert_csv():
    out_files = convert_node.func([str(SAMPLE)], "csv")
    assert out_files and out_files[0].endswith(".csv")

    p = Path(out_files[0])
    assert p.exists() and p.stat().st_size > 0

# --------------------------------------------------
# 2) JSON が生成されるか
# --------------------------------------------------
def test_convert_json():
    out_files = convert_node.func([str(SAMPLE)], "json")
    assert out_files and out_files[0].endswith(".json")

    p = Path(out_files[0])
    assert p.exists() and p.stat().st_size > 0

# --------------------------------------------------
# 3) CSV の内容検証（行数>0 & AIRTMP 列）
# --------------------------------------------------
def test_convert_csv_content():
    csv_path = convert_node.func([str(SAMPLE)], "csv")[0]
    df = pd.read_csv(csv_path)

    # 行数が 0 ではない
    assert len(df) > 0

    # AIRTMP 列（気温コード）が存在する
    assert "AIRTMP" in df.columns
