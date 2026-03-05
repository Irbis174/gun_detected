from fastapi import APIRouter
import httpx
import os
from ml.config import BACKEND_URL

router = APIRouter(tags=['status'])

@router.get('/health')
async def local_health():
    return {'service': 'ml', 'status': 'ok'}

@router.get('/health/deps')
async def deps_health():
    result = {'service': 'ml', 'status': 'ok', 'deps': {}}

    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            r = await client.get(f'{BACKEND_URL}/health')
            result['deps']['backend'] = {'status': 'ok' if r.status_code == 200 else 'bad', 'code': r.status_code}
    except Exception as e:
        result['deps']['backend'] = {'status': 'down', 'error': str(e)}
        result['status'] = 'degraded'

    return result