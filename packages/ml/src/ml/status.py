from fastapi import APIRouter
router = APIRouter(prefix='/status', tags=['status'])

@router.get('/health')
async def get_health():
    return {'service': 'ml', 'status': 'ok'}