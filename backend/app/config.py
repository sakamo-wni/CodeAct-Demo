# app/config.py
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

# プロジェクト Root（backend ディレクトリ）を特定
ROOT = Path(__file__).resolve().parent.parent

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

    # --- OpenAI ---
    openai_api_key: str = Field(..., validation_alias="OPENAI_API_KEY")
    openai_org_id: str | None = Field(None, validation_alias="OPENAI_ORG_ID")
    codeact_model: str = Field("openai:gpt-4o", validation_alias="CODEACT_MODEL")

    # --- Pydantic Settings ---
    model_config = SettingsConfigDict(
        env_file=[ROOT / ".env", ROOT / ".env.docker"],
        case_sensitive=False,
        extra="ignore",
    )

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

# グローバルなsettingsインスタンスを作成
settings = get_settings()
