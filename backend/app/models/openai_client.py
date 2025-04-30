# app/models/openai_client.py
from openai import OpenAI
from app.config import settings          # 先ほど追加した設定

client = OpenAI(
    api_key=settings.openai_api_key,
)

def invoke_openai(prompt: str,
                  *,
                  model: str | None = None,
                  tools: list | None = None,
                  max_tokens: int = 256,
                  temperature: float = 0.0,
                  **kwargs) -> dict:
    """
    OpenAI Chat Completions の薄いラッパー。
    fallback_node から tools を渡すと CodeAct として動く。
    テスト互換フォーマットで結果を返す。
    """
    rsp = client.chat.completions.create(
        model=(model or settings.codeact_model).split(":", 1)[-1],  # "gpt-4o"
        messages=[{"role": "user", "content": prompt}],
        tools=tools,
        tool_choice="auto" if tools else None,
        max_tokens=max_tokens,
        temperature=temperature,
        **kwargs,
    )
    content_text = rsp.choices[0].message.content
    return {
        "content": [{"text": content_text}]
    }

# デバッグ用: python -m app.models.openai_client "こんにちは"
if __name__ == "__main__":
    import sys, json
    q = sys.argv[1] if len(sys.argv) > 1 else "2+2 は？"
    print(json.dumps({"answer": invoke_openai(q)}, ensure_ascii=False, indent=2))
