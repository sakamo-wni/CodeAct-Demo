# backend/app/agent/tools/s3_fetcher.py
from typing import ClassVar, List
from datetime import datetime
from langchain.tools import BaseTool
from .s3_loader import load_from_s3
from app.config import get_settings
from pathlib import Path, PurePosixPath
import json, botocore, boto3

settings = get_settings()

BASE_DIR = Path(__file__).resolve().parents[2]

def download_location_json(bucket: str, key: str) -> dict:
    """
    location_metadata の JSON を取得して dict を返す。
    1) backend/app/data/{key} に存在すればローカルを使用
    2) 無ければ S3 からダウンロード
    """
    local = BASE_DIR / "app" / "data" / key
    if local.exists():
        return json.loads(local.read_text(encoding="utf-8"))

    s3 = boto3.client("s3")
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        return json.load(obj["Body"])
    except botocore.exceptions.ClientError as e:
        raise RuntimeError(f"S3 から location JSON を取得できません: s3://{bucket}/{key}") from e

class LoadRuFilesTool(BaseTool):
    """指定した TagID・日時範囲の ru ファイルを S3 からダウンロードする"""

    name: ClassVar[str] = "load_ru_files"
    description: ClassVar[str] = (
        "Args: tag_id(str), start_dt('YYYY-MM-DD HH:MM:SS'), "
        "end_dt(str, optional)。指定範囲の ru ファイルを S3 から取得する。"
    )

    # ---- 同期用 ---------------------------------------------------
    def _run(self, **kwargs) -> List[str]:
        import asyncio
        return asyncio.run(self._arun(**kwargs))

    # ---- 非同期用 -------------------------------------------------
    async def _arun(self, tag_id: str, start_dt: str, end_dt: str | None = None) -> List[str]:
        start = datetime.fromisoformat(start_dt)
        end = datetime.fromisoformat(end_dt) if end_dt else None

        prefix = f"{tag_id}/{start.year:04d}/{start.month:02d}/{start.day:02d}/"

        return await load_from_s3(
            bucket=settings.s3_bucket,
            prefix=prefix,
            start_dt=start,
            end_dt=end,
        )
