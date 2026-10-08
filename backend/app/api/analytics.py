"""Analytics endpoints: overview, drivers, constructors, circuits, races,
qualifying, pit stops."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics import circuits as circuits_analytics
from app.analytics import constructors as constructors_analytics
from app.analytics import drivers as drivers_analytics
from app.analytics import overview as overview_analytics
from app.analytics import pitstops as pitstops_analytics
from app.analytics import qualifying as qualifying_analytics
from app.analytics import races as races_analytics
from app.db import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", summary="Dashboard overview (counts + chart datasets)")
def overview(
    season: Optional[int] = Query(None, ge=1950, le=2100),
    db: Session = Depends(get_db),
) -> dict:
    return overview_analytics.overview(db, season=season)


@router.get("/drivers", summary="Driver aggregates with filters + sorting")
def drivers(
    season: Optional[int] = Query(None, ge=1950, le=2100),
    constructor_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=80),
    sort: str = Query("points"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    return drivers_analytics.driver_list(
        db, season=season, constructor_id=constructor_id, search=search,
        sort=sort, order=order, limit=limit, offset=offset,
    )


@router.get("/drivers/compare", summary="Side-by-side driver comparison")
def compare_drivers(
    ids: str = Query(..., description="Comma-separated driver ids, e.g. '1,44'"),
    db: Session = Depends(get_db),
) -> dict:
    driver_ids = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    return drivers_analytics.compare_drivers(db, driver_ids)


@router.get("/constructors", summary="Constructor aggregates with filters")
def constructors(
    season: Optional[int] = Query(None, ge=1950, le=2100),
    search: Optional[str] = Query(None, max_length=80),
    sort: str = Query("points"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    return constructors_analytics.constructor_list(
        db, season=season, search=search, sort=sort, order=order,
        limit=limit, offset=offset,
    )


@router.get("/circuits", summary="Circuit aggregates (enriched)")
def circuits(
    search: Optional[str] = Query(None, max_length=80),
    country: Optional[str] = Query(None, max_length=64),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    data = circuits_analytics.circuit_list(
        db, search=search, country=country, limit=limit, offset=offset
    )
    return data


@router.get("/races", summary="Race results overview with filters")
def races(
    season: Optional[int] = Query(None, ge=1950, le=2100),
    circuit_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=80),
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    return races_analytics.race_list(
        db, season=season, circuit_id=circuit_id, search=search,
        limit=limit, offset=offset,
    )


@router.get("/races/position-changes", summary="Biggest position gains/losses")
def position_changes(
    season: Optional[int] = Query(None, ge=1950, le=2100),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    return races_analytics.position_changes(db, season=season, limit=limit)


@router.get("/qualifying", summary="Qualifying analytics (correlation / buckets / race)")
def qualifying(
    season: Optional[int] = Query(None, ge=1950, le=2100),
    race_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
) -> dict:
    if race_id is not None:
        return {"race_id": race_id, "rows": qualifying_analytics.race_qualifying(db, race_id)}
    summary = qualifying_analytics.qualifying_summary(db, season=season)
    summary["top_qualifiers"] = qualifying_analytics.top_qualifiers(db, season=season)
    return summary


@router.get("/pit-stops", summary="Pit-stop analytics (durations / counts / correlation)")
def pit_stops(
    season: Optional[int] = Query(None, ge=1950, le=2100),
    constructor_id: Optional[int] = Query(None, ge=1),
    circuit_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
) -> dict:
    return pitstops_analytics.pit_stop_summary(
        db, season=season, constructor_id=constructor_id, circuit_id=circuit_id
    )
