from fastapi import FastAPI
from backend.status import router as get_health

app = FastAPI(title = 'Backend')

app.include_router(get_health)


