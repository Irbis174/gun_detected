from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI
from ml.status.status import router as status
from ml.inference.detect import router as predict_router


logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    stub_enabled = os.getenv('ML_ENABLE_STUB_DETECTION', '').lower() in {'1', 'true', 'yes'}
    if not stub_enabled:
        try:
            from ml.inference.yolo_model import load_model

            load_model()
        except Exception:
            os.environ['ML_ENABLE_STUB_DETECTION'] = '1'
            logger.exception('Failed to load YOLO model, falling back to stub detection.')
    yield

app = FastAPI(title = 'ML Service', lifespan=lifespan)

app.include_router(predict_router)
app.include_router(status)
