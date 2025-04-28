from pathlib import Path
from app.utils.ru_utils import ru_to_df, resolve_variable

SAMPLE = Path(__file__).parent / "data" / "sample.ru"

def test_ru_to_df():
    df = ru_to_df(SAMPLE)
    assert not df.empty
    assert "AIRTMP" in df.columns

def test_resolve_variable():
    assert resolve_variable("気温") == "AIRTMP"
    assert resolve_variable("air temperature") == "AIRTMP"
    assert resolve_variable("AIRTMP") == "AIRTMP"
