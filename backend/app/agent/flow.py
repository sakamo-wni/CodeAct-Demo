"""
LangGraph — interpret → fetch → convert / viz
"""

from __future__ import annotations
import json, re
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field, ValidationError

from app.models.bedrock_client import invoke_claude
from app.agent.tools.s3_fetcher import LoadRuFilesTool
from app.agent.tools.convert_node import convert_node
from app.agent.tools.viz_node import viz_node
from app.utils.country_resolver import (
    resolve_country_name,
    find_tag_ids_by_country,
)

# ---------- 1. 状態定義 -------------------------------------------------
class FlowState(TypedDict, total=False):
    input:     str
    parsed:    Dict[str, Any]
    files:     List[str]
    converted: List[str]
    images:    List[str]

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

    # date + hh:mm の補完 & その他正規表現フォールバックは省略（同前）

    return {"parsed": parsed}

# ---------- 5. fetch_node ---------------------------------------------
s3_tool = LoadRuFilesTool()

def fetch_node(state: FlowState) -> Dict[str, List[str]]:
    p = state["parsed"]
    if not (p.get("tag_id") and p.get("start_dt")):
        return {"files": ["Error: insufficient keys"]}

    try:
        files = s3_tool._run(
            tag_id=p["tag_id"],
            start_dt=p["start_dt"],
            end_dt=p.get("end_dt"),
        )
        return {"files": files}
    except Exception as e:
        return {"files": [f"Error: {e}"]}

# ---------- 6. convert_node ラッパー ----------------------------------
def run_convert_node(state: FlowState) -> Dict[str, Any]:
    fmt = state["parsed"].get("format")
    if not fmt:
        return {}
    try:
        paths = convert_node.func(state["files"], fmt)
        return {"converted": paths}
    except Exception as e:
        return {"converted": [f"Error: {e}"]}

# ---------- 7. viz_node ラッパー --------------------------------------
def run_viz_node(state: FlowState) -> Dict[str, Any]:
    chart = state["parsed"].get("chart")
    if not chart:
        return {}
    try:
        img = viz_node.func(
            state["files"],
            chart,
            tag_id=state["parsed"].get("tag_id"),
            variables=state["parsed"].get("vars"),
            x=state["parsed"].get("x"),
            y=state["parsed"].get("y"),
        )
        return {"images": [img]}
    except Exception as e:
        return {"images": [f"Error: {e}"]}

# ---------- 8. グラフ構築 ---------------------------------------------
graph = StateGraph(FlowState)
graph.add_node("interpret", interpret_node)
graph.add_node("fetch",     fetch_node)
graph.add_node("convert",   run_convert_node)
graph.add_node("viz",       run_viz_node)

graph.set_entry_point("interpret")
graph.add_edge("interpret", "fetch")
graph.add_edge("fetch",     "convert")
graph.add_edge("fetch",     "viz")      # 変換不要でも viz 可
graph.set_finish_point("viz")

workflow = graph.compile()
