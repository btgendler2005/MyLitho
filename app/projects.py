"""Local project history: every STL export gets saved so it can be
reopened later with the same photo and settings.

SQLite for the index (stdlib, no new dependency) plus the original photo
and a small thumbnail on disk, all under data/ -- gitignored, since this
can contain customer photos and must never end up in the (public) repo.
"""

from __future__ import annotations

import io
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from PIL import Image

from .models import LithophaneParams

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROJECTS_DIR = DATA_DIR / "projects"
DB_PATH = DATA_DIR / "projects.db"

MAX_PROJECTS = 200
THUMBNAIL_PX = 220

_VALID_EXTS = {"jpg", "jpeg", "png", "webp", "bmp", "gif", "tiff"}


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at REAL NOT NULL,
                name TEXT NOT NULL,
                params_json TEXT NOT NULL,
                image_ext TEXT NOT NULL
            )
            """
        )


def _derive_name(original_filename: str | None) -> str:
    if not original_filename:
        return "Untitled"
    stem = Path(original_filename).stem.strip()
    return stem or "Untitled"


def _infer_ext(filename: str | None, content_type: str | None) -> str:
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in _VALID_EXTS:
            return "jpg" if ext == "jpeg" else ext
    if content_type and "/" in content_type:
        guess = content_type.split("/")[-1].lower()
        if guess in _VALID_EXTS:
            return "jpg" if guess == "jpeg" else guess
    return "png"


def save_project(
    image_bytes: bytes,
    params: LithophaneParams,
    original_filename: str | None,
    content_type: str | None = None,
) -> int:
    """Store the exact original photo bytes (no re-encoding, so reopening
    a project doesn't lose quality) plus a small JPEG thumbnail for the
    Recent list, and index it in SQLite. Returns the new project id."""
    ext = _infer_ext(original_filename, content_type)
    name = _derive_name(original_filename)

    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO projects (created_at, name, params_json, image_ext) VALUES (?, ?, ?, ?)",
            (time.time(), name, params.model_dump_json(), ext),
        )
        project_id = cur.lastrowid

    project_dir = PROJECTS_DIR / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / f"original.{ext}").write_bytes(image_bytes)

    thumb = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    thumb.thumbnail((THUMBNAIL_PX, THUMBNAIL_PX), Image.LANCZOS)
    thumb.save(project_dir / "thumbnail.jpg", format="JPEG", quality=85)

    _enforce_max_projects()
    return project_id


def _enforce_max_projects() -> None:
    with _connect() as conn:
        rows = conn.execute("SELECT id FROM projects ORDER BY created_at DESC").fetchall()
    for row in rows[MAX_PROJECTS:]:
        delete_project(row["id"])


def list_projects(limit: int = 30) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, created_at, name FROM projects ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_project(project_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["params"] = json.loads(data.pop("params_json"))
    return data


def get_image_path(project_id: int) -> Path | None:
    project = get_project(project_id)
    if project is None:
        return None
    path = PROJECTS_DIR / str(project_id) / f"original.{project['image_ext']}"
    return path if path.exists() else None


def get_thumbnail_path(project_id: int) -> Path | None:
    path = PROJECTS_DIR / str(project_id) / "thumbnail.jpg"
    return path if path.exists() else None


def delete_project(project_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    project_dir = PROJECTS_DIR / str(project_id)
    if project_dir.exists():
        for f in project_dir.iterdir():
            f.unlink()
        project_dir.rmdir()
