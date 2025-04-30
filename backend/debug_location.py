# debug_location.py
from app.agent.tools.ru_parser import parse_ru_file

def debug_location():
    """location.jsonのpoint_dataの構造を出力"""
    location_file = "./tests/data/441000205/location.json"
    try:
        location_data = parse_ru_file(location_file)
        point_data = location_data["data"]["point_data"]
        print("=== location.json の point_data 構造 ===")
        for i, point in enumerate(point_data[:2]):  # 最初の2要素
            print(f"ポイント {i + 1}: {point}")
        print("\n=== point_data のキー ===")
        if point_data:
            print(list(point_data[0].keys()))
    except Exception as e:
        print("エラー:", str(e))

if __name__ == "__main__":
    debug_location()