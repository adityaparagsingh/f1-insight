"""OLAP operations on the star schema (ROLAP over MySQL).

Operations
----------
rollup    — aggregate up a hierarchy (driver -> constructor -> season, ...)
drilldown — descend a hierarchy (season -> race -> driver -> lap)
slice     — filter the cube on ONE dimension
dice      — filter the cube on MULTIPLE dimensions
pivot     — cross-tabulate two dimensions with a chosen measure

The cube is fact_race_result conformed with dim_driver / dim_constructor /
dim_circuit / dim_race (lap drill-down switches to fact_lap).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.services.sqlutil import fetch_all, fetch_one

# ---------------------------------------------------------------- dimensions
DIMENSIONS = {
    "driver": ("d.driver_id", "d.full_name", "d.code"),
    "constructor": ("c.constructor_id", "c.name", "NULL"),
    "season": ("f.season", "CAST(f.season AS CHAR)", "NULL"),
    "circuit": ("ci.circuit_id", "ci.name", "NULL"),
    "race": ("r.race_id", "r.name", "NULL"),
}

ALIASES = {"driver": "driver", "constructor": "constructor", "season": "season",
           "circuit": "circuit", "race": "race"}

MEASURE_SELECT = """
    COUNT(*)                                              AS races,
    SUM(f.position = 1)                                   AS wins,
    SUM(f.position <= 3)                                  AS podiums,
    ROUND(COALESCE(SUM(f.points), 0), 2)                  AS points,
    ROUND(AVG(CASE WHEN f.position IS NOT NULL THEN f.position END), 2) AS avg_finish,
    ROUND(AVG(NULLIF(f.grid, 0)), 2)                      AS avg_grid,
    SUM(f.position IS NULL)                               AS dnfs,
    ROUND(SUM(f.position IS NULL) / COUNT(*), 3)          AS dnf_rate,
    ROUND(AVG(f.position_gain), 2)                        AS avg_position_gain,
    ROUND(AVG(f.pit_stop_count), 2)                       AS avg_pit_stops
"""

FACT_FROM = """
    FROM fact_race_result f
    JOIN dim_race r        ON r.race_id = f.race_id
    JOIN dim_driver d      ON d.driver_id = f.driver_id
    JOIN dim_constructor c ON c.constructor_id = f.constructor_id
    JOIN dim_circuit ci    ON ci.circuit_id = f.circuit_id
