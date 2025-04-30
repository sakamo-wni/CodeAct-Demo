# tests/test_openai.py
from app.models.openai_client import invoke_openai

def test_openai_basic():
    """OpenAI API が動いて応答が返るかだけ確認"""
    rsp = invoke_openai("あなたにできることは何？")
    assert isinstance(rsp, str) and len(rsp) > 0

# 単体実行したいとき用
if __name__ == "__main__":
    print(invoke_openai("単体実行テスト: あなたができること は？"))