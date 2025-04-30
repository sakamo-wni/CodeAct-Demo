# tests/test_code_execution.py
import os
import json
import pandas as pd
from app.agent.tools.fallback_node import fallback_node
from app.agent.tools.ru_parser import parse_ru_file

def load_test_data():
    """テスト用のデータとマッピングをロード"""
    # RUデータをパース
    ru_file = "./tests/data/sample.ru"
    ru_data = parse_ru_file(ru_file)
    point_data = ru_data["data"]["point_data"]
    
    # variables_map.jsonをロード
    with open("./app/data/variables_map.json", "r") as f:
        variables_map = json.load(f)
    
    # point_dataをDataFrameに変換し、スケールを適用
    df = pd.DataFrame(point_data)
    for col in df.columns:
        if col in variables_map and "scale" in variables_map[col]:
            df[col] = df[col] * variables_map[col]["scale"]
    
    # time列が存在しないのでダミー列を追加
    if "time" not in df.columns:
        df["time"] = pd.date_range("2023-01-01", periods=len(df), freq="h")
    
    # location.jsonをRU形式でパース
    location_file = "./tests/data/441000205/location.json"
    location_data = parse_ru_file(location_file)
    location_points = location_data["data"]["point_data"]
    
    # GeoJSONデータを抽出
    geojson_key = '\x04\x1a{"type"'
    if not location_points or geojson_key not in location_points[0]:
        raise ValueError("Invalid location.json structure: GeoJSON data not found")
    
    geojson_str = location_points[0][geojson_key]
    # 不完全なJSONを補完
    complete_geojson_str = f'{{"type": {geojson_str}'
    try:
        geojson_data = json.loads(complete_geojson_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse GeoJSON from location.json: {str(e)}")
    
    features = geojson_data["features"]
    
    # LCLIDごとのlat, lonを抽出
    location_dict = {}
    for feature in features:
        lclid = feature["properties"]["LCLID"]
        coordinates = feature["geometry"]["coordinates"]  # [lon, lat, alt]
        location_dict[lclid] = {"lat": coordinates[1], "lon": coordinates[0]}
    
    # dfにlat, lonを追加
    if "LCLID" in df.columns:
        df["lat"] = df["LCLID"].map(lambda x: location_dict.get(x, {"lat": 0.0})["lat"])
        df["lon"] = df["LCLID"].map(lambda x: location_dict.get(x, {"lon": 0.0})["lon"])
    else:
        df["lat"] = 0.0
        df["lon"] = 0.0
    
    return df, variables_map

def test_code_execution_parquet():
    """Parquet変換のコード実行を検証"""
    df, _ = load_test_data()
    ctx = {"format": "parquet", "task_id": "test-123", "df": df}
    result = fallback_node(ctx)
    output_file = result["files"][0]
    assert os.path.exists(output_file), f"Parquet file {output_file} does not exist"
    assert output_file.endswith("result.parquet")
    result_df = pd.read_parquet(output_file)
    pd.testing.assert_frame_equal(result_df, df, check_like=True)

def test_code_execution_scatter():
    """散布図生成のコード実行を検証"""
    df, variables_map = load_test_data()
    ctx = {"chart": "scatter", "x": "time", "y": "AIRTMP", "task_id": "test-124", "df": df}
    ctx["variables_map"] = variables_map
    result = fallback_node(ctx)
    output_file = result["files"][0]
    assert os.path.exists(output_file), f"PNG file {output_file} does not exist"
    assert output_file.endswith("output.png")

def test_code_execution_csv():
    """CSV変換のコード実行を検証"""
    df, _ = load_test_data()
    ctx = {"format": "csv", "task_id": "test-126", "df": df}
    result = fallback_node(ctx)
    output_file = result["files"][0]
    assert os.path.exists(output_file), f"CSV file {output_file} does not exist"
    assert output_file.endswith("output.csv")
    result_df = pd.read_csv(output_file)
    pd.testing.assert_frame_equal(result_df, df, check_like=True)