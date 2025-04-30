# app/models/openai_client.py
from openai import OpenAI
from app.config import settings
import os
from typing import Any, Union
from langchain.chat_models import ChatOpenAI

client = OpenAI(
    api_key=settings.openai_api_key,
)

def invoke_openai(
    prompt: str,
    max_tokens: int = 256,
    temperature: float = 0.0,
) -> Union[str, dict]:
    """OpenAI ChatCompletions を呼び出す簡易ラッパー
       - 旧コード互換のため str も返せるようにする
    """
    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.codeact_model.split(":", 1)[-1],
        temperature=temperature,
    )
    rsp = llm.invoke(prompt, max_tokens=max_tokens)

    # ---- 戻り値を統一的に「テキスト str」で返す ----
    if hasattr(rsp, "content"):          # LangChain AIMessage
        return rsp.content
    if isinstance(rsp, dict):            # OpenAI raw dict 形式
        # {"content":[{"text": "..."}]} という構造
        try:
            return rsp["content"][0]["text"]
        except Exception:
            pass

    # それ以外はそのまま
    return str(rsp)

# デバッグ用: python -m app.models.openai_client "こんにちは"
if __name__ == "__main__":
    import sys, json
    q = sys.argv[1] if len(sys.argv) > 1 else "2+2 は？"
    print(json.dumps({"answer": invoke_openai(q)}, ensure_ascii=False, indent=2))
