"""Standings pipelines: per-round driver and constructor championship rows."""
from __future__ import annotations

from typing import Optional

from etl.extract.client import JolpicaError
from etl.extract.endpoints import F1Api
from etl.logging_utils import get_logger
from etl.pipelines._common import BatchUpsert, _scope_races
from etl.transform import facts
from etl.transform.quality import EtlStats, dedupe

log = get_logger("etl.standings")


def load_standings(
    api: F1Api,
    dims,
    session,
    stats: EtlStats,
    season: Optional[int] = None,
    min_season: Optional[int] = None,
    rounds: Optional[dict[int, set[int]]] = None,
) -> int:
    from app.models import FactConstructorStanding, FactDriverStanding

    races = _scope_races(dims, season=season, min_season=min_season, rounds=rounds)
    log.info("standings: scanning %d rounds", len(races))

    d_batch = BatchUpsert(session, FactDriverStanding, batch_size=2000)
    c_batch = BatchUpsert(session, FactConstructorStanding, batch_size=2000)

    for s, r in races:
        race_id = dims.race_map[(s, r)]

        # ---- driver standings ------------------------------------------
        try:
            d_rows = list(api.driver_standings(s, r))
        except JolpicaError as exc:
            stats.issue(f"driver standings {s}-{r:02d}: {exc}")
            d_rows = []
        for raw in dedupe(d_rows, lambda x: (x.get("Driver") or {}).get("driverId"), stats):
            stats.records_extracted += 1
            driver_id = dims.ensure_driver(raw.get("Driver") or {})
            if driver_id is None:
                stats.issue(f"driver standings {s}-{r:02d}: missing driver ref")
                continue
            constructors = raw.get("Constructors") or []
            constructor_id = (
                dims.ensure_constructor(constructors[-1]) if constructors else None
            )
            ids = {
                "race_id": race_id,
                "season": s,
                "round": raw.get("_round", r),
                "driver_id": driver_id,
                "constructor_id": constructor_id,
            }
            row = facts.transform_driver_standing(raw, ids, stats)
            if row is None:
                continue
            d_batch.add(row)
            stats.records_transformed += 1

        # ---- constructor standings --------------------------------------
        try:
            c_rows = list(api.constructor_standings(s, r))
        except JolpicaError as exc:
            stats.issue(f"constructor standings {s}-{r:02d}: {exc}")
            c_rows = []
        for raw in dedupe(c_rows, lambda x: (x.get("Constructor") or {}).get("constructorId"), stats):
            stats.records_extracted += 1
            constructor_id = dims.ensure_constructor(raw.get("Constructor") or {})
            if constructor_id is None:
                stats.issue(f"constructor standings {s}-{r:02d}: missing constructor ref")
                continue
            ids = {
                "race_id": race_id,
                "season": s,
                "round": raw.get("_round", r),
                "constructor_id": constructor_id,
            }
            row = facts.transform_constructor_standing(raw, ids, stats)
            if row is None:
                continue
            c_batch.add(row)
            stats.records_transformed += 1

    loaded = d_batch.flush() + c_batch.flush()
    stats.records_loaded += loaded
    log.info("standings rows loaded: %d", loaded)
    return loaded
