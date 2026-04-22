import os
from pathlib import Path

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+psycopg://diploma:diploma@localhost:5433/diploma',
)
AUTO_CREATE_TABLES = os.getenv('AUTO_CREATE_TABLES', '0').strip().lower() not in {
    '0',
    'false',
    'no',
}
ML_URL = os.getenv('ML_URL', 'http://localhost:8000')
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
DETECTION_FRAMES_DIR = Path(
    os.getenv('DETECTION_FRAMES_DIR') or _BACKEND_ROOT / 'var' / 'detection_frames'
)

# class Settings():
#     pass
