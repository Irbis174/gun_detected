from fastapi import APIRouter, HTTPException

from backend.repositories.detection_event_repository import detection_repo
from backend.schemas.detection import DetectionRead


router = APIRouter(tags=['detections'])


@router.get('/detections', response_model=list[DetectionRead])
def get_detections():
    return detection_repo.list_all()


@router.get('/detections/{detection_id}', response_model=DetectionRead)
def get_detection(detection_id: int):
    detection = detection_repo.get(detection_id)
    if detection is None:
        raise HTTPException(404, f'Не найдена detection_id = {detection_id}')
    return detection
