from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

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
        raise HTTPException(
            404,
            f'Detection not found: detection_id = {detection_id}',
        )
    return detection


@router.get('/detections/{detection_id}/frame')
def get_detection_frame(detection_id: int):
    detection = detection_repo.get(detection_id)
    if detection is None:
        raise HTTPException(
            404,
            f'Detection not found: detection_id = {detection_id}',
        )

    if detection.frame_path is None:
        raise HTTPException(
            404,
            f'Frame not saved for detection_id = {detection_id}',
        )

    frame_path = Path(detection.frame_path)
    if not frame_path.is_file():
        raise HTTPException(
            404,
            f'Frame file not found for detection_id = {detection_id}',
        )

    return FileResponse(
        frame_path,
        media_type='image/jpeg',
        filename=frame_path.name,
    )
