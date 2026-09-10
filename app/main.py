from __future__ import annotations

from fastapi import FastAPI

from app.config import get_settings
from app.database import init_db
from app.routers.mental_skills import router as mental_skills_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Mental Skills Playground",
        description="Standalone backend for low-intensity meta-cognitive training sessions.",
        version="0.1.0",
        servers=[{"url": get_settings().public_base_url}],
    )

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    @app.get("/api/health", operation_id="getHealth")
    def health() -> dict:
        return {"success": True, "service": "mental-skills-playground"}

    app.include_router(mental_skills_router)
    return app


app = create_app()

