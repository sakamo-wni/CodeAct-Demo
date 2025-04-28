# backend/app/models/bedrock_client.py
from boto3 import Session, client
from botocore.config import Config as BotoConfig
import json
from app.config import get_settings

settings = get_settings()

# --- S3 用：SSO プロファイル ------------------------------
s3_session = Session(profile_name=settings.aws_profile)
s3_client = s3_session.client("s3")

# --- Bedrock 用：キー認証 -------------------------------
bedrock_client = client(
    "bedrock-runtime",
    region_name=settings.bedrock_region,
    aws_access_key_id=settings.bedrock_access_key_id,
    aws_secret_access_key=settings.bedrock_secret_access_key,
    aws_session_token=settings.bedrock_session_token,
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
    resp = bedrock_client.invoke_model(
        modelId=settings.bedrock_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload).encode("utf-8"),
    )
    return resp["body"].read().decode("utf-8")
