# backend/app/models/bedrock_client.py
import boto3
from botocore.config import Config as BotoConfig
import json
from app.config import get_settings

s = get_settings()

# Bedrock 専用セッション（アクセスキーは .env.docker で設定）
session = boto3.Session(
    aws_access_key_id=s.bedrock_access_key_id,
    aws_secret_access_key=s.bedrock_secret_access_key,
    aws_session_token=s.bedrock_session_token,
    region_name=s.bedrock_region,
)

client = session.client(
    "bedrock-runtime",
    config=BotoConfig(retries={"max_attempts": 3, "mode": "standard"}),
)

def invoke_claude(prompt: str, max_tokens: int = 256, temp: float = 0.5) -> str:
    # Claude 3 形式メッセージ
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temp,
    }
    resp = client.invoke_model(
        modelId=s.bedrock_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload).encode("utf-8"),
    )
    return resp["body"].read().decode("utf-8")
