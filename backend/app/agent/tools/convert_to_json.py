import json
import tempfile
import os
import time
from datetime import datetime

def convert_to_json(parsed_data: dict) -> str:
    try:
        data = None
        if isinstance(parsed_data, dict):
            if "data" in parsed_data and "point_data" in parsed_data["data"]:
                data = parsed_data["data"]["point_data"]
            elif "point_data" in parsed_data:
                data = parsed_data["point_data"]
            else:
                data = parsed_data
        
        if not data:
            return "❌ 変換可能なデータが見つかりません"
        
        output_data = {
            "data": data,
            "metadata": {
                "format": "JSON",
                "generated_at": datetime.now().isoformat()
            }
        }
        
        tmp_dir = "tmp"
        os.makedirs(tmp_dir, exist_ok=True)
        output_path = os.path.join(tmp_dir, f"output_{int(time.time())}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        return output_path
        
    except Exception as e:
        return f"❌ JSON変換エラー: {str(e)}"