import pandas as pd
import tempfile
import os
import time

def convert_to_csv(parsed_data: dict) -> str:
    try:
        data = None
        if isinstance(parsed_data, dict):
            if "data" in parsed_data and "point_data" in parsed_data["data"]:
                data = parsed_data["data"]["point_data"]
            elif "point_data" in parsed_data:
                data = parsed_data["point_data"]
        
        if not data:
            return "❌ 変換可能なデータが見つかりません"
        
        df = pd.DataFrame(data)
        tmp_dir = "tmp"
        os.makedirs(tmp_dir, exist_ok=True)
        output_path = os.path.join(tmp_dir, f"output_{int(time.time())}.csv")
        df.to_csv(output_path, index=False)
        return output_path
        
    except Exception as e:
        return f"❌ CSV変換エラー: {str(e)}"