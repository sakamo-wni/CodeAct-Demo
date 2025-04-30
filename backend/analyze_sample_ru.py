# analyze_sample_ru.py
import json
from app.agent.tools.ru_parser import parse_ru_file

def analyze_sample_ru():
    """sample.ruの内容を解析して必要な情報を出力"""
    ru_file = "./tests/data/sample.ru"
    
    try:
        # RUファイルをパース
        ru_data = parse_ru_file(ru_file)
        point_data = ru_data["data"]["point_data"]
        
        # 1. point_dataの最初の1-2要素
        print("=== point_data の最初の1-2要素 ===")
        for i, point in enumerate(point_data[:2]):
            print(f"ポイント {i + 1}: {point}")
        
        # 2. 含まれる列名
        if point_data:
            columns = list(point_data[0].keys())
            print("\n=== 含まれる列名 ===")
            print(columns)
        
        # 3. time列の形式
        print("\n=== time 列の情報 ===")
        if "time" in columns:
            time_values = [point["time"] for point in point_data[:2]]
            print("time 列の値（最初の2つ）:", time_values)
            print("time 列の型（最初の値）:", type(time_values[0]).__name__)
        else:
            print("time 列は存在しません")
        
        # 4. LCLID列の存在と値
        print("\n=== LCLID 列の情報 ===")
        if "LCLID" in columns:
            lclid_values = [point["LCLID"] for point in point_data]
            unique_lclids = set(lclid_values)
            print("LCLID 列の値（すべて）:", lclid_values)
            print("ユニークな LCLID の数:", len(unique_lclids))
            print("ユニークな LCLID の値:", list(unique_lclids))
        else:
            print("LCLID 列は存在しません")
        
    except Exception as e:
        print("エラー:", str(e))

if __name__ == "__main__":
    analyze_sample_ru()