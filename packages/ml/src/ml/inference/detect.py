from __future__ import annotations

from io import BytesIO
import os
from time import perf_counter
from typing import TypedDict

from fastapi import APIRouter, File, HTTPException, UploadFile
import numpy as np
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from ml.config import ML_DEVICE
from ml.inference.yolo_model import get_model

router = APIRouter(prefix='/predict', tags=['predict'])

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
BBox = tuple[int, int, int, int]


class ImageMeta(TypedDict):
    filename: str
    file_extension: str
    width: int
    height: int


class Detection(BaseModel):
    label: str
    score: float = Field(ge=0.0, le=1.0)
    bbox: BBox = Field(
        description='Bounding box in pixels as (x, y, w, h).',
    )


class PredictImageResponse(BaseModel):
    filename: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    file_extension: str
    detections: list[Detection]
    processing_ms: float = Field(ge=0.0)


@router.post('/image', response_model=PredictImageResponse)
async def predict_image(file: UploadFile = File(...)) -> PredictImageResponse:
    content = await file.read()
    image, meta = decode_image(file.filename, content)
    detections_result = run_inference(image)
    return build_response(meta, detections_result)


def decode_image(filename: str | None, content: bytes) -> tuple[np.ndarray, ImageMeta]:
    if not filename:
        raise HTTPException(status_code=400, detail='Имя файла не передано')

    file_extension = os.path.splitext(filename)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail='Недопустимый формат файла')

    try:
        img = Image.open(BytesIO(content))
        img.load()
    except UnidentifiedImageError as error:
        raise HTTPException(
            status_code=400,
            detail='Файл не является корректным изображением',
        ) from error

    img = img.convert('RGB')
    width, height = img.size
    image_array = np.array(img)

    return image_array, ImageMeta(
        filename=filename,
        file_extension=file_extension,
        width=width,
        height=height,
    )


def run_inference(image: np.ndarray) -> tuple[list[Detection], float]:
    started_at = perf_counter()
    detections: list[Detection] = []

    model = get_model()
    results = model.predict(
        source=image,
        verbose=False,
        conf=0.25,
        device=ML_DEVICE,
    )

    processing_ms = (perf_counter() - started_at) * 1000

    result = results[0]
    for box in result.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        bbox = (x1, y1, x2 - x1, y2 - y1)

        score = float(box.conf[0].item())
        class_id = int(box.cls[0].item())
        label = result.names[class_id]

        detections.append(
            Detection(
                label=label,
                score=score,
                bbox=bbox,
            )
        )

    return detections, processing_ms

def build_response(
    meta: ImageMeta,
    detections_result: tuple[list[Detection], float],
) -> PredictImageResponse:
    detections, processing_ms = detections_result

    return PredictImageResponse(
        filename=meta['filename'],
        width=meta['width'],
        height=meta['height'],
        file_extension=meta['file_extension'],
        detections=detections,
        processing_ms=processing_ms,
    )
