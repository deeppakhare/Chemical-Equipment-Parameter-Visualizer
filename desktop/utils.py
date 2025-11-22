# desktop/utils.py
import os
from pathlib import Path
import tempfile

def ensure_dir(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

def save_stream_to_tempfile(ext=".pdf", prefix="ev_report_"):
    f = tempfile.NamedTemporaryFile(delete=False, suffix=ext, prefix=prefix)
    return f.name
