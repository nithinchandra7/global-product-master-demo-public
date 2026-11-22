"""Standalone Global Product Master Demo; identity is simulated and local only."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .local_security import install_local_boundary


def create_app(root: Path | None = None, state_root: Path | None = None) -> FastAPI:
    root = root or Path(os.getenv("SOLUTION_DEMO_ROOT", Path.cwd())).resolve()
    state_root = state_root or Path(os.getenv("SOLUTION_DEMO_STATE_ROOT", str(root))).resolve()
    application = FastAPI(
        title="Synthetic Global Product Master Demo",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    install_local_boundary(application)
    application.include_router(router(state_root))

    @application.get("/api/health")
    def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "project": "master",
            "synthetic": True,
            "identity": "simulated",
            "cloud_verified": False,
        }

    @application.get("/")
    def home() -> RedirectResponse:
        return RedirectResponse("/master-demo/")

    application.mount("/", StaticFiles(directory=root / "dist", html=True), name="demo")
    return application


app = create_app()
