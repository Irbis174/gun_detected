from fastapi import APIRouter, HTTPException

from backend.domain.test_run import TestRun
from backend.repositories.detection_event_repository import detection_repo
from backend.repositories.input_source_repository import source_repo
from backend.repositories.test_run_repository import test_run_repo
from backend.schemas.detection import DetectionRead
from backend.schemas.test_run import TestRunCreate, TestRunRead
from backend.services.video_test_runner import VideoTestRunner


router = APIRouter(tags=['test-runs'])


@router.post('/test-runs', response_model=TestRunRead)
def create_test_run(data: TestRunCreate):
    source = source_repo.get(data.source_id)
    if source is None:
        raise HTTPException(404, f'Не найден source_id = {data.source_id}')

    test_run = TestRun(
        0,
        source_id=data.source_id,
        status='created',
        started_at=None,
        finished_at=None,
        processed_frames=0,
        detections_count=0,
    )
    test_run_repo.add(test_run)
    return test_run


@router.get('/test-runs', response_model=list[TestRunRead])
def get_test_runs():
    return test_run_repo.list()


@router.get('/test-runs/{test_run_id}', response_model=TestRunRead)
def get_test_run(test_run_id: int):
    test_run = test_run_repo.get(test_run_id)
    if test_run is None:
        raise HTTPException(404, f'Не найден test_run_id = {test_run_id}')
    return test_run


@router.post('/test-runs/{test_run_id}/execute', response_model=TestRunRead)
async def execute_test_run(test_run_id: int, sample_every: int = 5):
    test_run = test_run_repo.get(test_run_id)
    if test_run is None:
        raise HTTPException(404, f'Не найден test_run_id = {test_run_id}')

    if sample_every <= 0:
        raise HTTPException(400, 'sample_every must be greater than 0')

    if test_run.status == 'running':
        raise HTTPException(409, 'Test run is already running')

    if test_run.status != 'created':
        raise HTTPException(
            409,
            'Only test runs with status "created" can be executed',
        )

    runner = VideoTestRunner(sample_every=sample_every)

    try:
        await runner.run(test_run_id)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error

    return test_run


@router.get('/test-runs/{test_run_id}/detections', response_model=list[DetectionRead])
def get_test_run_detections(test_run_id: int):
    test_run = test_run_repo.get(test_run_id)
    if test_run is None:
        raise HTTPException(404, f'Не найден test_run_id = {test_run_id}')

    return detection_repo.list_by_test_run_id(test_run_id)
