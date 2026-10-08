"""Per-race detail pipelines: pit stops and lap times."""
from __future__ import annotations

from typing import Iterable, Optional

from etl.extract.client import JolpicaError
from etl.extract.endpoints import F1Api
from etl.load.warehouse import refresh_pit_stop_counts
from etl.logging_utils import get_logger
from etl.pipelines._common import (
    BatchUpsert,
    _scope_races,
    race_result_index,
    resolve_race_ids,
)
from etl.transform import facts
from etl.transform.quality import EtlStats, dedupe

log = get_logger("etl.detail")


def load_pit_stops(
    api: F1Api,
    dims,
    session,
    stats: EtlStats,
    season: Optional[int] = None,
    min_season: Optional[int] = None,
    rounds: Optional[dict[int, set[int]]] = None,
    refresh_counts: bool = True,
) -> int:
    from app.models import FactPitStop

    total = 0
    races = _scope_races(dims, season=season, min_season=min_season, rounds=rounds)
    log.info("pit stops: scanning %d races", len(races))

    for s, r in races:
        race_id = dims.race_map[(s, r)]
        index = race_result_index(session, race_id)
        if not index:
            stats.note(f"pit stops skipped for {s}-{r:02d}: no race results loaded")
            continue
        try:
            raw_rows = list(api.pit_stops(s, r))
        except JolpicaError as exc:
            stats.issue(f"pit stops {s}-{r:02d}: {exc}")
            continue

        race_ctx = None
        batch = BatchUpsert(session, FactPitStop, batch_size=1000)
        rows = dedupe(raw_rows, lambda x: (x.get("driverId"), x.get("stop")), stats)
        for raw in rows:
            stats.records_extracted += 1
            race_ctx = raw.get("_race") or race_ctx
            driver_ref = raw.get("driverId")
            constructor_id = index.get(dims.driver_map.get(driver_ref, -1))
            if constructor_id is None:
                driver_id = dims.ensure_driver({"driverId": driver_ref})
                constructor_id = index.get(driver_id)
            else:
                driver_id = dims.driver_map.get(driver_ref)
            if driver_id is None or constructor_id is None:
                stats.issue(f"pit stop {s}-{r:02d}: unknown driver {driver_ref}")
                continue
            ids = resolve_race_ids(
                dims, race_ctx, stats=stats, driver_id=driver_id,
                constructor_id=constructor_id,
            )
            if ids is None:
                continue
            row = facts.transform_pit_stop(raw, ids, stats)
            if row is None:
                continue
            batch.add(row)
            stats.records_transformed += 1
        total += batch.flush()

    stats.records_loaded += total
    if refresh_counts and total:
        refresh_pit_stop_counts(session)
    log.info("pit stop rows loaded: %d", total)
    return total


def load_laps(
    api: F1Api,
    dims,
    session,
    stats: EtlStats,
    season: Optional[int] = None,
    min_season: Optional[int] = None,
    rounds: Optional[dict[int, set[int]]] = None,
) -> int:
    from app.models import FactLap

    total = 0
    races = _scope_races(dims, season=season, min_season=min_season, rounds=rounds)
    log.info("laps: scanning %d races", len(races))

    for s, r in races:
        race_id = dims.race_map[(s, r)]
        index = race_result_index(session, race_id)
        if not index:
            stats.note(f"laps skipped for {s}-{r:02d}: no race results loaded")
            continue
        try:
            raw_rows = list(api.laps(s, r))
        except JolpicaError as exc:
            stats.issue(f"laps {s}-{r:02d}: {exc}")
            continue

        batch = BatchUpsert(session, FactLap, batch_size=2000)
        rows = dedupe(
            raw_rows, lambda x: (x.get("driverId"), x.get("lap")), stats
        )
        race_ctx: Optional[dict] = None
        for raw in rows:
            stats.records_extracted += 1
            race_ctx = raw.get("_race") or race_ctx
            driver_ref = raw.get("driverId")
            driver_id = dims.driver_map.get(driver_ref)
            constructor_id = index.get(driver_id) if driver_id else None
            if driver_id is None:
                driver_id = dims.ensure_driver({"driverId": driver_ref})
                constructor_id = index.get(driver_id)
            if driver_id is None or constructor_id is None:
                stats.issue(f"lap {s}-{r:02d}: unknown driver {driver_ref}")
                continue
            ids = resolve_race_ids(
                dims, race_ctx, stats=stats, driver_id=driver_id,
                constructor_id=constructor_id,
            )
            if ids is None:
                continue
            row = facts.transform_lap(raw, ids, stats)
            if row is None:
                continue
            batch.add(row)
            stats.records_transformed += 1
        loaded = batch.flush()
        total += loaded

    stats.records_loaded += total
    log.info("lap rows loaded: %d", total)
    return total