"""


class CubeFilter:
    """Builds a WHERE clause for slice/dice from validated inputs."""

    def __init__(
        self,
        season: Optional[int] = None,
        season_from: Optional[int] = None,
        season_to: Optional[int] = None,
        driver_id: Optional[int] = None,
        constructor_id: Optional[int] = None,
        circuit_id: Optional[int] = None,
        constructor_ids: Optional[list[int]] = None,
        circuit_ids: Optional[list[int]] = None,
        driver_ids: Optional[list[int]] = None,
    ) -> None:
        self.conds: list[str] = []
        self.params: dict = {}

        if season is not None:
            self.conds.append("f.season = :season")
            self.params["season"] = season
        if season_from is not None:
            self.conds.append("f.season >= :season_from")
            self.params["season_from"] = season_from
        if season_to is not None:
            self.conds.append("f.season <= :season_to")
            self.params["season_to"] = season_to
        if driver_id is not None:
            self.conds.append("f.driver_id = :driver_id")
            self.params["driver_id"] = driver_id
        if constructor_id is not None:
            self.conds.append("f.constructor_id = :constructor_id")
            self.params["constructor_id"] = constructor_id
        if circuit_id is not None:
            self.conds.append("f.circuit_id = :circuit_id")
            self.params["circuit_id"] = circuit_id
        for name, col, values in (
            ("driver_ids", "f.driver_id", driver_ids),
            ("constructor_ids", "f.constructor_id", constructor_ids),
            ("circuit_ids", "f.circuit_id", circuit_ids),
        ):
            if values:
                ph = []
                for i, v in enumerate(values):
                    key = f"{name}_{i}"
                    ph.append(f":{key}")
                    self.params[key] = int(v)
                self.conds.append(f"{col} IN ({','.join(ph)})")

    @property
    def where(self) -> str:
        return (" WHERE " + " AND ".join(self.conds)) if self.conds else ""

    @property
    def active(self) -> dict:
        return {k: v for k, v in self.params.items() if not k.endswith(("_0", "_1", "_2", "_3"))}


def _group_clause(dimensions: list[str]) -> tuple[str, str]:
    """SELECT + GROUP BY fragments for the given dimension list."""
    select_cols, group_cols = [], []
    for dim in dimensions:
        if dim not in DIMENSIONS:
            raise ValueError(f"unknown dimension '{dim}'. allowed: {sorted(DIMENSIONS)}")
        key_col, label_col, code_col = DIMENSIONS[dim]
        alias = dim
        select_cols.append(f"{key_col} AS {alias}_id")
        select_cols.append(f"{label_col} AS {alias}_name")
        if code_col != "NULL":
            select_cols.append(f"{code_col} AS {alias}_code")
        group_cols.append(key_col)
        if dim == "season":
            pass  # season key is already the label
    return ",\n           ".join(select_cols), ",\n           ".join(dict.fromkeys(group_cols))


def rollup(
    session: Session,
    dimensions: list[str],
    flt: Optional[CubeFilter] = None,
    limit: int = 500,
) -> dict:
    """ROLL-UP: aggregate from low-level dimensions up to higher levels."""
    flt = flt or CubeFilter()
    select_cols, group_cols = _group_clause(dimensions)
    rows = fetch_all(
        session,
        f"""
        SELECT {select_cols},
               {MEASURE_SELECT}
        {FACT_FROM}
        {flt.where}
        GROUP BY {group_cols}
        ORDER BY points DESC
        LIMIT :limit
        """,
        **{**flt.params, "limit": int(limit)},
    )
    return {
        "operation": "rollup",
        "dimensions": dimensions,
        "filters": flt.active,
        "row_count": len(rows),
        "rows": rows,
    }


DRILL_LEVELS = ["season", "race", "driver", "lap"]


def drilldown(
    session: Session,
    level: str,
    season: Optional[int] = None,
    race_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    limit: int = 200,
) -> dict:
    """DRILL-DOWN: season -> race -> driver -> lap (next level rows)."""
    if level not in DRILL_LEVELS:
        raise ValueError(f"unknown level '{level}'. allowed: {DRILL_LEVELS}")

    conds, params = [], {}
    if season is not None:
        conds.append("f.season = :season")
        params["season"] = season
    if race_id is not None:
        conds.append("f.race_id = :race_id")
        params["race_id"] = race_id
    if driver_id is not None:
        conds.append("f.driver_id = :driver_id")
        params["driver_id"] = driver_id
    where = (" WHERE " + " AND ".join(conds)) if conds else ""

    if level == "season":
        rows = fetch_all(
            session,
            f"""
            SELECT f.season AS season_id, f.season AS season_name,
                   COUNT(DISTINCT f.race_id) AS races,
                   COUNT(*) AS entries,
                   SUM(f.position = 1) AS wins,
                   ROUND(COALESCE(SUM(f.points), 0), 2) AS points,
                   ROUND(AVG(CASE WHEN f.position IS NOT NULL THEN f.position END), 2) AS avg_finish,
                   SUM(f.position IS NULL) AS dnfs
            FROM fact_race_result f
            GROUP BY f.season ORDER BY f.season
            """,
        )
        next_level = "race"
        needed = []

    elif level == "race":
        rows = fetch_all(
            session,
            f"""
            SELECT r.race_id AS race_id,
                   CONCAT(r.season, ' R', r.round, ' — ', r.name) AS race_name,
                   r.season, r.round, r.date,
                   ci.name AS circuit,
                   COUNT(*) AS entries,
                   SUM(f.position = 1) AS wins_dummy,
                   ROUND(COALESCE(SUM(f.points), 0), 2) AS points,
                   SUM(f.position IS NULL) AS dnfs,
                   (SELECT d2.full_name FROM fact_race_result fw
                    JOIN dim_driver d2 ON d2.driver_id = fw.driver_id
                    WHERE fw.race_id = r.race_id AND fw.position = 1) AS winner
            FROM fact_race_result f
            JOIN dim_race r ON r.race_id = f.race_id
            JOIN dim_circuit ci ON ci.circuit_id = f.circuit_id
            {where}
            GROUP BY r.race_id, r.season, r.round, r.date, r.name, ci.name
            ORDER BY r.season DESC, r.round DESC
            LIMIT :limit
            """,
            **{**params, "limit": int(limit)},
        )
        for row in rows:
            row.pop("wins_dummy", None)
        next_level = "driver"
        needed = [k for k in ("season", "race_id") if k not in params]

    elif level == "driver":
        rows = fetch_all(
            session,
            f"""
            SELECT d.driver_id AS driver_id, d.full_name AS driver_name, d.code AS driver_code,
                   c.name AS constructor,
                   COUNT(*) AS races,
                   SUM(f.position = 1) AS wins,
                   SUM(f.position <= 3) AS podiums,
                   ROUND(COALESCE(SUM(f.points), 0), 2) AS points,
                   ROUND(AVG(CASE WHEN f.position IS NOT NULL THEN f.position END), 2) AS avg_finish,
                   ROUND(AVG(NULLIF(f.grid, 0)), 2) AS avg_grid,
                   SUM(f.position IS NULL) AS dnfs,
                   ROUND(AVG(f.position_gain), 2) AS avg_position_gain
            FROM fact_race_result f
            JOIN dim_driver d ON d.driver_id = f.driver_id
            JOIN dim_constructor c ON c.constructor_id = f.constructor_id
            {where}
            GROUP BY d.driver_id, d.full_name, d.code, c.name
            ORDER BY points DESC
            LIMIT :limit
            """,
            **{**params, "limit": int(limit)},
        )
        next_level = "lap"
        needed = [k for k in ("season", "race_id") if k not in params]

    else:  # lap
        if race_id is None:
            raise ValueError("drill-down to lap requires race_id")
        lap_conds = ["l.race_id = :race_id"]
        if driver_id is not None:
            lap_conds.append("l.driver_id = :driver_id")
            params["driver_id"] = driver_id
        lap_where = " AND ".join(lap_conds)
        params["limit"] = int(min(limit, 2000))
        rows = fetch_all(
            session,
            f"""
            SELECT l.lap AS lap_id,
                   CONCAT('LAP ', l.lap) AS lap_name,
                   l.position, l.lap_time, l.lap_milliseconds,
                   d.full_name AS driver, c.name AS constructor
            FROM fact_lap l
            JOIN dim_driver d ON d.driver_id = l.driver_id
            JOIN dim_constructor c ON c.constructor_id = l.constructor_id
            WHERE {lap_where}
            ORDER BY d.driver_id, l.lap
            LIMIT :limit
            """,
            **params,
        )
        next_level = None
        needed = []

    return {
        "operation": "drilldown",
        "level": level,
        "next_level": next_level,
        "required_filters": needed,
        "filters": {"season": season, "race_id": race_id, "driver_id": driver_id},
        "row_count": len(rows),
        "rows": rows,
    }


def slice(
    session: Session,
    dimension: str,
    value: str,
    group_by: Optional[str] = None,
    limit: int = 200,
) -> dict:
    """SLICE: fix ONE dimension to a value, view the remaining cube."""
    if dimension not in DIMENSIONS:
        raise ValueError(f"unknown dimension '{dimension}'. allowed: {sorted(DIMENSIONS)}")

    col_map = {"driver": "f.driver_id", "constructor": "f.constructor_id",
               "season": "f.season", "circuit": "f.circuit_id", "race": "f.race_id"}
    dim_col = col_map[dimension]
    label_expr = {"driver": "d.full_name", "constructor": "c.name",
                  "season": "CAST(f.season AS CHAR)", "circuit": "ci.name",
                  "race": "r.name"}[dimension]

    # value may be a surrogate id or an exact dimension label
    match = f"({dim_col} = :raw_v OR {label_expr} = :raw_v)"
    params_raw = {"raw_v": value}

    totals = fetch_one(
        session,
        f"""
        SELECT COUNT(*) AS entries,
               COUNT(DISTINCT f.race_id) AS races,
               SUM(f.position = 1) AS wins,
               SUM(f.position <= 3) AS podiums,
               ROUND(COALESCE(SUM(f.points), 0), 2) AS points,
               ROUND(AVG(CASE WHEN f.position IS NOT NULL THEN f.position END), 2) AS avg_finish,
               SUM(f.position IS NULL) AS dnfs
        {FACT_FROM}
        WHERE {match}
        """,
        **params_raw,
    )

    # breakdown by another dimension (default season)
    break_dim = group_by or ("season" if dimension != "season" else "constructor")
    if break_dim not in DIMENSIONS:
        raise ValueError(f"unknown group_by '{break_dim}'")
    b_key, b_label, _ = DIMENSIONS[break_dim]
    breakdown = fetch_all(
        session,
        f"""
        SELECT {b_label} AS group_value, COUNT(*) AS entries,
               SUM(f.position = 1) AS wins,
               ROUND(COALESCE(SUM(f.points), 0), 2) AS points,
               ROUND(AVG(CASE WHEN f.position IS NOT NULL THEN f.position END), 2) AS avg_finish
        {FACT_FROM}
        WHERE {match}
        GROUP BY {b_key}
        ORDER BY points DESC
        LIMIT :limit
        """,
        **{**params_raw, "limit": int(limit)},
    )

    return {
        "operation": "slice",
        "dimension": dimension,
        "value": value,
        "group_by": break_dim,
        "totals": totals,
        "breakdown": breakdown,
    }


def dice(
    session: Session,
    flt: CubeFilter,
    group_by: Optional[list[str]] = None,
    limit: int = 500,
) -> dict:
    """DICE: filter on MULTIPLE dimensions, aggregate the sub-cube."""
    group_by = group_by or ["season", "constructor"]
    select_cols, group_cols = _group_clause(group_by)
    rows = fetch_all(
        session,
        f"""
        SELECT {select_cols},
               {MEASURE_SELECT}
        {FACT_FROM}
        {flt.where}
        GROUP BY {group_cols}
        ORDER BY points DESC
        LIMIT :limit
        """,
        **{**flt.params, "limit": int(limit)},
    )
    totals = fetch_one(
        session,
        f"""
        SELECT COUNT(*) AS entries, SUM(f.position = 1) AS wins,
               SUM(f.position <= 3) AS podiums,
               ROUND(COALESCE(SUM(f.points), 0), 2) AS points
        FROM fact_race_result f
        {flt.where}
        """,
        **flt.params,
    )
    return {
        "operation": "dice",
        "group_by": group_by,
        "filters": flt.active,
        "totals": totals,
        "row_count": len(rows),
        "rows": rows,
    }


MEASURE_FUNCS = {
    "points": "COALESCE(SUM(f.points), 0)",
    "wins": "SUM(f.position = 1)",
    "podiums": "SUM(f.position <= 3)",
    "races": "COUNT(*)",
    "avg_finish": "AVG(CASE WHEN f.position IS NOT NULL THEN f.position END)",
    "dnfs": "SUM(f.position IS NULL)",
    "avg_position_gain": "AVG(f.position_gain)",
}


def pivot(
    session: Session,
    rows_dim: str = "constructor",
    cols_dim: str = "season",
    measure: str = "points",
    flt: Optional[CubeFilter] = None,
    limit_rows: int = 30,
    limit_cols: int = 30,
) -> dict:
    """PIVOT: cross-tabulate two dimensions with one measure."""
    for name, dim in (("rows_dim", rows_dim), ("cols_dim", cols_dim)):
        if dim not in DIMENSIONS:
            raise ValueError(f"unknown {name} '{dim}'. allowed: {sorted(DIMENSIONS)}")
    if measure not in MEASURE_FUNCS:
        raise ValueError(f"unknown measure '{measure}'. allowed: {sorted(MEASURE_FUNCS)}")
    if rows_dim == cols_dim:
        raise ValueError("rows_dim and cols_dim must differ")

    flt = flt or CubeFilter()
    r_key, r_label, r_code = DIMENSIONS[rows_dim]
    c_key, c_label, _ = DIMENSIONS[cols_dim]
    agg = MEASURE_FUNCS[measure]

    # driver rows carry an extra code column; others do not
    if r_code != "NULL":
        code_select = f", {r_code} AS row_code"
        code_group = f", {r_code}"
    else:
        code_select = ""
        code_group = ""

    # restrict columns to top seasons/values by total so wide tables stay sane
    col_rows = fetch_all(
        session,
        f"""
        SELECT {c_key} AS col_key, {c_label} AS col_label
        {FACT_FROM}{flt.where}
        GROUP BY {c_key}, {c_label}
        ORDER BY COUNT(*) DESC
        LIMIT :limit_cols
        """,
        **{**flt.params, "limit_cols": int(limit_cols)},
    )
    row_rows = fetch_all(
        session,
        f"""
        SELECT {r_key} AS row_key, {r_label} AS row_label{code_select}
        {FACT_FROM}{flt.where}
        GROUP BY {r_key}, {r_label}{code_group}
        ORDER BY {agg} DESC
        LIMIT :limit_rows
        """,
        **{**flt.params, "limit_rows": int(limit_rows)},
    )

    if not col_rows or not row_rows:
        return {"operation": "pivot", "rows_dim": rows_dim, "cols_dim": cols_dim,
                "measure": measure, "columns": [], "rows": [], "values": []}

    col_keys = [c["col_key"] for c in col_rows]
    row_keys = [r["row_key"] for r in row_rows]

    # pull the whole cross-tab in one query, then arrange in Python
    ph_col = ",".join(f":ck{i}" for i in range(len(col_keys)))
    ph_row = ",".join(f":rk{i}" for i in range(len(row_keys)))
    cparams = {f"ck{i}": v for i, v in enumerate(col_keys)}
    rparams = {f"rk{i}": v for i, v in enumerate(row_keys)}
    cells = fetch_all(
        session,
        f"""
        SELECT {r_key} AS row_key, {c_key} AS col_key, {agg} AS value
        {FACT_FROM}
        {flt.where + (' AND ' if flt.conds else ' WHERE ')}
            {r_key} IN ({ph_row}) AND {c_key} IN ({ph_col})
        GROUP BY {r_key}, {c_key}
        """,
        **{**flt.params, **cparams, **rparams},
    )
    lookup = {(c["row_key"], c["col_key"]): float(c["value"] or 0) for c in cells}

    values = []
    for rk in row_keys:
        values.append([round(lookup.get((rk, ck), 0), 2) for ck in col_keys])

    row_totals = [round(sum(v), 2) for v in values]
    col_totals = [
        round(sum(values[i][j] for i in range(len(row_keys))), 2)
        for j in range(len(col_keys))
    ]

    return {
        "operation": "pivot",
        "rows_dim": rows_dim,
        "cols_dim": cols_dim,
        "measure": measure,
        "filters": flt.active,
        "columns": [c["col_label"] for c in col_rows],
        "rows": [
            {"key": row_rows[i]["row_key"], "label": row_rows[i]["row_label"],
             **({"code": row_rows[i]["row_code"]} if row_rows[i].get("row_code") else {})}
            for i in range(len(row_keys))
        ],
        "values": values,
        "row_totals": row_totals,
        "col_totals": col_totals,
    }
