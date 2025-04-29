# app/utils/country_resolver.py
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from app.models.bedrock_client import invoke_claude

BASE_DIR = Path(__file__).resolve().parents[2]
META_PATH = BASE_DIR / "app" / "data" / "metadata.json"

# ------------------------------------------------
# 1) 表記ゆらぎ → ISO 英語正式名
# ------------------------------------------------
def resolve_country_name(raw: str) -> str:
    """
    例:
      「ねざーらんど」,「オランダ」 → Netherlands
      「独」,「Germany」 → Germany
    Claude 3 Sonnet に 1 クエリ投げるだけなので低コスト。
    """
    prompt = (
        "次の国名を、ISO 英語正式名称（例: Netherlands, Germany）の 1 単語で返して下さい。\n"
        f"国名: {raw}"
    )
    return invoke_claude(prompt).strip()

# ------------------------------------------------
# 2) country → TagID 一覧
# ------------------------------------------------
def find_tag_ids_by_country(country: str) -> List[str]:
    """
    metadata.json から一致 (大小無視) する TagID を返す。
    """
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    norm = country.casefold()
    return [rec["TagID"] for rec in meta if rec["country"].casefold() == norm]
