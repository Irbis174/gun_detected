from fastapi import APIRouter, HTTPException
from backend.domain.input_source import InputSource
from backend.schemas.input_source import InputSourceCreate, InputSourceRead
from backend.repositories.input_source_repository import source_repo


router = APIRouter(tags=['sources'])


@router.post('/sources', response_model=InputSourceRead)
def create_new_source(data: InputSourceCreate):
    input_source = InputSource(0, data.name, data.source_type, data.source, False)
    source_repo.add(input_source)
    return source_repo.get(input_source.source_id)


@router.get('/sources', response_model=list[InputSourceRead])
def get_sources():
    return source_repo.list()


@router.get(
    '/sources/{source_id}',
    response_model=InputSourceRead,
)
def get_source_id(source_id: int):
    source = source_repo.get(source_id)
    if source:
        return source
    else:
        raise HTTPException(404, f'Не найден source_id = {source_id}')
