# desktop/request_helper.py
import requests
from typing import Optional, Dict, Any

DEFAULT_TIMEOUT = 15  # seconds

class RequestHelper:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def set_token(self, token: Optional[str]):
        self.token = token

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Token {self.token}"
        if extra:
            h.update(extra)
        return h

    def post_json(self, path: str, json: Optional[Dict[str, Any]] = None, timeout: int = DEFAULT_TIMEOUT):
        url = f"{self.base_url}{path}"
        r = requests.post(url, json=json, headers=self._headers(), timeout=timeout)
        r.raise_for_status()
        return r.json()

    def post_multipart(self, path: str, files: Dict[str, Any], data: Optional[Dict[str, Any]] = None, timeout: int = DEFAULT_TIMEOUT):
        url = f"{self.base_url}{path}"
        # requests will set Content-Type for multipart
        r = requests.post(url, files=files, data=data or {}, headers=self._headers({"Accept": "application/json"}), timeout=timeout)
        r.raise_for_status()
        # Some upload endpoints return JSON, some return a location header
        try:
            return r.json()
        except ValueError:
            return {"status_code": r.status_code, "text": r.text}

    def get_json(self, path: str, params: Optional[Dict[str, Any]] = None, timeout: int = DEFAULT_TIMEOUT):
        url = f"{self.base_url}{path}"
        r = requests.get(url, params=params or {}, headers=self._headers(), timeout=timeout)
        r.raise_for_status()
        return r.json()

    def stream_to_file(self, path: str, out_path: str, timeout: int = DEFAULT_TIMEOUT, chunk_size: int = 8192):
        url = f"{self.base_url}{path}"
        with requests.get(url, headers=self._headers(), stream=True, timeout=timeout) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
        return out_path
