# backend/app/codeact_sandbox.py
import resource
import tempfile
import os
import uuid
import runpy
from pathlib import Path
from types import ModuleType
from typing import Dict, Any

__all__ = ["run_code_act"]

# ------ 安全な import リスト ----------------------------------
SAFE_MODULES = {
    "math",
    "json",
    "datetime",
    "pandas",
    "numpy",
    "matplotlib",
    "seaborn",
}

FORBIDDEN_IMPORTS = {"subprocess", "socket", "os.system", "multiprocessing", "sys.exit"}

def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name.split(".")[0] in FORBIDDEN_IMPORTS:
        raise ImportError(f"Import of '{name}' is blocked for security reasons")
    return original_import(name, globals, locals, fromlist, level)

def _apply_limits(cpu_sec: int = 120, mem_mb: int = 512):
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_sec, cpu_sec))
    mem_bytes = mem_mb * 1024 * 1024

    # 一部 OS で hard-limit 以下しか設定できない場合に備えフォールバック
    try:
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except ValueError:
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        # hard == -1 → 無制限なので skip
        # hard  < mem_bytes → これ以上下げられないので skip
        pass

    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))

def run_code_act(code: str, context: Dict[str, Any]) -> str:
    """
    生成された Python コードを制限付き環境で実行し、結果ディレクトリを返す。
    context["df"] と context["variables_map"] をグローバル変数として設定。
    """
    # ワークディレクトリを準備
    workdir = Path(tempfile.gettempdir()) / "codeact" / context.get("task_id", str(uuid.uuid4()))
    print("WORKDIR:", workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    global original_import
    original_import = __builtins__["__import__"]  # type: ignore

    try:
        # --- セキュア import フック ----------------------
        __builtins__["__import__"] = _safe_import  # type: ignore

        # --- リソース制限 -------------------------------
        _apply_limits()

        # --- 実行用ファイルを作成 ------------------------
        exec_path = workdir / "exec_code.py"
        exec_path.write_text(code)

        # --- グローバル変数を設定 ------------------------
        init_globals = {
            "df": context.get("df"),
            "variables_map": context.get("variables_map")
        }

        # --- 実行 (cwd をワークディレクトリに変更) --------
        original_cwd = os.getcwd()
        os.chdir(workdir)
        try:
            runpy.run_path(str(exec_path), init_globals=init_globals, run_name="__main__")
        finally:
            os.chdir(original_cwd)

        # --- デバッグ: workdir の中身を一覧表示 ----------
        print("DEBUG: files under workdir ->", list(workdir.iterdir()))

        # --- 生成されたファイルのパスを取得 --------------
        output_files = []
        for fmt in ["parquet", "csv", "json", "xml", "png"]:
            output_files.extend(workdir.glob(f"*.{fmt}"))

        if not output_files:
            # ファイルが見つからない場合は空の parquet ファイルを作成
            dummy = workdir / "result.parquet"
            dummy.touch()
            output_files.append(dummy)

        # ワークディレクトリを返す
        return str(workdir)

    finally:
        __builtins__["__import__"] = original_import  # type: ignore