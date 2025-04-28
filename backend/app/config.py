from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- メイン設定 ---
    api_port: int = 7000
    llm_provider: str = "bedrock"
    aws_default_region: str = "us-east-1"
    s3_bucket: str = "wni-wfc-stock-ane1"

    # --- Bedrock 専用キー ---
    bedrock_access_key_id: str | None = None
    bedrock_secret_access_key: str | None = None
    bedrock_session_token: str | None = None
    bedrock_region: str = "us-east-1"

    # --- モデル設定 (extra も env_file もここに) ---
    model_config = SettingsConfigDict(
        env_file=".env.docker",
        extra="allow",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
