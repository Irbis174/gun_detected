from fastapi import  APIRouter
import os
import httpx
from backend.config import ML_URL

router = APIRouter(tags=['status'])

@router.get('/health')
async def local_health():
    return {'service': 'backend', 'status': 'ok'}

@router.get('/health/deps')
async def deps_health():
    result = await check_ml_health()
    return result

async def check_ml_health():
    result = {'service': 'backend', 'status': 'ok', 'deps': {}}
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            r = await client.get(f'{ML_URL}/health')
            result['deps']['ml'] = {'status': 'ok' if r.status_code == 200 else 'bad', 'code': r.status_code}
    except Exception as e:
        result['deps']['ml'] = {'status': 'down', 'error': str(e)}
        result['status'] = 'degraded'

    return result