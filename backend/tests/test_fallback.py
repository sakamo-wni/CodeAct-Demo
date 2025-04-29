# backend/tests/test_fallback.py
from app.utils.ru_utils import load_ru
from langgraph.runner import run  # 仮、実際は flow 呼び出し

def test_fallback_parquet(tmp_path):
    from app.agent.flow import graph
    ru_file = "backend/tests/data/sample.ru"
    out = run(graph, {"input": f"parquet に変換して {ru_file}"})
    assert any(p.endswith(".parquet") for p in out["files"])
