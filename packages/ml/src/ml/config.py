import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / '.env'

load_dotenv(ENV_PATH)

BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8001')

dataset_root_raw = os.getenv('ML_DATASET_ROOT')
if not dataset_root_raw:
    raise ValueError(
        f'Не задана переменная ML_DATASET_ROOT. Проверь файл: {ENV_PATH}'
    )

DATASET_ROOT = dataset_root_raw

DEFAULT_MODEL_PATH = BASE_DIR / 'src' / 'ml' / 'inference' / 'models' / 'detect' / 'train-2' / 'weights' / 'best.pt'
MODEL_PATH = os.getenv('MODEL_PATH', str(DEFAULT_MODEL_PATH))
DEFAULT_TRACKER_CONFIG_PATH = BASE_DIR / 'src' / 'ml' / 'inference' / 'trackers' / 'bytetrack_stable.yaml'
TRACKER_CONFIG_PATH = os.getenv('TRACKER_CONFIG_PATH', str(DEFAULT_TRACKER_CONFIG_PATH))
ML_DEVICE = os.getenv('ML_DEVICE', 'cuda')
