"""OLAP endpoints: rollup, drilldown, slice, dice, pivot."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analytics import olap as olap_service
from app.db import get_db

router = APIRouter(prefix="/olap", tags=["olap"])


def _csv_ints(value: Optional[str]) -> Optional[list[int]]:
    if not value:
        return None
    out = [int(x) for x in value.split(",") if x.strip().lstrip("-").isdigit()]
    return out or None


def _csv_str(value: Optional[str]) -> Optional[list[str]]:
    if not value:
        return None
    parts = [x.strip() for x in value.split(",") if x.strip()]
    return parts or None


def _cube_filter(
    season: Optional[int],
    season_from: Optional[int],
    season_to: Optional[int],
    driver_id: Optional[int],
    constructor_id: Optional[int],
    circuit_id: Optional[int],
    constructor_ids: Optional[str],
    circuit_ids: Optional[str],
    driver_ids: Optional[str],
) -> olap_service.CubeFilter:
    return olap_service.CubeFilter(
        season=season,
        season_from=season_from,
        season_to=season_to,
        driver_id=driver_id,
        constructor_id=constructor_id,
        circuit_id=circuit_id,
        constructor_ids=_csv_ints(constructor_ids),
        circuit_ids=_csv_ints(circuit_ids),
        driver_ids=_csv_ints(driver_ids),
    )


def _catch_value_error(fn, **kwargs):
    try:
        return fn(**kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/rollup", summary="ROLL-UP: aggregate up dimension hierarchies")
def rollup(
    dimensions: str = Query(
        "driver,constructor,season",
        description="Comma-separated hierarchy, e.g. 'driver,constructor,season' "
                    "or 'constructor,season' or 'circuit,season'",
    ),
    season: Optional[int] = Query(None, ge=1950, le=2100),
    season_from: Optional[int] = Query(None, ge=1950, le=2100),
    season_to: Optional[int] = Query(None, ge=1950, le=2100),
    constructor_id: Optional[int] = Query(None, ge=1),
    circuit_id: Optional[int] = Query(None, ge=1),
    constructor_ids: Optional[str] = Query(None, description="e.g. '1,2,6'"),
    circuit_ids: Optional[str] = Query(None),
    driver_ids: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> dict:
    dims = _csv_str(dimensions) or ["driver"]
    flt = _cube_filter(season, season_from, season_to, None,
                       constructor_id, circuit_id,
                       constructor_ids, circuit_ids, driver_ids)
    return _catch_value_error(
        olap_service.rollup, session=db, dimensions=dims, flt=flt, limit=limit
    )


@router.get("/drilldown", summary="DRILL-DOWN: season -> race -> driver -> lap")
def drilldown(
    level: str = Query(..., pattern="^(season|race|driver|lap)$"),
    season: Optional[int] = Query(None, ge=1950, le=2100),
    race_id: Optional[int] = Query(None, ge=1),
    driver_id: Optional[int] = Query(None, ge=1),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return olap_service.drilldown(
            db, level=level, season=season, race_id=race_id,
            driver_id=driver_id, limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/slice", summary="SLICE: filter the cube on one dimension")
def slice(
    dimension: str = Query(..., pattern="^(driver|constructor|season|circuit|race)$"),
    value: str = Query(..., min_length=1, max_length=128,
                       description="Dimension id or exact label"),
    group_by: Optional[str] = Query(
        None, pattern="^(driver|constructor|season|circuit|race)$"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> dict:
    return _catch_value_error(
        olap_service.slice, session=db, dimension=dimension, value=value,
        group_by=group_by, limit=limit,
    )


@router.get("/dice", summary="DICE: filter on multiple dimensions")
def dice(
    season: Optional[int] = Query(None, ge=1950, le=2100),
    season_from: Optional[int] = Query(None, ge=1950, le=2100),
    season_to: Optional[int] = Query(None, ge=1950, le=2100),
    constructor_ids: Optional[str] = Query(None, description="e.g. '1,6'"),
    circuit_ids: Optional[str] = Query(None),
    driver_ids: Optional[str] = Query(None),
    group_by: Optional[str] = Query(
        "season,constructor", description="Comma-separated group-by dimensions"),
    limit: int = Query(300, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> dict:
    flt = _cube_filter(season, season_from, season_to, None, None, None,
                       constructor_ids, circuit_ids, driver_ids)
    dims = _csv_str(group_by) or ["season", "constructor"]
    return _catch_value_error(
        olap_service.dice, session=db, flt=flt, group_by=dims, limit=limit
    )


@router.get("/pivot", summary="PIVOT: cross-tabulate two dimensions")
def pivot(
    rows: str = Query("constructor", pattern="^(driver|constructor|season|circuit|race)$"),
    cols: str = Query("season", pattern="^(driver|constructor|season|circuit|race)$"),
    measure: str = Query(
        "points",
        pattern="^(points|wins|podiums|races|avg_finish|dnfs|avg_position_gain)$",
    ),
    season_from: Optional[int] = Query(None, ge=1950, le=2100),
    season_to: Optional[int] = Query(None, ge=1950, le=2100),
    constructor_ids: Optional[str] = Query(None),
    circuit_ids: Optional[str] = Query(None),
    driver_ids: Optional[str] = Query(None),
    limit_rows: int = Query(25, ge=1, le=100),
    limit_cols: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    flt = _cube_filter(None, season_from, season_to, None, None, None,
                       constructor_ids, circuit_ids, driver_ids)
    return _catch_value_error(
        olap_service.pivot, session=db, rows_dim=rows, cols_dim=cols,
        measure=measure, flt=flt, limit_rows=limit_rows, limit_cols=limit_cols,
    )
