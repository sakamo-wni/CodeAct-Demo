import os
from pathlib import Path
import pandas as pd
import pytest
import shutil
from app.agent.tools.fallback_node import fallback_node, USE_CODEACT

SAMPLE_RU = Path(__file__).parent / "data/sample.ru"
LOCATION_JS = Path(__file__).parent / "data/441000205/location.json"

@pytest.fixture(scope="module")
def parsed_dataframe():
    """Parse sample.ru with location.json once for all tests."""
    from app.agent.tools.ru_parser import RUParser
    df = RUParser(SAMPLE_RU.read_bytes(), LOCATION_JS).to_dataframe()
    # LCLIDを文字列に変換し、ゼロパディングを保証
    df["LCLID"] = df["LCLID"].astype(str).str.zfill(5)
    print(f"[DEBUG] Original DataFrame dtypes:\n{df.dtypes}")
    print(f"[DEBUG] Original DataFrame head:\n{df.head()}")
    return df

def test_codeact_e2e_csv(tmp_path, monkeypatch, parsed_dataframe):
    """Test CodeAct for CSV format."""
    if not USE_CODEACT:
        pytest.skip("CodeAct is disabled; set CODEACT_DISABLED=0 to enable")

    monkeypatch.setenv("TMPDIR", str(tmp_path))
    df = parsed_dataframe

    ctx = {
        "format": "csv",
        "task_id": "e2e-test-csv",
        "df": df,
        "use_patch": False
    }

    result = None
    try:
        result = fallback_node(ctx)
        print(f"[DEBUG] Fallback node result (csv): {result}")

        if "error" in result:
            pytest.fail(f"CodeAct failed for csv: {result['error']}")

        assert not any("codeact_quick_" in f for f in result["files"]), "Fallback path used for csv"
        assert "files" in result, "Missing 'files' key for csv"
        assert result["used_codeact"], "CodeAct not used for csv"
        out_file = Path(result["files"][0])
        assert out_file.exists() and out_file.suffix == ".csv", f"CSV not generated: {out_file}"
        assert out_file.name == "output.csv", f"Wrong file name for csv: {out_file.name}"

        # 元のDataFrameのデータ型を保持して読み込み
        dtypes = df.dtypes.to_dict()
        dtypes["LCLID"] = str  # LCLIDは文字列
        df_from_file = pd.read_csv(out_file, dtype=dtypes)
        print(f"[DEBUG] Generated CSV dtypes:\n{df_from_file.dtypes}")
        print(f"[DEBUG] Generated CSV head:\n{df_from_file.head()}")
        pd.testing.assert_frame_equal(df, df_from_file, check_like=True)

    except Exception as exc:
        print(f"[DEBUG] Test failed for csv: {exc}")
        raise
    finally:
        if result and "error" in result:
            print(f"[DEBUG] Preserving workdir for inspection (csv): {tmp_path}")

def test_codeact_e2e_json(tmp_path, monkeypatch, parsed_dataframe):
    """Test CodeAct for JSON format."""
    if not USE_CODEACT:
        pytest.skip("CodeAct is disabled; set CODEACT_DISABLED=0 to enable")

    monkeypatch.setenv("TMPDIR", str(tmp_path))
    df = parsed_dataframe

    ctx = {
        "format": "json",
        "task_id": "e2e-test-json",
        "df": df,
        "use_patch": False
    }

    result = None
    try:
        result = fallback_node(ctx)
        print(f"[DEBUG] Fallback node result (json): {result}")

        if "error" in result:
            pytest.fail(f"CodeAct failed for json: {result['error']}")

        assert not any("codeact_quick_" in f for f in result["files"]), "Fallback path used for json"
        assert "files" in result, "Missing 'files' key for json"
        assert result["used_codeact"], "CodeAct not used for json"
        out_file = Path(result["files"][0])
        assert out_file.exists() and out_file.suffix == ".json", f"JSON not generated: {out_file}"
        assert out_file.name == "output.json", f"Wrong file name for json: {out_file.name}"

        # 元のDataFrameのデータ型を保持して読み込み
        dtypes = df.dtypes.to_dict()
        dtypes["LCLID"] = str  # LCLIDは文字列
        df_from_file = pd.read_json(out_file, orient="records", lines=True, dtype=dtypes)
        print(f"[DEBUG] Generated JSON dtypes:\n{df_from_file.dtypes}")
        print(f"[DEBUG] Generated JSON head:\n{df_from_file.head()}")
        pd.testing.assert_frame_equal(df, df_from_file, check_like=True)

    except Exception as exc:
        print(f"[DEBUG] Test failed for json: {exc}")
        raise
    finally:
        # テスト終了後にクリーンアップ
        if result and "files" in result and not ("error" in result):
            for file in result["files"]:
                workdir = Path(file).parent
                shutil.rmtree(workdir, ignore_errors=True)
        if result and "error" in result:
            print(f"[DEBUG] Preserving workdir for inspection (json): {tmp_path}")