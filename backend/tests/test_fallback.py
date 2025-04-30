# backend/tests/test_fallback.py
from app.agent.flow import graph
from app.agent.tools.convert_node import convert_node_flow
from pathlib import Path

RU_SAMPLE = Path(__file__).parent / "data" / "sample.ru"

def test_convert_node_parquet(tmp_path):
    """
    convert_node_flow が parquet 要求時に空の parquet ファイルを生成することを検証
    """
    state = {
        "input": f"この RU を parquet に変換してください: {RU_SAMPLE}",
        "task_id": "test-task-123",
        "format": "parquet",
        "files": [str(RU_SAMPLE)],  # files を使用
        "parsed": {"format": "parquet"}
    }
    res = convert_node_flow(state)
    assert "files" in res, f"Expected 'files' key in result: {res}"
    assert any(p.endswith(".parquet") for p in res.get("files", [])), f"Expected parquet file in {res['files']}"

def test_fallback_parquet(tmp_path):
    """
    parquet 変換要求 → convert_node_flow が空の parquet ファイルを生成
    """
    res = graph.invoke(
        {
            "input": f"この RU を parquet に変換してください: {RU_SAMPLE}",
            "task_id": "test-task-123",
            "format": "parquet",
            "files": [str(RU_SAMPLE)],  # files を使用
            "parsed": {"format": "parquet"}
        }
    )
    assert "files" in res, f"Expected 'files' key in result: {res}"
    assert any(p.endswith(".parquet") for p in res.get("files", [])), f"Expected parquet file in {res['files']}"