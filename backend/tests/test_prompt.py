from app.agent.tools.fallback_node import _build_prompt
from app.models.bedrock_client import invoke_claude
import json
import re

def _parse_response(text: str, task_name: str) -> dict:
    """Claudeの応答をパースしてJSONオブジェクトを返す。"""
    # JSON または Python ブロックを抽出
    json_match = re.search(r'```(?:json|python)\n([\s\S]*?)\n```', text)
    if json_match:
        json_text = json_match.group(1).replace("\n", "")
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse {task_name} JSON block: {json_text}, error: {str(e)}")
    
    # プレーンJSONを試す（改行をエスケープ）
    cleaned_text = text.replace("\n", "\\n").strip()
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        raise ValueError(f"No JSON or Python block found for {task_name}, and text is not valid JSON: {cleaned_text}")

def test_prompt_generation():
    # テストケース1：Parquet変換
    ctx = {"format": "parquet", "task_id": "test-123"}
    prompt = _build_prompt(ctx, ctx["task_id"])
    print("Prompt for Parquet:", prompt)
    response = invoke_claude(prompt, max_tokens=512)
    print("Raw response for Parquet:", response)
    try:
        response_json = json.loads(response)
        parsed = _parse_response(response_json["content"][0]["text"], "Parquet")
        print("Parsed JSON for Parquet:", parsed)
        assert "filename" in parsed
        assert "code" in parsed
        assert "requirements" in parsed
        assert "timeout_sec" in parsed
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse Parquet response as JSON: {response}, error: {str(e)}")
        raise

    # テストケース2：散布図
    ctx = {"chart": "scatter", "x": "time", "y": "AIRTMP", "task_id": "test-124"}
    prompt = _build_prompt(ctx, ctx["task_id"])
    print("Prompt for Scatter:", prompt)
    response = invoke_claude(prompt, max_tokens=512)
    print("Raw response for Scatter:", response)
    try:
        response_json = json.loads(response)
        parsed = _parse_response(response_json["content"][0]["text"], "Scatter")
        print("Parsed JSON for Scatter:", parsed)
        assert "filename" in parsed
        assert "code" in parsed
        assert "requirements" in parsed
        assert "timeout_sec" in parsed
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse Scatter response as JSON: {response}, error: {str(e)}")
        raise

    # テストケース3：ヒートマップ
    ctx = {"chart": "heatmap", "x": "lat", "y": "lon", "vars": ["AIRTMP"], "task_id": "test-125"}
    prompt = _build_prompt(ctx, ctx["task_id"])
    print("Prompt for Heatmap:", prompt)
    response = invoke_claude(prompt, max_tokens=512)
    print("Raw response for Heatmap:", response)
    try:
        response_json = json.loads(response)
        parsed = _parse_response(response_json["content"][0]["text"], "Heatmap")
        print("Parsed JSON for Heatmap:", parsed)
        assert "filename" in parsed
        assert "code" in parsed
        assert "requirements" in parsed
        assert "timeout_sec" in parsed
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse Heatmap response as JSON: {response}, error: {str(e)}")
        raise

    # テストケース4：CSV変換
    ctx = {"format": "csv", "task_id": "test-126"}
    prompt = _build_prompt(ctx, ctx["task_id"])
    print("Prompt for CSV:", prompt)
    response = invoke_claude(prompt, max_tokens=512)
    print("Raw response for CSV:", response)
    try:
        response_json = json.loads(response)
        parsed = _parse_response(response_json["content"][0]["text"], "CSV")
        print("Parsed JSON for CSV:", parsed)
        assert "filename" in parsed
        assert "code" in parsed
        assert "requirements" in parsed
        assert "timeout_sec" in parsed
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse CSV response as JSON: {response}, error: {str(e)}")
        raise