from fastapi import FastAPI
from backend.config import AUTO_CREATE_TABLES
from backend.db.session import init_db
from backend.api.detections import router as detections
from backend.status.status import router as status
from backend.api.sources import router as source
from backend.api.test_run import router as test_run
from backend.api.tracking_updates import router as tracking_updates

app = FastAPI(title = 'Backend')


@app.on_event('startup')
def startup() -> None:
    if AUTO_CREATE_TABLES:
        init_db()

app.include_router(status)
app.include_router(source)
app.include_router(test_run)
app.include_router(detections)
app.include_router(tracking_updates)
