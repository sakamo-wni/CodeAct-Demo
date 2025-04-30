"""
fallback_node – CodeAct 0.1.3 対応版
───────────────────────────────────────────────────────────────
* CodeActContext が Pydantic-model で渡る場合でも format='csv' 等を
  正しく引き渡し、生成コードが output.csv / result.parquet を作成
* (code_str, {"result": {...}}) 形式の戻り値を許容
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from langchain_openai import ChatOpenAI
from app.config import settings
from langgraph.checkpoint.memory import MemorySaver
from langgraph_codeact import create_codeact

USE_CODEACT: bool = os.getenv("CODEACT_DISABLED", "0") != "1"
FALLBACK_ENABLED: bool = os.getenv("FALLBACK_ENABLED", "1") == "1"

__all__ = ["fallback_node", "USE_CODEACT"]

def save_df_to_csv(df: pd.DataFrame, path: str | Path) -> None:
    """Save **df** to *path* as CSV (quoted, no index)."""
    df.to_csv(path, index=False, quoting=csv.QUOTE_NONNUMERIC)

def _save_parquet(df: pd.DataFrame, out: Path) -> None:
    """Save **df** to *out* as Parquet using pyarrow."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    pq.write_table(pa.Table.from_pandas(df), out)

_LATEST_DF: pd.DataFrame | None = None

