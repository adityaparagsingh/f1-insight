"""Race results + qualifying pipelines (bulk or per-season extraction)."""
from __future__ import annotations

from typing import Optional

from etl.extract.endpoints import F1Api
from etl.load.warehouse import DimensionLoader
from etl.logging_utils import get_logger
from etl.pipelines._common import BatchUpsert, resolve_race_ids
from etl.transform import facts
from etl.transform.quality import EtlStats, dedupe

log = get_logger("etl.results")


def load_results(
    api: F1Api,
    dims: DimensionLoader,
    session,
    stats: EtlStats,
    season: Optional[int] = None,
) -> int:
    from app.models import FactRaceResult

    batch = BatchUpsert(session, FactRaceResult, batch_size=1000,
                        exclude_columns={"pit_stop_count"})
    rows_iter = api.results(season)
    rows_iter = dedupe(
        rows_iter,
        lambda r: (r["_race"].get("season"), r["_race"].get("round"),
                   (r.get("Driver") or {}).get("driverId")),
        stats,
    )
    for raw in rows_iter:
        stats.records_extracted += 1
        ids = resolve_race_ids(dims, raw["_race"], raw.get("Driver"),
                               raw.get("Constructor"), stats)
        if ids is None:
            continue
        row = facts.transform_result(raw, ids, stats)
        if row is None:
            continue
        batch.add(row)
        stats.records_transformed += 1
    loaded = batch.flush()
    stats.records_loaded += loaded
    log.info("race results loaded: %d (season=%s)", loaded, season or "all")
    return loaded


def load_qualifying(
    api: F1Api,
    dims: DimensionLoader,
    session,
    stats: EtlStats,
    season: Optional[int] = None,
) -> int:
    from app.models import FactQualifying

    batch = BatchUpsert(session, FactQualifying, batch_size=1000)
    rows_iter = api.qualifying(season)
    rows_iter = dedupe(
        rows_iter,
        lambda r: (r["_race"].get("season"), r["_race"].get("round"),
                   (r.get("Driver") or {}).get("driverId")),
        stats,
    )
    for raw in rows_iter:
        stats.records_extracted += 1
        ids = resolve_race_ids(dims, raw["_race"], raw.get("Driver"),
                               raw.get("Constructor"), stats)
        if ids is None:
            continue
        row = facts.transform_qualifying(raw, ids, stats)
        if row is None:
            continue
        batch.add(row)
        stats.records_transformed += 1
    loaded = batch.flush()
    stats.records_loaded += loaded
    log.info("qualifying rows loaded: %d (season=%s)", loaded, season or "all")
    return loaded
