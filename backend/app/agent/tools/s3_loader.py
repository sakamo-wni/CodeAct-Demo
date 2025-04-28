import boto3
from datetime import datetime, timedelta
import os
import re

async def load_from_s3(bucket: str, prefix: str, start_dt: datetime, end_dt: datetime = None) -> list:
    """
    S3からファイルをロードする関数
    ファイルはyyyymmddHHMMSS.{uuid}の形式で保存されている
    """
    s3 = boto3.client('s3')
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        if "Contents" not in response:
            return [f"Error: No files found in {bucket}/{prefix}"]

        files = []
        # 日時形式のパターン（yyyymmddHHMMSS）
        datetime_pattern = re.compile(r'^(\d{14})')
        
        for obj in response["Contents"]:
            key = obj["Key"]
            filename = key.split("/")[-1]
            
            # ファイル名から日時を抽出（例: 20250417195848.ea2008d2-4ae4-4e3f-a5ec-cb80beec37a4）
            dt_match = datetime_pattern.match(filename)
            if not dt_match:
                continue
                
            dt_str = dt_match.group(1)
            try:
                file_dt = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
                
                # 時間範囲が指定されている場合
                if end_dt:
                    if start_dt <= file_dt <= end_dt:
                        local_path = f"tmp/{filename}"
                        os.makedirs("tmp", exist_ok=True)
                        s3.download_file(bucket, key, local_path)
                        files.append(local_path)
                # 単一時刻の場合、最も近い時刻のファイルを選択
                else:
                    time_diff = abs((file_dt - start_dt).total_seconds())
                    # 30分以内のファイルなら追加
                    if time_diff < 1800:  
                        local_path = f"tmp/{filename}"
                        os.makedirs("tmp", exist_ok=True)
                        s3.download_file(bucket, key, local_path)
                        files.append(local_path)
                        # 30分以内で最も近いファイルが見つかったら終了
                        break
            except ValueError:
                continue
                
        return files if files else ["Error: No matching files"]
        
    except Exception as e:
        return [f"Error loading from S3: {str(e)}"]