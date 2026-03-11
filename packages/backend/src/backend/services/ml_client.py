import datetime
from backend.status.status import check_ml_health
import httpx
from backend.domain.detection_event import DetectionEvent
from backend.config import ML_URL
import requests

class MLClient:
    async def _check_status(self):
        return await check_ml_health()

    def _anylyze_image(self, filename: str):
        anylyze = requests.post(f'{ML_URL}/image/{filename}')
        return anylyze