# app/agent/tools/convert_node.py
from langchain.tools import tool
from app.agent.tools import convert_to_csv, convert_to_json, convert_to_xml

@tool("convert_ru")
def convert_node(files: list[str], fmt: str) -> list[str]:
    """fmt = csv|json|xml で RU→変換ファイルのパスを返す"""
    from app.utils.ru_utils import ru_to_df
    import pandas as pd, uuid, os

    df = pd.concat([ru_to_df(f) for f in files], ignore_index=True)
    parsed = {"data": {"point_data": df.to_dict(orient="records")}}

    if fmt == "csv":
        out = convert_to_csv.convert_to_csv(parsed)
    elif fmt == "json":
        out = convert_to_json.convert_to_json(parsed)
    elif fmt == "xml":
        out = convert_to_xml.convert_to_xml(parsed)
    else:
        raise ValueError(f"未知のフォーマット: {fmt}")

    return [out] if isinstance(out, str) else out
