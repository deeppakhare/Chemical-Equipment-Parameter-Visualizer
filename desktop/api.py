# desktop/api.py
from pathlib import Path
import json
from .request_helper import RequestHelper
from .auth import save_token, load_cached_token, clear_cached_token
from .utils import save_stream_to_tempfile

# Configure base URL (match your client.py)
API_BASE = "http://localhost:8000"

# create helper instance (token can be set later)
_req = RequestHelper(API_BASE)

def set_token(token: str):
    _req.set_token(token)

def login_user(username: str, password: str, remember: bool = False) -> dict:
    """
    POST /api-token-auth/ -> {"token": "..."}
    Returns dict {"token": "..."}
    """
    payload = {"username": username, "password": password}
    # DRF obtain_auth_token accepts JSON
    res = _req.post_json("/api-token-auth/", json=payload)
    token = res.get("token")
    if token and remember:
        save_token(username, token)
    if token:
        set_token(token)
    return res

def upload_file(file_path: str) -> dict:
    """
    POST multipart to /api/datasets/upload/
    Returns JSON response (dataset_id, summary_url, etc).
    """
    # open file and send as 'file'
    with open(file_path, "rb") as fh:
        files = {"file": (Path(file_path).name, fh)}
        res = _req.post_multipart("/api/datasets/upload/", files=files)
    return res

def get_summary(dataset_id_or_url) -> dict:
    """
    If dataset_id_or_url looks numeric, call /api/datasets/<id>/summary/
    If string starts with '/', treat as path on backend; otherwise pass to /api/datasets/<id>/summary/
    """
    if isinstance(dataset_id_or_url, int) or (isinstance(dataset_id_or_url, str) and str(dataset_id_or_url).isdigit()):
        return _req.get_json(f"/api/datasets/{dataset_id_or_url}/summary/")
    # if looks like a path with leading /, request as-is on backend
    if isinstance(dataset_id_or_url, str) and dataset_id_or_url.startswith("/"):
        return _req.get_json(dataset_id_or_url)
    # fallback try dataset id route
    return _req.get_json(f"/api/datasets/{dataset_id_or_url}/summary/")

def get_history() -> list:
    return _req.get_json("/api/datasets/history/")

def download_report(dataset_id: str) -> str:
    """
    GET /api/datasets/<id>/report/ -> stream PDF to a tempfile and return path
    """
    out = save_stream_to_tempfile(ext=".pdf")
    _req.stream_to_file(f"/api/datasets/{dataset_id}/report/", out)
    return out

def logout():
    clear_cached_token()
    set_token(None)
