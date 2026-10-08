"""F1 INSIGHT — FastAPI application entrypoint.

Run:  uvicorn app.main:app --host 127.0.0.1 --port 8000
Docs: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api import analytics, health, insights, mining, olap, reference
from app.config import CORS_ORIGINS

app = FastAPI(
    title="F1 INSIGHT API",
    description=(
        "Formula 1 Performance Intelligence — data warehouse analytics, OLAP "
        "operations and data-mining endpoints over a MySQL star schema loaded "
        "from the Jolpica F1 API."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(reference.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(olap.router, prefix=API_PREFIX)
app.include_router(mining.router, prefix=API_PREFIX)
app.include_router(insights.router, prefix=API_PREFIX)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "service": "F1 INSIGHT API",
        "version": __version__,
        "docs": "/docs",
        "health": "/api/health",
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {exc}"},
    )
