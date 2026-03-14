from fastapi import FastAPI
from backend.status.status import router as status
from backend.api.sources import router as source
from backend.api.test_run import router as test_run

app = FastAPI(title = 'Backend')

app.include_router(status)
app.include_router(source)
app.include_router(test_run)

