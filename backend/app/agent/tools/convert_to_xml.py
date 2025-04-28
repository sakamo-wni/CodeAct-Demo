import xml.etree.ElementTree as ET
from xml.dom import minidom
import tempfile
import os
import time
from datetime import datetime

def convert_to_xml(parsed_data: dict) -> str:
    try:
        root = ET.Element("WeatherData")
        data = None
        if isinstance(parsed_data, dict):
            if "data" in parsed_data and "point_data" in parsed_data["data"]:
                data = parsed_data["data"]["point_data"]
            elif "point_data" in parsed_data:
                data = parsed_data["point_data"]
        
        if not data:
            return "❌ 変換可能なデータが見つかりません"
        
        metadata = ET.SubElement(root, "Metadata")
        ET.SubElement(metadata, "Format").text = "XML"
        ET.SubElement(metadata, "GeneratedAt").text = datetime.now().isoformat()
        
        points = ET.SubElement(root, "Points")
        for i, point in enumerate(data):
            if not isinstance(point, dict):
                continue
            point_elem = ET.SubElement(points, "Point")
            point_elem.set("id", str(i))
            for key, value in point.items():
                safe_key = key.replace(" ", "_").replace("&", "and").replace("<", "lt").replace(">", "gt")
                if isinstance(value, (dict, list)):
                    value = str(value)
                if value is None or value == "":
                    value = "None"
                try:
                    elem = ET.SubElement(point_elem, safe_key)
                    elem.text = str(value)
                except Exception as e:
                    with open("xml_error.log", "a") as f:
                        f.write(f"Error with key {safe_key}: {str(e)}\n")
        
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        tmp_dir = "tmp"
        os.makedirs(tmp_dir, exist_ok=True)
        output_path = os.path.join(tmp_dir, f"output_{int(time.time())}.xml")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
        return output_path
        
    except Exception as e:
        return f"❌ XML変換エラー: {str(e)}"