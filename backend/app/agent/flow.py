"""
LangGraph PoC — Claude 3 Sonnet でパラメータ抽出 → S3 取得
(1) LLM → JsonOutputParser で構造化
(2) フォーマット逸脱時は _extract_json() で安全抽出
(3) キー名を標準化して型バリデーション
"""

from __future__ import annotations
import json, re
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field, ValidationError

from app.models.bedrock_client import invoke_claude
from app.agent.tools.s3_fetcher import LoadRuFilesTool

# ─── 1. Flow State ───────────────────────────────────────────────
class FlowState(TypedDict, total=False):
    input:  str
    parsed: Dict[str, Any]
    files:  List[str]

# ─── 2. Pydantic schema Claude should output ─────────────────────
class ParsedParams(BaseModel):
    tag_id:   str = Field(..., pattern=r"\d{9}")
    start_dt: str
    end_dt:   str

json_parser = JsonOutputParser(pydantic_schema=ParsedParams)

# Claude が使いがちな別名 → 標準キーへのマッピング
KEY_MAP = {
    "agent_id":   "tag_id",
    "target_id":  "tag_id",
    "start_time": "start_dt",
    "end_time":   "end_dt",
}

# ─── 3. Utility: safely extract JSON from any Claude reply ────────
def _extract_json(payload: Any) -> Optional[Dict[str, Any]]:
    """Return first JSON object found in Claude reply; None if none."""
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

# ─── 4. Interpret Node ────────────────────────────────────────────
def interpret_node(state: FlowState) -> Dict[str, Any]:
    user_input = state["input"]

    prompt = (
        "あなたは観測データ取得エージェントです。\n"
        "以下 JSON フォーマット『のみ』を返してください。\n"
        f"{json_parser.get_format_instructions()}\n\n"
        f"User: {user_input}"
    )
    raw_reply = invoke_claude(prompt)

    # ① JsonOutputParser で解析
    try:
        params = json_parser.parse(raw_reply)

        # A) pydantic モデルなら dict 化
        if hasattr(params, "model_dump"):
            parsed = params.model_dump()

        # B) dict（Anthropic Message 等）の場合は
        #    content.text から JSON を抽出
        elif isinstance(params, dict):
            parsed = (_extract_json(params) or params)

    except ValidationError:
        # C) そもそも parse できなかった場合
        parsed = _extract_json(raw_reply) or {}

    # ③ キー名を標準化
    parsed = {KEY_MAP.get(k, k): v for k, v in parsed.items()}

    # ④ 欠損キーを正規表現で補完
    if "tag_id" not in parsed:
        if m := re.search(r"\b(\d{9})\b", user_input):
            parsed["tag_id"] = m.group(1)
    if "start_dt" not in parsed:
        if m := re.search(r"(\d{4}-\d{2}-\d{2}).*?(\d{1,2})時", user_input):
            date, hour = m.groups()
            parsed["start_dt"] = f"{date} {int(hour):02d}:00:00"
    if "end_dt" not in parsed and "start_dt" in parsed:
        ymd, hms = parsed["start_dt"].split()
        hour = int(hms[:2]) + 1
        parsed["end_dt"] = f"{ymd} {hour:02d}:00:00"

    return {"parsed": parsed}

# ─── 5. Fetch Node ────────────────────────────────────────────────
s3_tool = LoadRuFilesTool()

def fetch_node(state: FlowState) -> Dict[str, List[str]]:
    data = state["parsed"]
    tag = data.get("tag_id")
    st  = data.get("start_dt")
    et  = data.get("end_dt")

    if not (tag and st):
        return {"files": [f"Error: insufficient keys → {data}"]}

    try:
        files = s3_tool._run(tag_id=tag, start_dt=st, end_dt=et)
        return {"files": files}
    except Exception as e:
        return {"files": [f"Error: {e}"]}

# ─── 6. LangGraph Assembly ────────────────────────────────────────
graph = StateGraph(FlowState)
graph.add_node("interpret", interpret_node)   # input  → parsed
graph.add_node("fetch",     fetch_node)       # parsed → files

graph.set_entry_point("interpret")
graph.add_edge("interpret", "fetch")
graph.set_finish_point("fetch")

workflow = graph.compile()
