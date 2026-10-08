"""Pydantic response/request schemas for the F1 INSIGHT API."""
from __future__ import annotations

from datetime import date
import datetime as dt
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorOut(BaseModel):
    detail: str


class Paged(BaseModel, Generic[T]):
    total: int
    limit: int
    offset: int
    items: list[T]


class HealthOut(BaseModel):
    status: str
    service: str = "F1 INSIGHT API"
    version: str
    database: str
    time: str
    warehouse: dict[str, int] = Field(default_factory=dict)
    etl_last_run: Optional[dict[str, Any]] = None


class SeasonOut(BaseModel):
    season: int
    races: int
    results: int
    first_race: Optional[date] = None
    last_race: Optional[date] = None


class RaceOut(BaseModel):
    race_id: int
    season: int
    round: int
    name: str
    date: Optional[dt.date] = None
    circuit_id: Optional[int] = None
    circuit: Optional[str] = None
    country: Optional[str] = None
    winner: Optional[str] = None
    winner_code: Optional[str] = None
    winning_constructor: Optional[str] = None
    entries: Optional[int] = None


class DriverOut(BaseModel):
    driver_id: int
    driver_ref: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    full_name: Optional[str] = None
    number: Optional[int] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[date] = None
    url: Optional[str] = None
    races: Optional[int] = None
    wins: Optional[int] = None
    podiums: Optional[int] = None
    points: Optional[float] = None
    avg_finish: Optional[float] = None
    avg_grid: Optional[float] = None
    dnf_rate: Optional[float] = None
    win_rate: Optional[float] = None
    podium_rate: Optional[float] = None
    fastest_laps: Optional[int] = None
    avg_position_gain: Optional[float] = None
    teams: Optional[str] = None

    model_config = {"extra": "allow"}


class ConstructorOut(BaseModel):
    constructor_id: int
    constructor_ref: Optional[str] = None
    name: str
    nationality: Optional[str] = None
    races: Optional[int] = None
    wins: Optional[int] = None
    podiums: Optional[int] = None
    points: Optional[float] = None
    avg_finish: Optional[float] = None
    dnf_rate: Optional[float] = None
    fastest_laps: Optional[int] = None
    first_season: Optional[int] = None
    last_season: Optional[int] = None

    model_config = {"extra": "allow"}


class CircuitOut(BaseModel):
    circuit_id: int
    circuit_ref: Optional[str] = None
    name: str
    location: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    races: Optional[int] = None
    first_race: Optional[date] = None
    last_race: Optional[date] = None

    model_config = {"extra": "allow"}
