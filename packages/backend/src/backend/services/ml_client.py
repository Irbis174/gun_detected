from __future__ import annotations

import mimetypes

import httpx
from pydantic import BaseModel, Field, ValidationError

from backend.config import ML_URL
from backend.status.status import check_ml_health

import asyncio

BBox = tuple[int, int, int, int]


class MLClientError(RuntimeError):
    pass


class MLDetection(BaseModel):
    label: str
    score: float = Field(ge=0.0, le=1.0)
    bbox: BBox


class MLPredictImageResponse(BaseModel):
    filename: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    file_extension: str
    detections: list[MLDetection]
    processing_ms: float = Field(ge=0.0)


class MLClient:
    def __init__(self, base_url: str = ML_URL, timeout_seconds: float = 10.0):
        self.base_url = base_url.rstrip('/')
        self.timeout_seconds = timeout_seconds
        self._client: httpx.AsyncClient | None = None

    async def check_status(self) -> dict:
        return await check_ml_health()

    async def predict_image(
        self,
        *,
        filename: str,
        content: bytes,
    ) -> MLPredictImageResponse:
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        files = {'file': (filename, content, content_type)}
        client = self._get_client()

        try:
            response = await client.post(
                f'{self.base_url}/predict/image',
                files=files,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            detail = error.response.text.strip() or 'ML service returned an error'
            raise MLClientError(
                f'ML service returned {error.response.status_code}: {detail}'
            ) from error
        except httpx.RequestError as error:
            raise MLClientError(f'Could not reach ML service: {error}') from error

        try:
            payload = response.json()
        except ValueError as error:
            raise MLClientError('ML service returned non-JSON response') from error

        try:
            return MLPredictImageResponse.model_validate(payload)
        except ValidationError as error:
            raise MLClientError('ML service returned invalid response schema') from error

    async def run_tracking(
        self,
        *,
        source: str,
        source_id: int,
        test_run_id: int,
        detection_id: int,
        frame_index: int,
        frame_ts: float,
        bbox: BBox,
        label: str,
    ) -> dict:
        client = self._get_client()
        payload = {
            'source': source,
            'source_id': source_id,
            'test_run_id': test_run_id,
            'detection_id': detection_id,
            'frame_index': frame_index,
            'frame_ts': frame_ts,
            'bbox': list(bbox),
            'label': label,
        }

        try:
            response = await client.post(
                f'{self.base_url}/inference/stream',
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            detail = error.response.text.strip() or 'ML service returned an error'
            raise MLClientError(
                f'ML service returned {error.response.status_code}: {detail}'
            ) from error
        except httpx.RequestError as error:
            raise MLClientError(f'Could not reach ML service: {error}') from error

        return response.json()

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout_seconds,
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                ),
            )
        return self._client

    
ml_client = MLClient()
