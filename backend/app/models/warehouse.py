"""SQLAlchemy ORM models for the F1 INSIGHT star-schema data warehouse.

Table names mirror database/schema.sql exactly.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ============================================================================
# DIMENSIONS
# ============================================================================
class DimDate(Base):
    __tablename__ = "dim_date"

    date_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    quarter: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month_name: Mapped[str] = mapped_column(String(12), nullable=False)
    day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0=Mon
    day_name: Mapped[str] = mapped_column(String(12), nullable=False)
    week_of_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_weekend: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class DimDriver(Base):
    __tablename__ = "dim_driver"

    driver_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    driver_ref: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    code: Mapped[Optional[str]] = mapped_column(String(8))
    forename: Mapped[str] = mapped_column(String(64), nullable=False)
    surname: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    number: Mapped[Optional[int]] = mapped_column(Integer)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    nationality: Mapped[Optional[str]] = mapped_column(String(64))
    url: Mapped[Optional[str]] = mapped_column(String(255))


class DimConstructor(Base):
    __tablename__ = "dim_constructor"

    constructor_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    constructor_ref: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    nationality: Mapped[Optional[str]] = mapped_column(String(64))
    url: Mapped[Optional[str]] = mapped_column(String(255))


class DimCircuit(Base):
    __tablename__ = "dim_circuit"

    circuit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    circuit_ref: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(64))
    country: Mapped[Optional[str]] = mapped_column(String(64))
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6))
    altitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    url: Mapped[Optional[str]] = mapped_column(String(255))


class DimRace(Base):
    __tablename__ = "dim_race"

    race_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_ref: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    season: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    round: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"), nullable=False)
    circuit_id: Mapped[int] = mapped_column(ForeignKey("dim_circuit.circuit_id"), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(255))

    circuit: Mapped["DimCircuit"] = relationship(lazy="joined")


# ============================================================================
# FACTS
# ============================================================================
class FactRaceResult(Base):
    __tablename__ = "fact_race_result"
    __table_args__ = (UniqueConstraint("race_id", "driver_id", name="uq_fact_race_result"),)

    result_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("dim_driver.driver_id"), nullable=False)
    constructor_id: Mapped[int] = mapped_column(
        ForeignKey("dim_constructor.constructor_id"), nullable=False
    )
    circuit_id: Mapped[int] = mapped_column(ForeignKey("dim_circuit.circuit_id"), nullable=False)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"), nullable=False)
    season: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    grid: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[Optional[int]] = mapped_column(Integer)
    position_text: Mapped[Optional[str]] = mapped_column(String(4))
    points: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    laps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    time_milliseconds: Mapped[Optional[int]] = mapped_column(BigInteger)
    fastest_lap_rank: Mapped[Optional[int]] = mapped_column(Integer)
    fastest_lap_time: Mapped[Optional[str]] = mapped_column(String(16))
    fastest_lap_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 3))
    fastest_lap_speed: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 3))
    pit_stop_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(48), nullable=False)
    position_gain: Mapped[Optional[int]] = mapped_column(Integer)  # grid - position


class FactQualifying(Base):
    __tablename__ = "fact_qualifying"
    __table_args__ = (UniqueConstraint("race_id", "driver_id", name="uq_fact_qualifying"),)

    qualifying_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("dim_driver.driver_id"), nullable=False)
    constructor_id: Mapped[int] = mapped_column(
        ForeignKey("dim_constructor.constructor_id"), nullable=False
    )
    circuit_id: Mapped[int] = mapped_column(ForeignKey("dim_circuit.circuit_id"), nullable=False)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"), nullable=False)
    season: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    q1: Mapped[Optional[str]] = mapped_column(String(16))
    q2: Mapped[Optional[str]] = mapped_column(String(16))
    q3: Mapped[Optional[str]] = mapped_column(String(16))
    q1_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 3))
    q2_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 3))
    q3_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 3))


class FactLap(Base):
    __tablename__ = "fact_lap"
    __table_args__ = (UniqueConstraint("race_id", "driver_id", "lap", name="uq_fact_lap"),)

    lap_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("dim_driver.driver_id"), nullable=False)
    constructor_id: Mapped[int] = mapped_column(
        ForeignKey("dim_constructor.constructor_id"), nullable=False
    )
    circuit_id: Mapped[int] = mapped_column(ForeignKey("dim_circuit.circuit_id"), nullable=False)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"), nullable=False)
    season: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    lap: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[Optional[int]] = mapped_column(Integer)
    lap_time: Mapped[Optional[str]] = mapped_column(String(16))
    lap_milliseconds: Mapped[Optional[int]] = mapped_column(Integer)


class FactPitStop(Base):
    __tablename__ = "fact_pit_stop"
    __table_args__ = (UniqueConstraint("race_id", "driver_id", "stop_number", name="uq_fact_pit_stop"),)

    pit_stop_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("dim_driver.driver_id"), nullable=False)
    constructor_id: Mapped[int] = mapped_column(
        ForeignKey("dim_constructor.constructor_id"), nullable=False
    )
    circuit_id: Mapped[int] = mapped_column(ForeignKey("dim_circuit.circuit_id"), nullable=False)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"), nullable=False)
    season: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    stop_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lap: Mapped[int] = mapped_column(Integer, nullable=False)
    duration: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 3))
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)


class FactDriverStanding(Base):
    __tablename__ = "fact_driver_standing"
    __table_args__ = (
        UniqueConstraint("season", "round", "driver_id", name="uq_fact_ds"),
    )

    standing_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    race_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dim_race.race_id"))
    season: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    round: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    driver_id: Mapped[int] = mapped_column(ForeignKey("dim_driver.driver_id"), nullable=False)
    constructor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("dim_constructor.constructor_id")
    )
    points: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class FactConstructorStanding(Base):
    __tablename__ = "fact_constructor_standing"
    __table_args__ = (
        UniqueConstraint("season", "round", "constructor_id", name="uq_fact_cs"),
    )

    standing_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    race_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dim_race.race_id"))
    season: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    round: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    constructor_id: Mapped[int] = mapped_column(
        ForeignKey("dim_constructor.constructor_id"), nullable=False
    )
    points: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# ============================================================================
# ETL AUDIT
# ============================================================================
class EtlRunLog(Base):
    __tablename__ = "etl_run_log"

    run_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pipeline: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="RUNNING")
    records_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_transformed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_loaded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates_removed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_values_fixed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[Optional[str]] = mapped_column(Text)
