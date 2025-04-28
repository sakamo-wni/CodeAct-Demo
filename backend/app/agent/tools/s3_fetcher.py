# backend/app/agent/tools/s3_fetcher.py
from typing import ClassVar, List
from datetime import datetime
from langchain.tools import BaseTool
from .s3_loader import load_from_s3
from app.config import get_settings

settings = get_settings()


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
