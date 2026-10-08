"""Reference pipeline: seasons/races, drivers, constructors, circuits, dates."""
from __future__ import annotations

from etl.extract.endpoints import F1Api
from etl.load.warehouse import DimensionLoader
from etl.logging_utils import get_logger
from etl.transform.quality import EtlStats

log = get_logger("etl.reference")


def load_reference(api: F1Api, dims: DimensionLoader, stats: EtlStats) -> None:
    """Extract + load all dimension entities (idempotent)."""
    n_circuits = n_constructors = n_drivers = n_races = 0

    for raw in api.circuits():
        stats.records_extracted += 1
        if dims.ensure_circuit(raw) is not None:
            n_circuits += 1
    log.info("circuits: %d", n_circuits)

    for raw in api.constructors():
        stats.records_extracted += 1
        if dims.ensure_constructor(raw) is not None:
            n_constructors += 1
    log.info("constructors: %d", n_constructors)

    for raw in api.drivers():
        stats.records_extracted += 1
        # refresh=True keeps existing rows (e.g. created from a result payload
        # before the reference stage ran) in sync with the canonical listing.
        if dims.ensure_driver(raw, refresh=True) is not None:
            n_drivers += 1
    log.info("drivers: %d", n_drivers)

    from etl.transform.common import parse_date

    for raw in api.races():
        stats.records_extracted += 1
        race_date = parse_date(raw.get("date"))
        circuit_id = dims.ensure_circuit(raw.get("Circuit") or {})
        if race_date is None or circuit_id is None:
            stats.issue(
                f"race {raw.get('season')}-{raw.get('round')}: invalid date/circuit"
            )
            continue
        dims.ensure_race(
            season=int(raw["season"]),
            round_=int(raw["round"]),
            name=raw.get("raceName") or f"{raw['season']} Round {raw['round']}",
            race_date=race_date,
            circuit_id=circuit_id,
            url=raw.get("url"),
        )
        n_races += 1
    log.info("races: %d", n_races)

    stats.records_transformed += n_circuits + n_constructors + n_drivers + n_races
    stats.records_loaded += n_circuits + n_constructors + n_drivers + n_races
