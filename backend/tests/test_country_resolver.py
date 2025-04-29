# backend/tests/test_country_resolver.py
from app.utils.country_resolver import resolve_country_name, find_tag_ids_by_country

def test_country_resolver(monkeypatch):
    # Claude 呼び出しをモック
    monkeypatch.setattr(
        "app.utils.country_resolver.invoke_claude", lambda prompt: "Netherlands"
    )

    name = resolve_country_name("ねざーらんど")
    assert name == "Netherlands"

    tags = find_tag_ids_by_country(name)
    # metadata.json 内に 1 件以上ある想定
    assert tags and isinstance(tags[0], str)