def _fallback_quick(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Always generate `output.csv` under a temp dir and return its path."""
    df: pd.DataFrame = ctx["df"]
    workdir = Path(tempfile.mkdtemp(prefix="codeact_quick_"))
    out = workdir / "output.csv"
    save_df_to_csv(df, out)
    return {"files": [str(out)], "used_codeact": False}

if USE_CODEACT:
    openai_model = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.codeact_model.split(":", 1)[-1],  # "gpt-4o"
    )

    TMPDIR = Path(tempfile.gettempdir()) / "codeact_unit"
    TMPDIR.mkdir(exist_ok=True)

    def _make_eval_fn(workdir: Path, ctx_format: str):
        """Return an eval_fn that writes + executes generated code, using ctx['format']."""
        def eval_code(code: str, context: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
            global _LATEST_DF
            outfile = workdir / "generated.py"
            outfile.write_text(code, encoding="utf-8")
            exec_globals: Dict[str, Any] = {
                "__file__": str(outfile),
                "__name__": "__main__",
                "Path": Path,
                "workdir": workdir,
                "format": ctx_format,  # ctx["format"]を直接使用
                "chart": context.get("chart") if isinstance(context, dict) else None,
                "save_df_to_csv": save_df_to_csv,
                "_save_parquet": _save_parquet,
                "json": json,
            }
            if _LATEST_DF is not None:
                exec_globals["df"] = _LATEST_DF
            print(f"[DEBUG] Executing code:\n{code}")
            print(f"[DEBUG] exec_globals keys: {list(exec_globals.keys())}")
            print(f"[DEBUG] format value: {exec_globals['format']}")
            print(f"[DEBUG] workdir exists: {workdir.exists()}, writable: {os.access(workdir, os.W_OK)}")
            try:
                exec(code, exec_globals)
                result = exec_globals.get("result", {})
                if not isinstance(result, dict):
                    return ("", {"error": "Code did not return a valid JSON bundle"})
                print(f"[DEBUG] Execution result: {result}")
                return ("", {"result": result})
            except Exception as exc:
                print(f"[DEBUG] Execution failed: {exc}")
                return ("", {"error": str(exc)})
        return eval_code

    def create_codeact_agent(workdir: Path, ctx_format: str):
        """Create CodeAct agent with format-specific eval_fn."""
        return (
            create_codeact(
                openai_model,
                [save_df_to_csv, _save_parquet],
                _make_eval_fn(workdir, ctx_format),
            )
            .compile(checkpointer=MemorySaver())
        )

def fallback_node(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Run CodeAct (if enabled) and adapt its output to the test contract."""
    global _LATEST_DF
    _LATEST_DF = ctx["df"]

    if not USE_CODEACT:
        if FALLBACK_ENABLED:
            return _fallback_quick(ctx)
        raise ValueError("CodeAct is disabled and fallback is not enabled")

    workdir = TMPDIR
    before = {p.name for p in workdir.iterdir()}

    # ctx["format"]をエージェントに渡す
    _codeact_agent = create_codeact_agent(workdir, ctx["format"])

    prompt = (
        f"グローバル変数として、pandas DataFrameの`df`、Pathオブジェクトの`workdir`、文字列の`format`（'{ctx['format']}'）、およびオプションの`chart`が与えられます。\n"
        "あなたのタスクは、`format`に基づいて`df`をファイルに保存するPythonコードを生成することです。\n"
        "- `format`が'csv'の場合、`save_df_to_csv(df, path)`を使用して`workdir/'output.csv'`に保存します。\n"
        "- `format`が'parquet'の場合、`_save_parquet(df, path)`を使用して`workdir/'result.parquet'`に保存します。\n"
        "- `chart`がNoneでない場合、`df[chart.x]`と`df[chart.y]`の散布図を作成し、`workdir/'output.png'`に保存します。\n"
        "以下の要件を満たしてください：\n"
        "- `main()`関数を定義し、要求された操作を実行して辞書を返します。\n"
        "- 辞書を`result`変数に割り当て、キーは{{'filename': str, 'code': str, 'requirements': list, 'timeout_sec': int}}です。\n"
        "- グローバル変数`format`, `df`, `workdir`, `save_df_to_csv`を明示的に使用します。\n"
        f"- 現在の`format`は'{ctx['format']}'です。\n"
        "CSVの例（format='csv'の場合）：\n"
        "```python\n"
        "from pathlib import Path\n"
        "def main():\n"
        "    global format, df, workdir, save_df_to_csv\n"
        "    save_df_to_csv(df, workdir / 'output.csv')\n"
        "    return {{'filename': 'output.csv', 'code': 'save_df_to_csv(df, workdir / \"output.csv\")', 'requirements': [], 'timeout_sec': 10}}\n"
        "result = main()\n"
        "```\n"
        "何も印刷しないでください。コードブロック外に説明テキストやコメントを含めないでください。\n"
        "コードがエラーなく実行され、指定された出力ファイルが生成されることを確認してください。\n"
    )

    try:
        raw = _codeact_agent.invoke(
            {
                "messages": [{"role": "user", "content": prompt}],
                "format": ctx["format"],
            },
            config={
                "configurable": {
                    "thread_id": ctx.get("task_id", str(uuid.uuid4())),
                    "temperature": 0,
                }
            },
        )
    except Exception as exc:
        raise RuntimeError(f"CodeAct failed: {exc}") from exc

    # ── 正常化 ─────────────────────────────────────
    if isinstance(raw, tuple) and len(raw) == 2:
        raw = raw[1]

    result_dict: Dict[str, Any] | None = None
    if isinstance(raw, dict):
        result_dict = raw.get("result", raw)
    elif isinstance(raw, str):
        try:
            result_dict = json.loads(raw)
        except json.JSONDecodeError:
            tmp: Dict[str, Any] = {}
            try:
                exec(raw, tmp)
                if isinstance(tmp.get("result"), dict):
                    result_dict = tmp["result"]
            except Exception:
                pass

    files: List[str] = []
    if result_dict and isinstance(result_dict.get("files"), list):
        files = [str(f) for f in result_dict["files"]]
    elif result_dict and result_dict.get("filename") not in {None, "", "None"}:
        files = [str(workdir / result_dict["filename"])]

    # 期待される出力ファイルをチェック
    expected_file = workdir / "output.csv" if ctx["format"] == "csv" else workdir / "result.parquet"
    if expected_file.exists() and str(expected_file) not in files:
        files.append(str(expected_file))

    if not files:
        print(f"[DEBUG] Workdir contents: {[p.name for p in workdir.iterdir()]}")
        return _return_created_files(workdir, before)

    return {"files": files, "used_codeact": True}

def _return_created_files(workdir: Path, before: set[str]) -> Dict[str, Any]:
    created = sorted({p.name for p in workdir.iterdir()} - before)
    if created:
        return {"files": [str(workdir / f) for f in created], "used_codeact": True}
    return {"error": "No output file generated", "used_codeact": True}