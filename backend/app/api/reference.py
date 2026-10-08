"""Reference data endpoints: seasons, races, drivers, constructors, circuits."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analytics import circuits as circuits_analytics
from app.analytics import constructors as constructors_analytics
from app.analytics import drivers as drivers_analytics
from app.analytics import races as races_analytics
from app.db import get_db
from app.schemas import CircuitOut, ConstructorOut, DriverOut, Paged, RaceOut, SeasonOut
from app.services.sqlutil import fetch_all

router = APIRouter(tags=["reference"])


# --------------------------------------------------------------- seasons
@router.get("/seasons", response_model=list[SeasonOut], summary="All seasons with race counts")
def seasons(db: Session = Depends(get_db)) -> list[SeasonOut]:
    rows = fetch_all(
        db,
        """
        SELECT r.season,
               COUNT(DISTINCT r.race_id) AS races,
               COUNT(f.result_id) AS results,
               MIN(r.date) AS first_race,
               MAX(r.date) AS last_race
        FROM dim_race r
        LEFT JOIN fact_race_result f ON f.race_id = r.race_id
        GROUP BY r.season
        ORDER BY r.season
        """,
    )
    return [SeasonOut(**row) for row in rows]


# ---------------------------------------------------------------- races
@router.get("/races", response_model=Paged[RaceOut], summary="Paginated race list")
def list_races(
    season: Optional[int] = Query(None, ge=1950, le=2100),
    circuit_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=80),
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> Paged[RaceOut]:
    data = races_analytics.race_list(
        db, season=season, circuit_id=circuit_id, search=search,
        limit=limit, offset=offset,
    )
    return Paged[RaceOut](
        total=data["total"], limit=data["limit"], offset=data["offset"],
        items=[RaceOut(**row) for row in data["items"]],
    )


@router.get("/races/{race_id}", summary="Race detail (timing screen)")
def race_detail(race_id: int, db: Session = Depends(get_db)) -> dict:
    data = races_analytics.race_detail(db, race_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Race {race_id} not found")
    return data


# --------------------------------------------------------------- drivers
@router.get("/drivers", response_model=Paged[DriverOut], summary="Paginated driver list")
def list_drivers(
    season: Optional[int] = Query(None, ge=1950, le=2100),
    constructor_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=80),
    sort: str = Query("points", pattern="^(points|wins|podiums|races|avg_finish|avg_grid|dnf_rate|position_gain|name)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> Paged[DriverOut]:
    data = drivers_analytics.driver_list(
        db, season=season, constructor_id=constructor_id, search=search,
        sort=sort, order=order, limit=limit, offset=offset,
    )
    return Paged[DriverOut](
        total=data["total"], limit=data["limit"], offset=data["offset"],
        items=[DriverOut(**row) for row in data["items"]],
    )


@router.get("/drivers/{driver_id}", summary="Driver profile + career analytics")
def driver_detail(driver_id: int, db: Session = Depends(get_db)) -> dict:
    data = drivers_analytics.driver_profile(db, driver_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Driver {driver_id} not found")
    return data


# ---------------------------------------------------------- constructors
@router.get("/constructors", response_model=Paged[ConstructorOut],
            summary="Paginated constructor list")
def list_constructors(
    season: Optional[int] = Query(None, ge=1950, le=2100),
    search: Optional[str] = Query(None, max_length=80),
    sort: str = Query("points", pattern="^(points|wins|podiums|races|avg_finish|dnf_rate|name)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> Paged[ConstructorOut]:
    data = constructors_analytics.constructor_list(
        db, season=season, search=search, sort=sort, order=order,
        limit=limit, offset=offset,
    )
    return Paged[ConstructorOut](
        total=data["total"], limit=data["limit"], offset=data["offset"],
        items=[ConstructorOut(**row) for row in data["items"]],
    )


@router.get("/constructors/{constructor_id}", summary="Constructor profile + analytics")
def constructor_detail(constructor_id: int, db: Session = Depends(get_db)) -> dict:
    data = constructors_analytics.constructor_profile(db, constructor_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Constructor {constructor_id} not found")
    return data


# -------------------------------------------------------------- circuits
@router.get("/circuits", response_model=Paged[CircuitOut], summary="Paginated circuit list")
def list_circuits(
    search: Optional[str] = Query(None, max_length=80),
    country: Optional[str] = Query(None, max_length=64),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> Paged[CircuitOut]:
    data = circuits_analytics.circuit_list(
        db, search=search, country=country, limit=limit, offset=offset,
    )
    return Paged[CircuitOut](
        total=data["total"], limit=data["limit"], offset=data["offset"],
        items=[CircuitOut(**row) for row in data["items"]],
    )


@router.get("/circuits/{circuit_id}", summary="Circuit profile + analytics")
def circuit_detail(circuit_id: int, db: Session = Depends(get_db)) -> dict:
    data = circuits_analytics.circuit_profile(db, circuit_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Circuit {circuit_id} not found")
    return data
