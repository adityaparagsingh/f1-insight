"""Load layer: dimension resolution + idempotent fact upserts."""
from __future__ import annotations

from datetime import date
from typing import Any, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.models import (
    DimCircuit,
    DimConstructor,
    DimDate,
    DimDriver,
    DimRace,
)
from etl.logging_utils import get_logger
from etl.transform.common import clean_str, full_name, parse_date

log = get_logger("etl.load")


class DimensionLoader:
    """Resolves natural keys -> surrogate keys, inserting missing dimensions.

    All lookups are cached in-memory for the run; new rows are flushed and
    committed immediately so foreign keys always resolve.  Re-runs are
    idempotent because every dimension has a UNIQUE natural key and we
    SELECT before INSERT.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.date_map: dict[date, int] = {
            r.full_date: r.date_id for r in session.query(DimDate)
        }
        self.driver_map: dict[str, int] = {
            r.driver_ref: r.driver_id for r in session.query(DimDriver)
        }
        self.constructor_map: dict[str, int] = {
            r.constructor_ref: r.constructor_id for r in session.query(DimConstructor)
        }
        self.circuit_map: dict[str, int] = {
            r.circuit_ref: r.circuit_id for r in session.query(DimCircuit)
        }
        self.race_map: dict[tuple[int, int], int] = {
            (r.season, r.round): r.race_id for r in session.query(DimRace)
        }
        log.info(
            "dimension cache: dates=%d drivers=%d constructors=%d circuits=%d races=%d",
            len(self.date_map), len(self.driver_map), len(self.constructor_map),
            len(self.circuit_map), len(self.race_map),
        )

    # ------------------------------------------------------------------ date
    def ensure_date(self, d: date) -> int:
        key = d if isinstance(d, date) else parse_date(d)
        if key is None:
            raise ValueError(f"invalid date: {d!r}")
        if key in self.date_map:
            return self.date_map[key]
        row = DimDate(
            full_date=key,
            year=key.year,
            quarter=(key.month - 1) // 3 + 1,
            month=key.month,
            month_name=key.strftime("%B"),
            day=key.day,
            day_of_week=key.weekday(),
            day_name=key.strftime("%A"),
            week_of_year=int(key.strftime("%V")),
            is_weekend=key.weekday() >= 5,
        )
        self.session.add(row)
        self.session.flush()
        self.session.commit()
        self.date_map[key] = row.date_id
        return row.date_id

    # ---------------------------------------------------------------- driver
    @staticmethod
    def _driver_values(raw: dict, ref: str) -> dict:
        """Build column values from a Jolpica driver object.

        Jolpica (Ergast-compatible) uses ``givenName`` / ``familyName``;
        ``forename`` / ``surname`` are accepted as a fallback.
        """
        forename = clean_str(raw.get("givenName") or raw.get("forename")) or ""
        surname = clean_str(raw.get("familyName") or raw.get("surname")) or ""
        if not forename and not surname:
            # Last resort: derive a readable name from the stable driver ref.
            surname = ref.replace("_", " ").title()
        full = full_name(forename, surname) or surname
        number = raw.get("permanentNumber")
        try:
            number_i = int(str(number)) if number not in (None, "", "\\N") else None
        except ValueError:
            number_i = None
        return {
            "code": clean_str(raw.get("code"), 8),
            "forename": forename or surname,
            "surname": surname or forename,
            "full_name": full,
            "number": number_i,
            "date_of_birth": parse_date(raw.get("dateOfBirth")),
            "nationality": clean_str(raw.get("nationality"), 64),
            "url": clean_str(raw.get("url"), 255),
        }

    def ensure_driver(self, raw: dict, refresh: bool = False) -> Optional[int]:
        ref = clean_str(raw.get("driverId"))
        if not ref:
            return None
        existing = self.driver_map.get(ref)
        values = self._driver_values(raw, ref)
        if existing is not None:
            if refresh:
                row = self.session.get(DimDriver, existing)
                if row is not None:
                    for key, value in values.items():
                        if value not in (None, "") and getattr(row, key) != value:
                            setattr(row, key, value)
                    self.session.commit()
            return existing
        row = DimDriver(driver_ref=ref, **values)
        self.session.add(row)
        self.session.flush()
        self.session.commit()
        self.driver_map[ref] = row.driver_id
        return row.driver_id

    # ----------------------------------------------------------- constructor
    def ensure_constructor(self, raw: dict) -> Optional[int]:
        ref = clean_str(raw.get("constructorId"))
        if not ref:
            return None
        if ref in self.constructor_map:
            return self.constructor_map[ref]
        row = DimConstructor(
            constructor_ref=ref,
            name=clean_str(raw.get("name")) or ref.replace("_", " ").title(),
            nationality=clean_str(raw.get("nationality"), 64),
            url=clean_str(raw.get("url"), 255),
        )
        self.session.add(row)
        self.session.flush()
        self.session.commit()
        self.constructor_map[ref] = row.constructor_id
        return row.constructor_id

    # -------------------------------------------------------------- circuit
    def ensure_circuit(self, raw: dict) -> Optional[int]:
        ref = clean_str(raw.get("circuitId"))
        if not ref:
            return None
        if ref in self.circuit_map:
            return self.circuit_map[ref]
        loc = raw.get("Location") or {}
        from etl.transform.common import to_float

        row = DimCircuit(
            circuit_ref=ref,
            name=clean_str(raw.get("circuitName")) or ref.replace("_", " ").title(),
            location=clean_str(loc.get("locality"), 64),
            country=clean_str(loc.get("country"), 64),
            latitude=to_float(loc.get("lat")),
            longitude=to_float(loc.get("long")),
            altitude=to_float(loc.get("altitude")),
            url=clean_str(raw.get("url"), 255),
        )
        self.session.add(row)
        self.session.flush()
        self.session.commit()
        self.circuit_map[ref] = row.circuit_id
        return row.circuit_id

    # ----------------------------------------------------------------- race
    def ensure_race(
        self,
        season: Any,
        round_: Any,
        name: str,
        race_date: date,
        circuit_id: int,
        url: Optional[str] = None,
    ) -> Optional[int]:
        season_i, round_i = int(season), int(round_)
        key = (season_i, round_i)
        if key in self.race_map:
            return self.race_map[key]
        date_id = self.ensure_date(race_date)
        row = DimRace(
            race_ref=f"{season_i}-{round_i:02d}",
            season=season_i,
            round=round_i,
            name=name,
            date=race_date,
            date_id=date_id,
            circuit_id=circuit_id,
            url=clean_str(url, 255),
        )
        self.session.add(row)
        self.session.flush()
        self.session.commit()
        self.race_map[key] = row.race_id
        return row.race_id


# ============================================================================
# Generic idempotent fact upsert (MySQL INSERT ... ON DUPLICATE KEY UPDATE)
# ============================================================================
def upsert_rows(
    session: Session,
    model,
    rows: Sequence[dict],
    update_columns: Optional[Sequence[str]] = None,
    chunk_size: int = 1000,
    exclude_columns: Optional[set[str]] = None,
) -> int:
    """Upsert ``rows`` into ``model`` using its UNIQUE natural key(s).

    ``update_columns`` defaults to every provided column except the first two
    key columns passed implicitly by the caller (all columns in the row dict
    that are not part of the natural key are updated).  Returns rows written.
    """
    if not rows:
        return 0
    table = model.__tablename__
    key_cols = _unique_key_columns(model)
    excluded = set(exclude_columns or ())
    update_cols = [c for c in rows[0].keys() if c not in key_cols and c not in excluded]
    if update_columns is not None:
        update_cols = [c for c in update_columns if c in rows[0]]

    written = 0
    for start in range(0, len(rows), chunk_size):
        chunk = list(rows[start : start + chunk_size])
        stmt = mysql_insert(model).values(chunk)
        if update_cols:
            stmt = stmt.on_duplicate_key_update(
                {c: getattr(stmt.inserted, c) for c in update_cols}
            )
        result = session.execute(stmt)
        session.commit()
        written += len(chunk)
        del result
    log.info("upserted %d rows -> %s", written, table)
    return written


def _unique_key_columns(model) -> set[str]:
    """Columns of the table's named unique constraints (natural keys)."""
    cols: set[str] = set()
    for constraint in model.__table__.constraints:
        if constraint.__class__.__name__ == "UniqueConstraint":
            cols.update(c.name for c in constraint.columns)
    if not cols:
        cols = {model.__table__.primary_key.columns[0].name}
    return cols


def refresh_pit_stop_counts(session: Session) -> None:
    """Recompute fact_race_result.pit_stop_count from fact_pit_stop."""
    session.execute(
        text(
            """
            UPDATE fact_race_result f
            LEFT JOIN (
                SELECT race_id, driver_id, COUNT(*) AS cnt
                FROM fact_pit_stop
                GROUP BY race_id, driver_id
            ) p ON p.race_id = f.race_id AND p.driver_id = f.driver_id
            SET f.pit_stop_count = COALESCE(p.cnt, 0)
            """
        )
    )
    session.commit()
    log.info("pit_stop_count refreshed on fact_race_result")
