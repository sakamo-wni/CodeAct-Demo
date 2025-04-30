import os
from pathlib import Path
import pandas as pd
import pytest
import shutil
from app.agent.tools.fallback_node import fallback_node, USE_CODEACT

SAMPLE_RU = Path(__file__).parent / "data/sample.ru"
LOCATION_JS = Path(__file__).parent / "data/441000205/location.json"

def test_codeact_e2e(tmp_path, monkeypatch):
    if not USE_CODEACT:
        pytest.skip("CodeAct is disabled; set CODEACT_DISABLED=0 to enable")

    monkeypatch.setenv("TMPDIR", str(tmp_path))

    from app.agent.tools.ru_parser import RUParser
    df = RUParser(SAMPLE_RU.read_bytes(), LOCATION_JS).to_dataframe()
    print(f"[DEBUG] Original DataFrame dtypes:\n{df.dtypes}")
    print(f"[DEBUG] Original DataFrame head:\n{df.head()}")

    ctx = {
        "format": "csv",
        "task_id": "e2e-test",
        "df": df,
        "use_patch": False
    }

    result = None
    try:
        result = fallback_node(ctx)
        print(f"[DEBUG] Fallback node result: {result}")

        if "error" in result:
            pytest.fail(f"CodeAct failed: {result['error']}")

        assert not any("codeact_quick_" in f for f in result["files"]), "Fallback path used"
        assert "files" in result, "Missing 'files' key"
        assert result["used_codeact"], "CodeAct not used"
        out_csv = Path(result["files"][0])
        assert out_csv.exists() and out_csv.suffix == ".csv", f"CSV not generated: {out_csv}"
        assert out_csv.name == "output.csv", f"Wrong CSV name: {out_csv.name}"

        df_from_csv = pd.read_csv(out_csv, dtype=str)
        print(f"[DEBUG] Generated CSV dtypes:\n{df_from_csv.dtypes}")
        print(f"[DEBUG] Generated CSV head:\n{df_from_csv.head()}")
        pd.testing.assert_frame_equal(df.astype(str), df_from_csv, check_like=True)

    finally:
        if result and "files" in result and not ("error" in result):
            for file in result["files"]:
                workdir = Path(file).parent
                shutil.rmtree(workdir, ignore_errors=True)
        else:
            print(f"[DEBUG] Preserving workdir for inspection: {tmp_path}")