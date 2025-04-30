"""
LangGraph — interpret → fetch → convert / viz
"""

from __future__ import annotations
import json, re
from typing import TypedDict, List, Dict, Any, Optional
import logging

from langgraph.graph import StateGraph, END, START
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field, ValidationError

from app.models.bedrock_client import invoke_claude
from app.agent.tools.s3_fetcher import LoadRuFilesTool
from app.agent.tools.convert_node import convert_node_flow
from app.agent.tools.viz_node import viz_node as _vz_tool
from app.agent.tools.fallback_node import fallback_node as _fb_tool
from app.utils.country_resolver import (
    resolve_country_name,
    find_tag_ids_by_country,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

viz_node = _vz_tool.func
fallback_node = _fb_tool.func

# ---------- 1. 状態定義 -------------------------------------------------
class FlowState(TypedDict, total=False):
    input:     str
    parsed:    Dict[str, Any]
    files:     List[str]
    converted: List[str]
    images:    List[str]
    error:     Optional[str]

# ---------- 2. Claude が返す JSON スキーマ -----------------------------
class ParsedParams(BaseModel):
    tag_id:   str | None = Field(None, pattern=r"\d{9}")
    start_dt: str | None = None
    end_dt:   str | None = None
    country:  str | None = None
    format:   str | None = None          # csv/json/xml
    chart:    str | None = None          # scatter/bar/map
    x:        str | None = None
    y:        str | None = None
    vars:     List[str] | None = None    # 気象変数リスト

json_parser = JsonOutputParser(pydantic_schema=ParsedParams)

KEY_MAP = {
    "agent_id":   "tag_id",
    "target_id":  "tag_id",
    "start_time": "start_dt",
    "end_time":   "end_dt",
}

# ---------- 3. Claude 失敗時の JSON 抽出 -------------------------------
def _extract_json(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, dict) and "content" in payload:
        payload = payload["content"][0].get("text", "")
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode()
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except Exception:
            if m := re.search(r"\{[\s\S]+?\}", payload):
                try:
                    return json.loads(m.group(0))
                except Exception:
                    return None
    return None

# ---------- 4. interpret_node ------------------------------------------
def interpret_node(state: FlowState) -> Dict[str, Any]:
    logger.debug(f"interpret_node input state: {state}")
    user_input = state["input"]

    prompt = (
        "You are a JSON extraction agent.\n"
        "Return ONLY a JSON object matching this schema:\n"
        f"{json_parser.get_format_instructions()}\n\n"
        f"User: {user_input}"
    )
    raw = invoke_claude(prompt)

    try:
        parsed: Dict[str, Any] = json_parser.parse(raw).model_dump()
    except ValidationError:
        parsed = _extract_json(raw) or {}

    parsed = {KEY_MAP.get(k, k): v for k, v in parsed.items()}

    # country から TagID 補完 ---------------------------------
    if "tag_id" not in parsed and "country" in parsed:
        country = resolve_country_name(parsed["country"])
        tag_ids = find_tag_ids_by_country(country)
        if tag_ids:
            parsed["tag_id"] = tag_ids[0]

    logger.debug(f"interpret_node result: {parsed}")
    return {"parsed": parsed}

# ---------- 5. fetch_node ---------------------------------------------
s3_tool = LoadRuFilesTool()

def fetch_node(state: FlowState) -> Dict[str, List[str]]:
    logger.debug(f"fetch_node input state: {state}")
    p = state["parsed"]
    if not (p.get("tag_id") and p.get("start_dt")):
        return {"files": ["Error: insufficient keys"]}

    try:
        files = s3_tool._run(
            tag_id=p["tag_id"],
            start_dt=p["start_dt"],
            end_dt=p.get("end_dt"),
        )
        logger.debug(f"fetch_node result: {files}")
        return {"files": files}
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        return {"files": [f"Error: {e}"]}

# ---------- 6. convert_node ラッパー ----------------------------------
def run_convert_node(state: FlowState) -> Dict[str, Any]:
    logger.debug(f"run_convert_node input state: {state}")
    fmt = state["parsed"].get("format") or state.get("format")
    files = state.get("files", state.get("ru_files", []))
    if not fmt:
        logger.warning("No format specified, returning empty result")
        return {"files": []}
    try:
        result = convert_node_flow({"parsed": state["parsed"], "files": files, "ru_files": files})
        logger.debug(f"convert_node_flow result: {result}")
        return result
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return {"error": str(e)}

# ---------- 7. viz_node ラッパー --------------------------------------
def run_viz_node(state: FlowState) -> Dict[str, Any]:
    logger.debug(f"run_viz_node input state: {state}")
    if "parsed" not in state or not state["parsed"].get("chart"):
        logger.debug("No chart specified, passing through files")
        return {"files": state.get("files", [])}

    try:
        img = viz_node(
            state["files"],
            chart=state["parsed"].get("chart"),
            tag_id=state["parsed"].get("tag_id"),
            variables=state["parsed"].get("vars"),
            x=state["parsed"].get("x"),
            y=state["parsed"].get("y"),
        )
        logger.debug(f"viz_node result: {img}")
        return {"images": [img], "files": state.get("files", [])}
    except Exception as e:
        logger.error(f"Viz error: {e}")
        return {"error": str(e)}

# ---------- 8. グラフ構築 ---------------------------------------------
graph = StateGraph(FlowState)

graph.add_node("interpret", interpret_node)
graph.add_node("fetch",     fetch_node)
graph.add_node("convert",   run_convert_node)  # convert_node_flow をラッパーで呼ぶ
graph.add_node("viz",       run_viz_node)
graph.add_node("fallback",  fallback_node)
graph.add_node("finish",    lambda s: {"files": s.get("files", [])})

graph.add_edge("interpret", "fetch")
graph.add_edge("fetch",     "convert")
graph.add_edge("fetch",     "viz")      # 変換不要でも viz 可

# ----- convert 結果で分岐 ---------------------------------------
def after_convert(state):
    logger.debug(f"after_convert state: {state}")
    next_node = "fallback" if state.get("error") else "viz"
    logger.debug(f"after_convert next: {next_node}")
    return next_node
graph.add_conditional_edges("convert", after_convert)

# ----- viz 結果で分岐 ------------------------------------------
def after_viz(state):
    logger.debug(f"after_viz state: {state}")
    next_node = "fallback" if state.get("error") else "finish"
    logger.debug(f"after_viz next: {next_node}")
    return next_node
graph.add_conditional_edges("viz", after_viz)

# ----- fallback から finish へ抜ける ---------------------------
graph.add_edge("fallback", "finish")

graph.set_entry_point("convert")
graph.set_finish_point("finish")

# --- ここでコンパイルして "実行グラフ" をエクスポート -------------
graph = graph.compile()
