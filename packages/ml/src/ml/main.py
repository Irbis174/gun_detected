from fastapi import FastAPI
from health.status import router as status
from ml.inference.detect import router as predict_router

app = FastAPI(title = 'ML Service')

app.include_router(predict_router)
app.include_router(status)
