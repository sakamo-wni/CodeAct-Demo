"""
fallback_node – CodeAct 0.1.3 対応版
───────────────────────────────────────────────────────────────
* CodeActContext が Pydantic-model で渡る場合でも format='csv' 等を
  正しく引き渡し、生成コードが output.csv / result.json を作成
* (code_str, {"result": {...}}) 形式の戻り値を許容
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
import uuid
import ast
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from langchain_openai import ChatOpenAI
from app.config import settings
from langgraph.checkpoint.memory import MemorySaver
from langgraph_codeact import create_codeact

USE_CODEACT: bool = os.getenv("CODEACT_DISABLED", "0") != "1"
FALLBACK_ENABLED: bool = os.getenv("FALLBACK_ENABLED", "1") == "1"

__all__ = ["fallback_node", "_build_prompt", "USE_CODEACT"]

def _build_prompt(ctx: dict[str, Any], task_id: str | None = None) -> str:
    """
    tests/test_prompt.py から import される関数。

    ctx には {"format": "...", "task_id": "...", ...} が入る。
    DataFrame は巨大なので除外し、残りを JSON 表現した文字列を返す。
    """
    safe_ctx = {k: v for k, v in ctx.items() if k != "df"}
    json_body = json.dumps(safe_ctx, ensure_ascii=False)
    return (
        "Generate python code for the following task.\n"
        f"```json\n{json_body}\n```"
    )

def save_df_to_csv(df: pd.DataFrame, path: str | Path) -> None:
    """Save **df** to *path* as CSV (quoted, no index)."""
    df.to_csv(path, index=False, quoting=csv.QUOTE_NONNUMERIC)

def save_df_to_json(df: pd.DataFrame, path: str | Path) -> None:
    """Save **df** to *path* as JSON, ensuring LCLID is string."""
    df = df.copy()
    df["LCLID"] = df["LCLID"].astype(str).str.zfill(5)  # ゼロパディングを保持
    df.to_json(path, orient="records", lines=True)

_LATEST_DF: pd.DataFrame | None = None

def _fallback_quick(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Always generate output file under a temp dir and return its path."""
    df: pd.DataFrame = ctx["df"]
    fmt = ctx["format"]
    workdir = Path(tempfile.mkdtemp(prefix="codeact_quick_"))
    out = workdir / f"output.{fmt}"
    if fmt == "csv":
        save_df_to_csv(df, out)
    elif fmt == "json":
        save_df_to_json(df, out)
    else:
        raise ValueError(f"Unsupported format: {fmt}")
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
                "format": ctx_format,
                "save_df_to_csv": save_df_to_csv,
                "save_df_to_json": save_df_to_json,
                "json": json,
            }
            if _LATEST_DF is not None:
                exec_globals["df"] = _LATEST_DF
            print(f"[DEBUG] Executing code:\n{code}")
            print(f"[DEBUG] exec_globals keys: {list(exec_globals.keys())}")
            print(f"[DEBUG] format value: {exec_globals['format']}")
            print(f"[DEBUG] workdir exists: {workdir.exists()}, writable: {os.access(workdir, os.W_OK)}")
            try:
                ast.parse(code)
                exec(code, exec_globals)
                result = exec_globals.get("result", {})
                if not isinstance(result, dict):
                    return ("", {"error": "Code did not return a valid JSON bundle"})
                print(f"[DEBUG] Execution result: {result}")
                return ("", {"result": result})
            except SyntaxError as se:
                print(f"[DEBUG] SyntaxError in generated code: {se}")
                return ("", {"error": f"SyntaxError: {se}"})
            except Exception as exc:
                print(f"[DEBUG] Execution failed: {exc}")
                return ("", {"error": str(exc)})
        return eval_code

    def create_codeact_agent(workdir: Path, ctx_format: str):
        """Create CodeAct agent with format-specific eval_fn."""
        return (
            create_codeact(
                openai_model,
                [save_df_to_csv, save_df_to_json],
                _make_eval_fn(workdir, ctx_format),
            )
            .compile(checkpointer=MemorySaver())
        )

def fallback_node(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Run CodeAct (if enabled) and adapt its output to the test contract.
    
    The input DataFrame (ctx['df']) is derived from sample.ru, parsed using RUParser
    with location.json to map observation station IDs and metadata.
    """
    global _LATEST_DF
    _LATEST_DF = ctx["df"]

    if not USE_CODEACT:
        if FALLBACK_ENABLED:
            return _fallback_quick(ctx)
        raise ValueError("CodeAct is disabled and fallback is not enabled")

    workdir = TMPDIR
    workdir.mkdir(exist_ok=True)
    before = {p.name for p in workdir.iterdir()}
    _codeact_agent = create_codeact_agent(workdir, ctx["format"])

    prompt = (
        f"Generate Python code to save a pandas DataFrame `df` to a file based on the global string variable `format` ('{ctx['format']}').\n"
        "Available functions:\n"
        "- `save_df_to_csv(df, path)`: Save to `workdir/'output.csv'`.\n"
        "- `save_df_to_json(df, path)`: Save to `workdir/'output.json'`.\n"
        "Requirements:\n"
        "- Define a `main()` function that returns a dictionary {{'filename': str, 'code': str, 'requirements': list, 'timeout_sec': int}}.\n"
        "- Use global variables `format`, `df`, `workdir`, and the appropriate save function.\n"
        "- Generate a single complete code block with no extra text, comments, or print statements.\n"
        f"- Current `format` is '{ctx['format']}'.\n"
        f"Example for format='{ctx['format']}':\n"
        "```python\n"
        "from pathlib import Path\n"
        "def main():\n"
        f"    global format, df, workdir, save_df_to_{ctx['format']}\n"
        f"    if format == '{ctx['format']}':\n"
        f"        save_df_to_{ctx['format']}(df, workdir / 'output.{ctx['format']}')\n"
        f"        return {{'filename': 'output.{ctx['format']}', 'code': 'save_df_to_{ctx['format']}(df, workdir / \"output.{ctx['format']}\")', 'requirements': [], 'timeout_sec': 10}}\n"
        "    return {'filename': '', 'code': '', 'requirements': [], 'timeout_sec': 10}\n"
        "result = main()\n"
        "```\n"
        "Do not include any text outside the code block. Ensure the code is syntactically correct and completes in one response.\n"
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
                    "recursion_limit": 50,
                    "max_iterations": 5,  # 再帰を制限
                }
            },
        )
    except Exception as exc:
        print(f"[DEBUG] CodeAct invocation failed: {exc}")
        raise RuntimeError(f"CodeAct failed: {exc}") from exc

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

    expected_file = workdir / f"output.{ctx['format']}"
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