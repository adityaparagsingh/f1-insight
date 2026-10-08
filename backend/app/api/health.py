"""GET /api/health"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.db import get_db
from app.schemas import HealthOut
from app.services.sqlutil import fetch_one

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthOut, summary="Service + warehouse health")
def health(db: Session = Depends(get_db)) -> HealthOut:
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
        counts = {
            "seasons": db.execute(text("SELECT COUNT(DISTINCT season) FROM dim_race")).scalar(),
            "races": db.execute(text("SELECT COUNT(*) FROM dim_race")).scalar(),
            "drivers": db.execute(text("SELECT COUNT(*) FROM dim_driver")).scalar(),
            "constructors": db.execute(text("SELECT COUNT(*) FROM dim_constructor")).scalar(),
            "circuits": db.execute(text("SELECT COUNT(*) FROM dim_circuit")).scalar(),
            "race_records": db.execute(text("SELECT COUNT(*) FROM fact_race_result")).scalar(),
            "lap_records": db.execute(text("SELECT COUNT(*) FROM fact_lap")).scalar(),
            "qualifying_records": db.execute(text("SELECT COUNT(*) FROM fact_qualifying")).scalar(),
            "pit_stop_records": db.execute(text("SELECT COUNT(*) FROM fact_pit_stop")).scalar(),
        }
        last = fetch_one(
            db,
            """
            SELECT run_id, pipeline, scope, started_at, finished_at, status,
                   records_extracted, records_transformed, records_loaded, errors
            FROM etl_run_log ORDER BY run_id DESC LIMIT 1
            """,
        )
        status = "ok"
    except Exception:
        db_status = "unavailable"
        counts = {}
        last = None
        status = "degraded"

    return HealthOut(
        status=status,
        version=__version__,
        database=db_status,
        time=datetime.utcnow().isoformat() + "Z",
        warehouse={k: int(v or 0) for k, v in counts.items()},
        etl_last_run=last,
    )
