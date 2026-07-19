from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import lithophane
from .models import LithophaneParams

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="MyLitho")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text())


def _parse_params(params: str) -> LithophaneParams:
    try:
        return LithophaneParams.model_validate_json(params)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Invalid params: {exc}") from exc


@app.post("/api/preview")
async def preview(image: UploadFile = File(...), params: str = Form(...)) -> JSONResponse:
    p = _parse_params(params)
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image upload")
    try:
        result = lithophane.build_preview_heightmap(data, p)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to process image: {exc}") from exc
    return JSONResponse(result)


@app.post("/api/generate")
async def generate(image: UploadFile = File(...), params: str = Form(...)) -> StreamingResponse:
    p = _parse_params(params)
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image upload")

    try:
        panel = lithophane.build_panel_mesh(data, p)
        accessory_meshes = lithophane.build_accessory_meshes(p)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to generate mesh: {exc}") from exc

    files: dict[str, bytes] = {"lithophane_panel.stl": panel.export(file_type="stl")}
    for name, mesh in accessory_meshes.items():
        files[f"{name}.stl"] = mesh.export(file_type="stl")

    if len(files) == 1:
        (filename, content), = files.items()
        return StreamingResponse(
            io.BytesIO(content),
            media_type="model/stl",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="mylitho_export.zip"'},
    )
