# backend/app/codeact_sandbox.py
import resource
import tempfile
import os
import uuid
import runpy
from pathlib import Path
from types import ModuleType

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
    resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))


def run_code_act(code: str, context: dict) -> str:
    """
    生成された Python コードを制限付き環境で実行し、結果ファイルのパスを返す
    """
    workdir = Path(tempfile.gettempdir()) / "codeact" / str(uuid.uuid4())
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

        # --- 実行 ----------------------------------------
        runpy.run_path(str(exec_path), run_name="__main__")
        return str(workdir)
    finally:
        __builtins__["__import__"] = original_import  # type: ignore
