# desktop/api.py
from pathlib import Path
import json
import os
from request_helper import RequestHelper
from auth import save_token, load_cached_token, clear_cached_token
from utils import save_stream_to_tempfile

API_BASE = "http://localhost:8000"

_req = RequestHelper(API_BASE)

def set_token(token: str):
    _req.set_token(token)

def login_user(username: str, password: str, remember: bool = False) -> dict:
    payload = {"username": username, "password": password}
    res = _req.post_json("/api-token-auth/", json=payload)
    token = res.get("token")
    if token and remember:
        save_token(username, token)
    if token:
        set_token(token)
    return res

def upload_file(file_path: str) -> dict:
    with open(file_path, "rb") as fh:
        files = {"file": (Path(file_path).name, fh)}
        res = _req.post_multipart("/api/datasets/upload/", files=files)
    return res

def get_summary(dataset_id_or_url) -> dict:
    """
    If numeric id or numeric-like string -> /api/datasets/<id>/summary/
    If path-like starting with '/' -> request that path on backend
    Otherwise try dataset id endpoint.
    """
    if isinstance(dataset_id_or_url, int) or (isinstance(dataset_id_or_url, str) and str(dataset_id_or_url).isdigit()):
        return _req.get_json(f"/api/datasets/{int(dataset_id_or_url)}/summary/")
    if isinstance(dataset_id_or_url, str) and dataset_id_or_url.startswith("/"):
        return _req.get_json(dataset_id_or_url)
    return _req.get_json(f"/api/datasets/{dataset_id_or_url}/summary/")

def get_history() -> list:
    """
    Fetch history from backend and normalize entries so caller always
    gets a dataset_id string to use (fallbacks applied).
    """
    try:
        raw = _req.get_json("/api/datasets/history/")
    except Exception:
        # Fallback mock if backend not available
        raw = [
            {
                "dataset_id": "sample_equipment_data.csv",
                "uploaded_at": "2025-11-17T12:00:00Z",
                "rows": 15,
                "columns": ["ID", "Flowrate", "Pressure", "Temperature", "Note"]
            }
        ]

    normalized = []
    for e in raw:
        # e might be a dict with inconsistent keys
        if not isinstance(e, dict):
            continue
        ds = e.get("dataset_id") or e.get("original_filename") or e.get("filename") or e.get("name") or e.get("id")
        # Ensure dataset_id is a string for non-numeric ids
        if ds is None:
            ds = "unknown"
        try:
            rows = int(e.get("rows") or e.get("num_rows") or 0)
        except Exception:
            rows = 0
        columns = e.get("columns") or e.get("cols") or []
        uploaded_at = e.get("uploaded_at") or e.get("created_at") or e.get("timestamp") or None
        normalized.append({
            "dataset_id": ds,
            "uploaded_at": uploaded_at,
            "rows": rows,
            "columns": columns
        })
    return normalized

def download_report(dataset_id: str) -> str:
    out = save_stream_to_tempfile(ext=".pdf")
    _req.stream_to_file(f"/api/datasets/{dataset_id}/report/", out)
    return out

def logout():
    clear_cached_token()
    set_token(None)
