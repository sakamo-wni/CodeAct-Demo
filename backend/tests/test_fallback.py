# backend/tests/test_fallback.py
from app.agent.flow import graph
from pathlib import Path

RU_SAMPLE = Path(__file__).parent / "data" / "sample.ru"

def test_fallback_parquet(tmp_path):
    """
    parquet 変換要求 → convert_node が UnsupportedFormatError を raise
    → fallback_node が Code Act で parquet を生成する
    """
    res = graph.invoke(
        {
            "input": f"この RU を parquet に変換してください: {RU_SAMPLE}",
            "task_id": "test-task-123",
            "format": "parquet",
            "ru_files": [str(RU_SAMPLE)],
        }
    )
    assert any(p.endswith(".parquet") for p in res.get("files", []))
