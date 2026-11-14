import os
from typing import Any

import requests


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class SessionExpired(ApiError):
    pass


class ApiClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("BACKEND_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.token = token

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=json,
                headers=headers,
                timeout=15,
            )
        except requests.RequestException as exc:
            raise ApiError(0, "The backend is unavailable. Check that FastAPI is running.") from exc

        if response.status_code == 401:
            raise SessionExpired(401, "Your session has expired. Please sign in again.")
        if not response.ok:
            try:
                body = response.json()
                detail = body.get("detail", "The backend returned an error.")
            except ValueError:
                detail = "The backend returned an error."
            raise ApiError(response.status_code, str(detail))
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, *, json: dict[str, Any] | None = None) -> Any:
        return self.request("POST", path, json=json)

    def patch(self, path: str, *, json: dict[str, Any] | None = None) -> Any:
        return self.request("PATCH", path, json=json)


def get_api_client() -> ApiClient:
    import streamlit as st

    return ApiClient(token=st.session_state.get("access_token"))
