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
                  **kwargs) -> str:
    """
    OpenAI Chat Completions の薄いラッパー。
    fallback_node から tools を渡すと CodeAct として動く。
    """
    rsp = client.chat.completions.create(
        model=(model or settings.codeact_model).split(":", 1)[-1],  # "gpt-4o"
        messages=[{"role": "user", "content": prompt}],
        tools=tools,
        tool_choice="auto" if tools else None,
        **kwargs,
    )
    return rsp.choices[0].message.content

# デバッグ用: python -m app.models.openai_client "こんにちは"
if __name__ == "__main__":
    import sys, json
    q = sys.argv[1] if len(sys.argv) > 1 else "2+2 は？"
    print(json.dumps({"answer": invoke_openai(q)}, ensure_ascii=False, indent=2))
