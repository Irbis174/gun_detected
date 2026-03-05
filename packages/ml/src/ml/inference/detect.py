from fastapi import APIRouter, UploadFile, File, HTTPException

import numpy as np
from PIL import Image
from io import BytesIO
import os

router = APIRouter(prefix='/predict', tags=['predict'])

@router.post('/image')
async def predict_image(file: UploadFile = File(...)):
    content = await file.read()
    image, meta = decode_image(file.filename, content)
    detections, processing_ms = run_inference(image)
    return build_response(meta, detections, processing_ms)

def decode_image(filename: str, content: bytes) -> tuple[np.ndarray, dict]:
    file_extension = os.path.splitext(filename)[1].lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png']

    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail='Недопустимый формат файла')
    try:
        img = Image.open(BytesIO(content))
    except:
        raise HTTPException(status_code=400, detail='Файл не является корректным изображением')
    img = img.convert('RGB')
    width, height = img.size
    img_arr = np.array(img)

    return (img_arr, {'file_extension': file_extension, 'width': width, 'height': height})


def run_inference(image: np.ndarray) -> tuple[list[dict], float]:
    detections = [
        {
            'class_name': 'dangerous_object',
            'confidence': 0.93,
            'bbox': [10, 20, 100, 200],
        }
    ]
    processing_ms = 12.5

    return detections, processing_ms

def build_response(meta: dict, detections: list[dict], processing_ms: float) -> dict:
    return {
        'filename': meta.get('filename'),
        'width': meta['width'],
        'height': meta['height'],
        'file_extension': meta.get('file_extension'),
        'detections': detections,
        'processing_ms': processing_ms,
    }