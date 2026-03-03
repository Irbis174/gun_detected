from fastapi import  APIRouter
import requests

router = APIRouter(prefix='/status', tags=['status'])

@router.get('/health')
def get_health():
    return requests.get('http://localhost:8000/status/health').json()