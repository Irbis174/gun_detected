from backend.camera import router 
from fastapi import FastAPI

app = FastAPI()

app.include_router(router, prefix='/video')
