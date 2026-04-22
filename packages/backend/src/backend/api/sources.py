from fastapi import APIRouter, HTTPException, Request, Response

from backend.domain.input_source import InputSource
from backend.repositories.preview_frame_repository import preview_frame_repo
from backend.repositories.input_source_repository import source_repo
from backend.schemas.input_source import InputSourceCreate, InputSourceRead


router = APIRouter(tags=['sources'])


@router.post('/sources', response_model=InputSourceRead)
def create_new_source(data: InputSourceCreate):
    input_source = InputSource(0, data.name, data.source_type, data.source, False)
    source_repo.add(input_source)
    return source_repo.get(input_source.source_id)


@router.get('/sources', response_model=list[InputSourceRead])
def get_sources():
    return source_repo.list()


@router.get('/sources/{source_id}', response_model=InputSourceRead)
def get_source_id(source_id: int):
    source = source_repo.get(source_id)
    if source is None:
        raise HTTPException(404, f'Source not found: source_id = {source_id}')
    return source


@router.delete('/sources/{source_id}', response_model=InputSourceRead)
def delete_source(source_id: int):
    source = source_repo.delete(source_id)
    if source is None:
        raise HTTPException(404, f'Source not found: source_id = {source_id}')
    preview_frame_repo.clear(source_id)
    return source


@router.get('/sources/{source_id}/preview')
def get_source_preview(source_id: int):
    source = source_repo.get(source_id)
    if source is None:
        raise HTTPException(404, f'Source not found: source_id = {source_id}')

    frame_bytes = preview_frame_repo.get(source_id)
    if frame_bytes is None:
        return Response(status_code=204)

    return Response(content=frame_bytes, media_type='image/jpeg')


@router.post('/sources/{source_id}/preview')
async def update_source_preview(source_id: int, request: Request):
    source = source_repo.get(source_id)
    if source is None:
        raise HTTPException(404, f'Source not found: source_id = {source_id}')

    frame_bytes = await request.body()
    if not frame_bytes:
        return Response(status_code=204)

    preview_frame_repo.set(source_id, frame_bytes)
    return Response(status_code=204)
