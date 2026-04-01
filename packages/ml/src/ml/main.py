from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from ml.status.status import router as status
from ml.inference.detect import router as predict_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    stub_enabled = os.getenv('ML_ENABLE_STUB_DETECTION', '').lower() in {'1', 'true', 'yes'}
    if not stub_enabled:
        from ml.inference.yolo_model import load_model

        load_model()
    yield

app = FastAPI(title = 'ML Service', lifespan=lifespan)

app.include_router(predict_router)
app.include_router(status)
