"""Shared pipeline helpers: race-context resolution and batched upserts."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models import FactRaceResult
from etl.load.warehouse import DimensionLoader, upsert_rows
from etl.transform.common import parse_date
from etl.transform.quality import EtlStats


class BatchUpsert:
    """Accumulates warehouse rows and flushes them in idempotent chunks."""

    def __init__(self, session: Session, model, batch_size: int = 1000,
                 exclude_columns: Optional[set[str]] = None) -> None:
        self.session = session
        self.model = model
        self.batch_size = batch_size
        self.exclude_columns = exclude_columns
        self._rows: list[dict] = []
        self.loaded = 0

    def add(self, row: Optional[dict]) -> None:
        if row is None:
            return
        self._rows.append(row)
        if len(self._rows) >= self.batch_size:
            self.flush()

    def extend(self, rows) -> None:
        for r in rows:
            self.add(r)

    def flush(self) -> int:
        if self._rows:
            self.loaded += upsert_rows(
                self.session, self.model, self._rows,
                exclude_columns=self.exclude_columns,
            )
            self._rows = []
        return self.loaded

    @property
    def pending(self) -> int:
        return len(self._rows)


def resolve_race_ids(
    dims: DimensionLoader,
    race_ctx: dict,
    driver_raw: Optional[dict] = None,
    constructor_raw: Optional[dict] = None,
    stats: Optional[EtlStats] = None,
    driver_id: Optional[int] = None,
    constructor_id: Optional[int] = None,
) -> Optional[dict]:
    """Resolve every surrogate key needed for one fact row from race context.

    Creates missing dimensions on the fly (race results may contain circuits,
    drivers or constructors that the reference stage has not seen).
    ``driver_id`` / ``constructor_id`` may be passed pre-resolved (lap and pit
    stop payloads only carry ``driverId``).
    """
    stats = stats or EtlStats()
    season = race_ctx.get("season")
    round_ = race_ctx.get("round")
    race_date = parse_date(race_ctx.get("date"))
    circuit_raw = race_ctx.get("Circuit") or {}

    if season is None or round_ is None or race_date is None:
        stats.issue(
            f"incomplete race context (season={season}, round={round_}, "
            f"date={race_ctx.get('date')})"
        )
        return None

    circuit_id = dims.ensure_circuit(circuit_raw)
    if circuit_id is None:
        stats.issue(f"race {season}-{round_}: missing circuit reference")
        return None

    race_id = dims.ensure_race(
        season=int(season),
        round_=int(round_),
        name=race_ctx.get("raceName") or f"{season} Round {round_}",
        race_date=race_date,
        circuit_id=circuit_id,
        url=race_ctx.get("url"),
    )
    if race_id is None:
        stats.issue(f"race {season}-{round_}: could not be created")
        return None

    if driver_id is None:
        driver_id = dims.ensure_driver(driver_raw or {})
    if constructor_id is None:
        constructor_id = dims.ensure_constructor(constructor_raw or {})
    if driver_id is None:
        stats.issue(f"race {season}-{round_}: missing driver reference")
        return None
    if constructor_id is None:
        stats.issue(f"race {season}-{round_}: missing constructor reference")
        return None

    return {
        "race_id": race_id,
        "driver_id": driver_id,
        "constructor_id": constructor_id,
        "circuit_id": circuit_id,
        "date_id": dims.date_map[race_date],
        "season": int(season),
        "round": int(round_),
    }


def race_result_index(session: Session, race_id: int) -> dict[int, int]:
    """driver_id -> constructor_id for a race (used to enrich lap rows)."""
    rows = session.query(
        FactRaceResult.driver_id, FactRaceResult.constructor_id
    ).filter(FactRaceResult.race_id == race_id).all()
    return {r[0]: r[1] for r in rows}


def _scope_races(
    dims,
    season: Optional[int] = None,
    min_season: Optional[int] = None,
    rounds: Optional[dict] = None,
) -> list[tuple[int, int]]:
    """Sorted (season, round) scope from the loaded dim_race cache."""
    out = []
    for (s, r) in dims.race_map:
        if season is not None and s != season:
            continue
        if min_season is not None and s < min_season:
            continue
        if rounds is not None and r not in rounds.get(s, set()):
            continue
        out.append((s, r))
    return sorted(out)
