# app/config.py
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# プロジェクト Root（backend ディレクトリ）を特定
BACKEND_ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # --- 一般 ---
    api_port: int = Field(7000, description="FastAPI listen port")
    aws_profile: str | None = Field(None, alias="AWS_PROFILE")
    aws_default_region: str = Field("us-east-1", alias="AWS_DEFAULT_REGION")
    s3_bucket: str = Field("wni-wfc-stock-ane1", alias="S3_BUCKET")

    # --- LLM / Bedrock ---
    llm_provider: str = Field("bedrock")
    bedrock_model_id: str | None = Field(None, alias="BEDROCK_MODEL_ID")
    bedrock_access_key_id: str | None = Field(None, alias="BEDROCK_ACCESS_KEY_ID")
    bedrock_secret_access_key: str | None = Field(None, alias="BEDROCK_SECRET_ACCESS_KEY")
    bedrock_session_token: str | None = Field(None, alias="BEDROCK_SESSION_TOKEN")
    bedrock_region: str = Field("us-east-1", alias="BEDROCK_REGION")

    # --- Pydantic Settings ---
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env.docker"),   # ← ルート直下を読む
        extra="ignore",
        case_sensitive=False,
    )

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
