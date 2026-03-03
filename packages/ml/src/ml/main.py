from fastapi import FastAPI
from ml.status import router as get_health
from ml.detect import router as predict_router

app = FastAPI(title = 'ML Service')

app.include_router(predict_router)
app.include_router(get_health)
