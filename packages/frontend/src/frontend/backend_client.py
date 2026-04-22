from __future__ import annotations

from typing import Any

import requests

from frontend.config import BACKEND_URL
from frontend.i18n import translate_backend_detail


class BackendClientError(RuntimeError):
    pass


class BackendClient:
    def __init__(self, base_url: str = BACKEND_URL, timeout_seconds: float = 5.0):
        self.base_url = base_url.rstrip('/')
        self.timeout_seconds = timeout_seconds
        self._session = requests.Session()

    def list_sources(self) -> list[dict[str, Any]]:
        return self._request('GET', '/sources')

    def create_source(self, *, name: str, source_type: str, source: str) -> dict[str, Any]:
        return self._request(
            'POST',
            '/sources',
            json={
                'name': name,
                'source_type': source_type,
                'source': source,
            },
        )

    def delete_source(self, *, source_id: int) -> dict[str, Any]:
        return self._request(
            'DELETE',
            f'/sources/{source_id}',
        )

    def create_test_run(self, *, source_id: int) -> dict[str, Any]:
        return self._request(
            'POST',
            '/test-runs',
            json={'source_id': source_id},
        )

    def execute_test_run(self, *, test_run_id: int, sample_every: int = 1) -> dict[str, Any]:
        return self._request(
            'POST',
            f'/test-runs/{test_run_id}/execute',
            params={'sample_every': sample_every},
        )

    def stop_test_run(self, *, test_run_id: int) -> dict[str, Any]:
        return self._request(
            'POST',
            f'/test-runs/{test_run_id}/stop',
        )

    def get_test_run(self, *, test_run_id: int) -> dict[str, Any]:
        return self._request('GET', f'/test-runs/{test_run_id}')

    def get_test_run_detections(self, *, test_run_id: int) -> list[dict[str, Any]]:
        return self._request('GET', f'/test-runs/{test_run_id}/detections')

    def get_tracking_updates(
        self,
        *,
        test_run_id: int | None = None,
        latest_only: bool = False,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if test_run_id is not None:
            params['test_run_id'] = test_run_id
        path = '/tracking-updates/latest' if latest_only else '/tracking-updates'
        return self._request('GET', path, params=params)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        timeout = kwargs.pop('timeout', self.timeout_seconds)
        url = f'{self.base_url}{path}'

        try:
            response = self._session.request(method=method, url=url, timeout=timeout, **kwargs)
        except requests.RequestException as error:
            raise BackendClientError(f'Не удалось подключиться к backend: {error}') from error

        if not response.ok:
            detail: str
            try:
                detail_payload = response.json()
                detail = str(detail_payload)
            except ValueError:
                detail = response.text.strip() or 'backend returned an error'
            detail = translate_backend_detail(detail)
            raise BackendClientError(
                f'Backend вернул {response.status_code}: {detail}'
            )

        if not response.content:
            return None

        try:
            return response.json()
        except ValueError as error:
            raise BackendClientError('Backend вернул ответ не в формате JSON') from error
