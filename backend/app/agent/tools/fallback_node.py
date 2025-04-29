# backend/app/agent/tools/fallback_node.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
import uuid

# -------------------- CodeAct import ---------------------------
# langgraph-codeact >=0.2
try:
    from langgraph_codeact import CodeAct
except ImportError:  # テスト環境でモックに置き換えるためのフォールバック
    class CodeAct:  # type: ignore
        def __init__(self, model: str): ...
        def generate_code(self, prompt: str) -> str:
            # ダミーコードを返して sandbox 実行が通るように
            return "print('dummy CodeAct execution')"

from langgraph import tool

from app.codeact_sandbox import run_code_act

# ────────────────────────────────────────────────────────────
@tool("code_act_fallback")
def fallback_node(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph ノードの未対応例外を受け取り、Claude(CodeAct) で動的コード生成→実行。
    Returns
    -------
    {
      "files": ["/tmp/codeact/<uuid>/output.*"],
      "code" : "<generated python code>"
    }
    """
    task_id = context.get("task_id", str(uuid.uuid4()))
    prompt = _build_prompt(context, task_id)

    # Claude 3 Sonnet でコード生成
    executor = CodeAct(model="claude-3-sonnet-20240229")  # Bedrock 経由
    generated_code = executor.generate_code(prompt)

    # サンドボックス内で実行
    result_dir = run_code_act(generated_code, context)

    # 生成物を列挙
    files: List[str] = [str(p) for p in Path(result_dir).iterdir()]
    return {"files": files, "code": generated_code}


# ────────────────────────────────────────────────────────────
def _build_prompt(ctx: Dict[str, Any], task_id: str) -> str:
    """
    CodeAct 用プロンプト文字列を生成
    """
    df_hint = "The variable `df` already exists and contains the loaded RU data."
    if ctx.get("format"):
        return (
            f"{df_hint}\n"
            f"Convert `df` into {ctx['format']} and save to "
            f"`/tmp/codeact/{task_id}/output.{ctx['format']}`"
        )
    if ctx.get("chart"):
        return (
            f"{df_hint}\n"
            f"Draw a {ctx['chart']} chart with matplotlib/seaborn. "
            f"Save the image to `/tmp/codeact/{task_id}/output.png`"
        )
    # フォールバックの最後の砦
    return f"{df_hint}\nPrint df.head() and save CSV to `/tmp/codeact/{task_id}/output.csv`"
