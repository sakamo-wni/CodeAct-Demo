# backend/tests/conftest.py
from pathlib import Path
import pytest

TEST_ROOT = Path(__file__).parent

@pytest.fixture
def sample_obs_ru() -> Path:
    """gzip 観測データ RU ファイル"""
    return TEST_ROOT / "data" / "sample.ru"
