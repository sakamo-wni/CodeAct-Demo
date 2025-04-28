from pathlib import Path
import pandas as pd
from app.agent.tools.convert_node import convert_node

# サンプル RU
SAMPLE = Path(__file__).parent / "data" / "sample.ru"

# --------------------------------------------------
# 1) CSV が生成されるか
# --------------------------------------------------
def test_convert_csv(tmp_path):
    out_files = convert_node.func([str(SAMPLE)], "csv")
    assert out_files and out_files[0].endswith(".csv")
    assert Path(out_files[0]).exists()

# --------------------------------------------------
# 2) JSON が生成されるか
# --------------------------------------------------
def test_convert_json(tmp_path):
    out_files = convert_node.func([str(SAMPLE)], "json")
    assert out_files and out_files[0].endswith(".json")
    assert Path(out_files[0]).exists()

# --------------------------------------------------
# 3) CSV の内容が壊れていないか（行数>0 & AIRTMP 列）
# --------------------------------------------------
def test_convert_csv_content():
    out_file = convert_node.func([str(SAMPLE)], "csv")[0]
    df = pd.read_csv(out_file)

    # 行数が 0 ではない
    assert len(df) > 0

    # AIRTMP 列（気温コード）が存在する
    assert "AIRTMP" in df.columns
