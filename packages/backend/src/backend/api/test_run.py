from fastapi import APIRouter, HTTPException
from backend.domain.test_run import TestRun
from backend.schemas.test_run import TestRunCreate, TestRunRead
from backend.repositories.input_source_repository import source_repo
from backend.repositories.test_run_repository import test_run_repo

router = APIRouter(tags = ['test-runs'])

@router.post('/test-runs', response_model=TestRunRead)
def create_test_run(data: TestRunCreate):
    source = source_repo.get(data.source_id)
    if source is None:
        raise HTTPException(404, f'Не найден source_id = {data.source_id}')
    else:
        test_run = TestRun(0, source_id=data.source_id,status='created',started_at=None,finished_at=None,processed_frames=0,detections_count=0)
        test_run_repo.add(test_run)
        return test_run
        

@router.get('/test-runs', response_model=list[TestRunRead])
def get_test_runs():
    return test_run_repo.list()


@router.get('/test-runs/{test_run_id}', response_model=TestRunRead)
def get_test_run(test_run_id: int):
    test_run = test_run_repo.get(test_run_id)
    if test_run is None:
        raise HTTPException(
            404, f'Не найден test_run_id = {test_run_id}',)
    return test_run