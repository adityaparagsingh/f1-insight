"""Warehouse schema + data-integrity tests (require a reachable MySQL)."""
from __future__ import annotations

from sqlalchemy import text

STAR_SCHEMA_TABLES = {
    "dim_date", "dim_driver", "dim_constructor", "dim_circuit", "dim_race",
    "fact_race_result", "fact_qualifying", "fact_lap", "fact_pit_stop",
    "fact_driver_standing", "fact_constructor_standing",
}


def test_expected_tables_exist(db):
    rows = db.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = DATABASE()"
    )).fetchall()
    present = {r[0] for r in rows}
    missing = STAR_SCHEMA_TABLES - present
    assert not missing, f"missing star-schema tables: {sorted(missing)}"


def test_reference_dimensions_are_populated(db):
    for table, minimum in (
        ("dim_driver", 100),
        ("dim_constructor", 20),
        ("dim_circuit", 10),
        ("dim_race", 100),
    ):
        count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        assert count >= minimum, f"{table} has only {count} rows"


def test_race_results_loaded(db):
    count = db.execute(text("SELECT COUNT(*) FROM fact_race_result")).scalar()
    assert count > 0


def test_race_results_have_no_orphan_dimension_keys(db):
    orphan = db.execute(text(
        """
        SELECT COUNT(*) FROM fact_race_result f
        LEFT JOIN dim_driver d ON d.driver_id = f.driver_id
        LEFT JOIN dim_race r ON r.race_id = f.race_id
        LEFT JOIN dim_constructor c ON c.constructor_id = f.constructor_id
        LEFT JOIN dim_circuit ci ON ci.circuit_id = f.circuit_id
        WHERE d.driver_id IS NULL OR r.race_id IS NULL
           OR c.constructor_id IS NULL OR ci.circuit_id IS NULL
        """
    )).scalar()
    assert orphan == 0


def test_position_gain_matches_grid_minus_position(db):
    mismatches = db.execute(text(
        """
        SELECT COUNT(*) FROM fact_race_result
        WHERE grid > 0 AND position IS NOT NULL
          AND position_gain IS NOT NULL
          AND position_gain <> grid - position
        """
    )).scalar()
    assert mismatches == 0


def test_fact_rows_reference_valid_races(db):
    for table in ("fact_qualifying", "fact_pit_stop", "fact_lap",
                  "fact_driver_standing", "fact_constructor_standing"):
        orphan = db.execute(text(
            f"""
            SELECT COUNT(*) FROM {table} t
            LEFT JOIN dim_race r ON r.race_id = t.race_id
            WHERE t.race_id IS NOT NULL AND r.race_id IS NULL
            """
        )).scalar()
        assert orphan == 0, f"{table} has {orphan} rows with unknown race_id"


def test_winner_exists_for_every_loaded_race(db):
    no_winner = db.execute(text(
        """
        SELECT COUNT(*) FROM (
            SELECT f.race_id
            FROM fact_race_result f
            GROUP BY f.race_id
            HAVING SUM(f.position = 1) = 0
        ) x
        """
    )).scalar()
    assert no_winner == 0, f"{no_winner} races loaded without a winner"
    # historical shared-drive races legitimately list two drivers at P1;
    # ensure the vast majority of races resolve to a single winner
    multi_winner = db.execute(text(
        """
        SELECT COUNT(*) FROM (
            SELECT f.race_id
            FROM fact_race_result f
            GROUP BY f.race_id
            HAVING SUM(f.position = 1) > 1
        ) x
        """
    )).scalar()
    total = db.execute(text("SELECT COUNT(DISTINCT race_id) FROM fact_race_result")).scalar()
    # shared-drive races are genuine historical data (e.g. 1956 Argentina);
    # allow a tiny handful but never a significant share
    assert multi_winner <= max(5, total // 200), f"{multi_winner} races share P1"
