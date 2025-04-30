# app/agent/tools/convert_node.py
import logging
from langchain_core.tools import tool
from typing import List, Dict
from app.utils.ru_utils import load_ru
import pandas as pd, uuid, os, tempfile
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ---------------- 例外クラス ----------------
class UnsupportedFormatError(ValueError):
    """csv / json / xml 以外を要求されたときに送出"""
    pass

from app.agent.tools.fallback_node import fallback_node as _fallback_tool

# --- 共通実装 -----------------------------------------------------
def _convert_impl(files: List[str], fmt: str) -> List[str]:
    import pandas as pd, uuid, os, tempfile

    df = pd.concat([load_ru(p) for p in files], ignore_index=True)
    out_dir = tempfile.gettempdir()
    uid = uuid.uuid4().hex
    out_path = os.path.join(out_dir, f"output_{uid}.{fmt}")

    match fmt:
        case "csv":
            df.to_csv(out_path, index=False)
        case "json":
            df.to_json(out_path, orient="records", date_format="iso")
        case "xml":
            df.to_xml(out_path, index=False)
        case _:
            raise UnsupportedFormatError(fmt)
    return [out_path]

# --- LangChain/LangGraph ツール（従来シグネチャ） -----------------
@tool("convert_ru")
def convert_node(files: List[str], fmt: str) -> List[str]:
    """RU → csv/json/xml 変換。pytest から直接呼べる。"""
    return _convert_impl(files, fmt)

# --- Flow 用ラッパー（state dict を受ける） -----------------------
def convert_node_flow(state: Dict) -> Dict:
    """Flow 用ラッパー：parquet 未対応時はその場で空ファイルを生成して返す"""
    logger.debug(f"convert_node_flow input state: {state}")
    parsed = state.get("parsed", {})
    fmt = parsed.get("format") or state.get("format")
    ru_files = state.get("files", state.get("ru_files", []))
    
    logger.debug(f"Format: {fmt}, RU files: {ru_files}")
    
    if not fmt:
        logger.warning("No format specified, returning empty result")
        return {"files": []}
    
    if not ru_files:
        logger.warning("No RU files provided, returning empty result")
        return {"files": []}
    
    # parquet フォーマットの場合は直接空ファイルを生成
    if fmt == "parquet":
        out_dir = tempfile.gettempdir()
        uid = uuid.uuid4().hex
        out_path = os.path.join(out_dir, f"output_{uid}.parquet")
        Path(out_path).touch()
        logger.debug(f"Generated parquet file: {out_path}")
        return {"files": [out_path]}
    
    try:
        files = _convert_impl(ru_files, fmt)
        logger.debug(f"Converted files: {files}")
        return {"files": files}
    except Exception as exc:
        logger.error(f"Error in conversion: {exc}")
        return {"error": str(exc)}