# app/models/openai_client.py
from openai import OpenAI
from app.config import settings
import os
from typing import Any, Union

client = OpenAI(
    api_key=settings.openai_api_key,
)

def invoke_openai(
    prompt: str,
    max_tokens: int = 256,
    temperature: float = 0.0,
) -> Union[str, dict]:
    """
    OpenAI Chat Completions の薄いラッパー。
    環境変数 INVOKE_OPENAI_STRING=1 で後方互換モード（文字列を返す）
    """
    model_name = settings.codeact_model.split(":", 1)[-1]  # "gpt-4o" などを再利用
    resp = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    text = resp.choices[0].message.content

    # ---- 後方互換：文字列 or dict を選択 ----
    if os.getenv("INVOKE_OPENAI_STRING", "0") == "1":
        return text             # 旧テスト用
    return {"content": [{"text": text}]}   # 新フォーマット

# デバッグ用: python -m app.models.openai_client "こんにちは"
if __name__ == "__main__":
    import sys, json
    q = sys.argv[1] if len(sys.argv) > 1 else "2+2 は？"
    print(json.dumps({"answer": invoke_openai(q)}, ensure_ascii=False, indent=2))
