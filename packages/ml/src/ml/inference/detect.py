from fastapi import APIRouter, UploadFile, File, HTTPException
from dataclasses import dataclass
import numpy as np
from PIL import Image
from io import BytesIO
import os

router = APIRouter(prefix='/predict', tags=['predict'])

@dataclass
class Detection:
    label: str
    score: float
    bbox: tuple[int, int, int, int]


@router.post('/image')
async def predict_image(file: UploadFile = File(...)):
    content = await file.read()
    image, meta = decode_image(file.filename, content)
    detections = run_inference(image)
    return build_response(meta, detections)

def decode_image(filename: str, content: bytes) -> tuple[np.ndarray, dict]:
    file_extension = os.path.splitext(filename)[1].lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png']

    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail='Недопустимый формат файла')
    try:
        img = Image.open(BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail='Файл не является корректным изображением')
    img = img.convert('RGB')
    width, height = img.size
    img_arr = np.array(img)

    return (img_arr, {'filename': filename, 'file_extension': file_extension, 'width': width, 'height': height})


def run_inference(image: np.ndarray) -> tuple[list[Detection], float]:
    detections = [Detection(
            label = 'danger',
            score = 0.5,
            bbox = (100, 200, 150, 250),
    )]

    processing_ms = 12.5
    return detections, processing_ms

def build_response(meta: dict, detections_result: tuple[list[Detection], float]) -> dict:
    detections, processing_ms = detections_result

    return {
        'filename': meta.get('filename'),
        'width': meta['width'],
        'height': meta['height'],
        'file_extension': meta.get('file_extension'),
        'detections': detections,
        'processing_ms': processing_ms,
    }