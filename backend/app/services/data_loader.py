# backend/app/services/data_loader.py
from pathlib import Path
import json
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache
def load_metadata() -> list[dict]:
    with open(BASE_DIR / "metadata.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_variable_map() -> dict:
    with open(BASE_DIR / "variables_map.json", encoding="utf-8") as f:
        return json.load(f)


def find_by_tag(tag_id: str) -> dict | None:
    """TagID でメタデータを 1 件取得（無ければ None）"""
    return next((row for row in load_metadata() if row["tag_id"] == tag_id), None)
