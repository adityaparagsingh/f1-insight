"""ETL orchestrator: stages, run-log audit trail, incremental logic."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func

from app.db import SessionLocal
from app.models import (
    DimRace,
    EtlRunLog,
    FactRaceResult,
)
from etl.extract.client import JolpicaClient
from etl.extract.endpoints import F1Api
from etl.load.warehouse import DimensionLoader
from etl.logging_utils import get_logger
from etl.pipelines import detail, reference, results, standings
from etl.transform.quality import EtlStats

log = get_logger("etl.runner")

ALL_STAGES = ("reference", "results", "qualifying", "pitstops", "standings", "laps")

_DELTA_KEYS = (
    "records_extracted",
    "records_transformed",
    "records_loaded",
    "duplicates_removed",
    "missing_values_fixed",
    "invalid_values_fixed",
    "errors",
)


class EtlRunner:
    def __init__(
        self,
        lap_start: int = 2015,
        pit_start: int = 2011,
        standings_since: int = 1980,
        use_cache: bool = True,
        refresh_cache: bool = False,
        requests_per_second: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        kwargs = {"use_cache": use_cache, "refresh_cache": refresh_cache}
        if requests_per_second is not None:
            kwargs["requests_per_second"] = requests_per_second
        if max_retries is not None:
            kwargs["max_retries"] = max_retries
        self.client = JolpicaClient(**kwargs)
        self.api = F1Api(self.client)
        self.session = SessionLocal()
        self.dims = DimensionLoader(self.session)
        self.stats = EtlStats()
        self.lap_start = lap_start
        self.pit_start = pit_start
        self.standings_since = standings_since
        self._stages_run: list[EtlRunLog] = []

    # ------------------------------------------------------------- run log
    def _snapshot(self) -> dict:
        d = self.stats.as_dict()
        return {k: d.get(k, 0) for k in _DELTA_KEYS}

    # ------------------------------------------------------------- stages
    def stage_reference(self, scope: str = "all") -> None:
        row = self._open_stage("reference", scope)
        try:
            reference.load_reference(self.api, self.dims, self.stats)
            self._close_stage(row, None)
        except Exception as exc:
            self._close_stage(row, exc)
            raise

    def stage_results(self, season: Optional[int] = None) -> None:
        row = self._open_stage("results", str(season or "all"))
        try:
            results.load_results(self.api, self.dims, self.session, self.stats, season)
            self._close_stage(row, None)
        except Exception as exc:
            self._close_stage(row, exc)
            raise

    def stage_qualifying(self, season: Optional[int] = None) -> None:
        row = self._open_stage("qualifying", str(season or "all"))
        try:
            results.load_qualifying(self.api, self.dims, self.session, self.stats, season)
            self._close_stage(row, None)
        except Exception as exc:
            self._close_stage(row, exc)
            raise

    def stage_pitstops(
        self,
        season: Optional[int] = None,
        min_season: Optional[int] = None,
        rounds: Optional[dict] = None,
    ) -> None:
        scope = f"season={season} min_season={min_season} rounds={rounds is not None}"
        row = self._open_stage("pitstops", scope)
        try:
            detail.load_pit_stops(
                self.api, self.dims, self.session, self.stats,
                season=season, min_season=min_season, rounds=rounds,
            )
            self._close_stage(row, None)
        except Exception as exc:
            self._close_stage(row, exc)
            raise

    def stage_standings(
        self,
        season: Optional[int] = None,
        min_season: Optional[int] = None,
        rounds: Optional[dict] = None,
    ) -> None:
        scope = f"season={season} min_season={min_season} rounds={rounds is not None}"
        row = self._open_stage("standings", scope)
        try:
            standings.load_standings(
                self.api, self.dims, self.session, self.stats,
                season=season, min_season=min_season, rounds=rounds,
            )
            self._close_stage(row, None)
        except Exception as exc:
            self._close_stage(row, exc)
            raise

    def stage_laps(
        self,
        season: Optional[int] = None,
        min_season: Optional[int] = None,
        rounds: Optional[dict] = None,
    ) -> None:
        scope = f"season={season} min_season={min_season} rounds={rounds is not None}"
        row = self._open_stage("laps", scope)
        try:
            detail.load_laps(
                self.api, self.dims, self.session, self.stats,
                season=season, min_season=min_season, rounds=rounds,
            )
            self._close_stage(row, None)
        except Exception as exc:
            self._close_stage(row, exc)
            raise

    # ------------------------------------------------------- stage helpers
    def _open_stage(self, name: str, scope: str) -> EtlRunLog:
        self._before = self._snapshot()
        row = EtlRunLog(
            pipeline=name, scope=scope, started_at=datetime.utcnow(), status="RUNNING",
        )
        self.session.add(row)
        self.session.commit()
        log.info("=== stage %s [%s] start ===", name, scope)
        return row

    def _close_stage(self, row: EtlRunLog, exc: Optional[BaseException]) -> None:
        row.finished_at = datetime.utcnow()
        after = self._snapshot()
        for k in _DELTA_KEYS:
            setattr(row, k, max(after.get(k, 0) - self._before.get(k, 0), 0))
        if exc is None:
            row.status = "SUCCESS"
            row.message = self.stats.quality_summary
        else:
            row.status = "FAILED"
            row.message = f"{type(exc).__name__}: {exc}"[:2000]
        self.session.add(row)
        self.session.commit()
        self._stages_run.append(row)
        log.info(
            "=== stage %s [%s] %s | extracted=%d transformed=%d loaded=%d errors=%d ===",
            row.pipeline, row.scope, row.status,
            row.records_extracted, row.records_transformed,
            row.records_loaded, row.errors,
        )

    # ------------------------------------------------------------ modes
    def current_season(self) -> int:
        max_season = self.session.query(func.max(DimRace.season)).scalar()
        if max_season:
            return int(max_season)
        return datetime.utcnow().year

    def missing_rounds(self, season: int) -> dict[int, set[int]]:
        """Rounds of ``season`` that have no rows in fact_race_result."""
        race_rows = (
            self.session.query(DimRace.race_id, DimRace.round)
            .filter(DimRace.season == season)
            .all()
        )
        if not race_rows:
            return {}
        race_ids = [r[0] for r in race_rows]
        loaded = set(
            r[0]
            for r in self.session.query(FactRaceResult.race_id)
            .filter(FactRaceResult.race_id.in_(race_ids))
            .distinct()
            .all()
        )
        missing = {season: {r for rid, r in race_rows if rid not in loaded}}
        return missing

    def run(self, mode: str, season: Optional[int] = None,
            stages: Optional[tuple[str, ...]] = None) -> dict:
        """Run the pipeline.  mode ∈ {'all', 'season', 'update'}."""
        stages = tuple(stages or ALL_STAGES)
        unknown = set(stages) - set(ALL_STAGES)
        if unknown:
            raise ValueError(f"unknown stages: {sorted(unknown)}")

        log.info("ETL run starting: mode=%s season=%s stages=%s", mode, season, stages)

        if "reference" in stages:
            self.stage_reference("all")

        if mode == "all":
            target_season: Optional[int] = None
        elif mode == "season":
            if season is None:
                raise ValueError("--season requires a year")
            target_season = season
        elif mode == "update":
            target_season = season or self.current_season()
        else:
            raise ValueError(f"unknown mode {mode}")

        rounds: Optional[dict] = None
        if mode == "update":
            rounds = self.missing_rounds(target_season)
            n_missing = sum(len(v) for v in rounds.values())
            log.info(
                "update scope: season=%s missing rounds=%d", target_season, n_missing
            )
            if n_missing == 0:
                rounds = None  # nothing missing: still refresh results/quali cheaply

        if "results" in stages:
            self.stage_results(target_season)
        if "qualifying" in stages:
            self.stage_qualifying(target_season)

        detail_rounds = rounds if mode == "update" and rounds and any(rounds.values()) else None

        if "pitstops" in stages:
            pit_min = self.pit_start if target_season is None else None
            if target_season is None or target_season >= self.pit_start:
                self.stage_pitstops(
                    season=target_season, min_season=pit_min, rounds=detail_rounds
                )
            else:
                log.info(
                    "pit stops skipped: season %s < pit_start %s",
                    target_season, self.pit_start,
                )
        if "standings" in stages:
            self.stage_standings(
                season=target_season,
                min_season=None if target_season else self.standings_since,
                rounds=detail_rounds,
            )
        if "laps" in stages:
            min_season = self.lap_start if target_season is None else None
            if target_season is None or target_season >= self.lap_start:
                self.stage_laps(
                    season=target_season, min_season=min_season, rounds=detail_rounds
                )
            else:
                log.info(
                    "laps skipped: season %s < lap_start %s",
                    target_season, self.lap_start,
                )

        summary = self.summary()
        log.info("ETL run complete: %s", summary)
        return summary

    # ----------------------------------------------------------- summary
    def summary(self) -> dict:
        from app.models import (
            DimCircuit,
            DimConstructor,
            DimDate,
            DimDriver,
            FactConstructorStanding,
            FactDriverStanding,
            FactLap,
            FactPitStop,
            FactQualifying,
        )

        def count(model) -> int:
            return int(self.session.query(func.count()).select_from(model).scalar() or 0)

        counts = {
            "dim_date": count(DimDate),
            "dim_driver": count(DimDriver),
            "dim_constructor": count(DimConstructor),
            "dim_circuit": count(DimCircuit),
            "dim_race": count(DimRace),
            "fact_race_result": count(FactRaceResult),
            "fact_qualifying": count(FactQualifying),
            "fact_lap": count(FactLap),
            "fact_pit_stop": count(FactPitStop),
            "fact_driver_standing": count(FactDriverStanding),
            "fact_constructor_standing": count(FactConstructorStanding),
        }
        counts["total_records"] = sum(counts.values())
        counts["etl_stats"] = self.stats.as_dict()
        counts["client_stats"] = dict(self.client.stats)
        return counts

    def close(self) -> None:
        self.session.close()
