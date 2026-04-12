import datetime

from fastapi import APIRouter

from backend.domain.tracking_update import TrackingUpdate
from backend.repositories.tracking_update_repository import tracking_update_repo
from backend.schemas.tracking_update import TrackingUpdateCreate, TrackingUpdateRead

router = APIRouter(tags=['tracking-updates'])


@router.post('/tracking-updates', response_model=TrackingUpdateRead)
def create_tracking_update(data: TrackingUpdateCreate):
    update = TrackingUpdate(
        update_id=0,
        test_run_id=data.test_run_id,
        detection_id=data.detection_id,
        frame_index=data.frame_index,
        frame_ts=data.frame_ts,
        label=data.label,
        score=data.score,
        bbox=data.bbox,
        track_id=data.track_id,
        received_at=datetime.datetime.now(),
    )
    return tracking_update_repo.add(update)


@router.get('/tracking-updates', response_model=list[TrackingUpdateRead])
def get_tracking_updates(test_run_id: int | None = None):
    if test_run_id is None:
        return tracking_update_repo.list_all()
    return tracking_update_repo.list_by_test_run_id(test_run_id)


@router.get('/tracking-updates/latest', response_model=list[TrackingUpdateRead])
def get_latest_tracking_updates():
    return tracking_update_repo.latest()
