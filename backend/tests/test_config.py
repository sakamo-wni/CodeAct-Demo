from app.config import get_settings

def test_env_loaded():
    s = get_settings()
    # .env.docker に必ず定義している変数だけチェック
    assert s.s3_bucket == "wni-wfc-stock-ane1"
