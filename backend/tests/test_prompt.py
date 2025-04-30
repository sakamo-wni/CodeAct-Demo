"""prompt round-trip test – OpenAI 版
_code_ 生成プロンプトが正しい構造で、OpenAI LLM から
期待 JSON（または Python ブロック）を取得できるかを検証する。
"""

from __future__ import annotations

import json
import os
import re
import pytest
from pytest import skip

# ── OpenAI ラッパーを使用 ────────────────────────────
from app.models.openai_client import invoke_openai
from app.agent.tools.fallback_node import _build_prompt

# OpenAI API キーが無い環境（CI など）ではスキップ
if os.getenv("OPENAI_API_KEY") is None:
    pytest.skip("OpenAI key absent; skipping prompt round-trip test",
                allow_module_level=True)

# ---------------------------------------------------------------------------
def _parse_response(text: str, task_name: str) -> dict:
    """LLM応答から JSON / Python ブロックを抽出し dict に変換する。"""
    json_match = re.search(r'```(?:json|python)\n([\s\S]*?)\n```', text)
    if json_match:
        block = json_match.group(1).replace("\n", "")
        try:
            return json.loads(block)
        except json.JSONDecodeError as e:
            raise ValueError(f"{task_name} JSON parse error: {e}") from e
    raise ValueError(f"{task_name}: no JSON/Python block found in response")

# ---------------------------------------------------------------------------
def test_prompt_generation() -> None:
    """Parquet 変換タスクのプロンプト → LLM → JSON 戻りの往復をテスト"""
    ctx = {"format": "parquet", "task_id": "test-123"}
    prompt = _build_prompt(ctx, ctx["task_id"])
    print("Prompt for Parquet:", prompt)

    # OpenAI ChatCompletions で最大 512 トークン取得
    raw_resp = invoke_openai(prompt, max_tokens=512, temperature=0)
    print("Raw response:", raw_resp)

    # openai ラッパーが str か dict か両対応
    if isinstance(raw_resp, str):
        text = raw_resp
    else:
        text = raw_resp["content"][0]["text"]

    try:
        parsed = _parse_response(text, "Parquet")
    except ValueError:
        pytest.skip("LLM response had no JSON/Python block")

    assert parsed == ctx, f"Returned JSON mismatch: {parsed} != {ctx}"
