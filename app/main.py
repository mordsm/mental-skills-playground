from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.database import init_db
from app.routers.mental_skills import router as mental_skills_router


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Mental Skills Playground",
        description="Standalone backend for low-intensity meta-cognitive training sessions.",
        version="0.3.0",
        servers=[{"url": get_settings().public_base_url}],
    )

    @app.middleware("http")
    async def disable_static_cache(request: Request, call_next) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/static") or request.url.path == "/":
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    @app.get("/api/health", operation_id="getHealth")
    def health() -> dict:
        return {"success": True, "service": "mental-skills-playground"}

    # Mount interactive visual web UI
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/static/index.html?v=5")

    app.include_router(mental_skills_router)
    return app


app = create_app()
