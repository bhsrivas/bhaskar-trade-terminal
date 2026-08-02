from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.routes import router
from app.core.config import settings

app = FastAPI(title="Bhaskar Trade Terminal", version="3.0-sprint1")
app.include_router(router)


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(settings.base_dir / "index.html")


@app.get("/app.js")
async def app_js() -> FileResponse:
    return FileResponse(settings.base_dir / "app.js", media_type="application/javascript")


@app.get("/styles.css")
async def styles_css() -> FileResponse:
    return FileResponse(settings.base_dir / "styles.css", media_type="text/css")
