from fastapi import FastAPI
from backend.status.status import router as status

app = FastAPI(title = 'Backend')

app.include_router(status)


