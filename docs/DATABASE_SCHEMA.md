# Database Schema Documentation

## Overview

F1 Insight uses a **star schema** data warehouse design optimized for analytical queries and OLAP operations. The schema consists of 5 dimension tables, 6 fact tables, and 1 audit table.

---

## Schema Diagram

```
DIMENSIONS                    FACTS
-----------                  ------
dim_date                      fact_race_result
dim_driver                    fact_qualifying
dim_constructor               fact_pit_stop
dim_circuit                   fact_lap
dim_race                      fact_driver_standing
                              fact_constructor_standing

AUDIT
-----
etl_run_log
```

---

## Dimension Tables

### 1. dim_date
Time dimension for date-based analysis.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| date_id | INT | PK, AUTO_INCREMENT | Surrogate key |
| full_date | DATE | NOT NULL, UNIQUE | Calendar date |
| year | SMALLINT | NOT NULL | Year (e.g., 2024) |
| quarter | TINYINT | NOT NULL | Quarter (1-4) |
| month | TINYINT | NOT NULL | Month (1-12) |
| month_name | VARCHAR(12) | NOT NULL | Month name (January, etc.) |
| day | TINYINT | NOT NULL | Day of month |
| day_of_week | TINYINT | NOT NULL | Day of week (0-6, Monday=0) |
| day_name | VARCHAR(12) | NOT NULL | Day name |
| week_of_year | SMALLINT | NOT NULL | ISO week number |
| is_weekend | TINYINT(1) | NOT NULL | 1 if weekend, 0 if weekday |

**Indexes:** uq_dim_date_full, ix_dim_date_year

---

### 2. dim_driver
Driver dimension containing driver demographics and profile information.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| driver_id | INT | PK, AUTO_INCREMENT | Surrogate key |
| driver_ref | VARCHAR(64) | NOT NULL, UNIQUE | Natural key from API (e.g., "hamilton") |
| code | VARCHAR(8) | NULL | Driver code (e.g., "HAM") |
| forename | VARCHAR(64) | NOT NULL | First name |
| surname | VARCHAR(64) | NOT NULL | Last name |
| full_name | VARCHAR(128) | NOT NULL | Full name |
| number | INT | NULL | Permanent driver number |
| date_of_birth | DATE | NULL | Date of birth |
| nationality | VARCHAR(64) | NULL | Nationality |
| url | VARCHAR(255) | NULL | Wikipedia/API URL |

**Indexes:** uq_dim_driver_ref, ix_dim_driver_surname, ix_dim_driver_code

---

### 3. dim_constructor
Constructor (team) dimension.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| constructor_id | INT | PK, AUTO_INCREMENT | Surrogate key |
| constructor_ref | VARCHAR(64) | NOT NULL, UNIQUE | Natural key (e.g., "mercedes") |
| name | VARCHAR(128) | NOT NULL | Team name (e.g., "Mercedes") |
| nationality | VARCHAR(64) | NULL | Team nationality |
| url | VARCHAR(255) | NULL | Wikipedia/API URL |

**Indexes:** uq_dim_constructor_ref, ix_dim_constructor_name

---

### 4. dim_circuit
Circuit/track dimension.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| circuit_id | INT | PK, AUTO_INCREMENT | Surrogate key |
| circuit_ref | VARCHAR(64) | NOT NULL, UNIQUE | Natural key (e.g., "monza") |
| name | VARCHAR(128) | NOT NULL | Circuit name |
| location | VARCHAR(64) | NULL | City/location |
| country | VARCHAR(64) | NULL | Country |
| latitude | DECIMAL(9,6) | NULL | Geographic latitude |
| longitude | DECIMAL(9,6) | NULL | Geographic longitude |
| altitude | DECIMAL(8,2) | NULL | Altitude in meters |
| url | VARCHAR(255) | NULL | Wikipedia/API URL |

**Indexes:** uq_dim_circuit_ref, ix_dim_circuit_country

---

### 5. dim_race
Race/Grand Prix dimension (conformed dimension).

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| race_id | INT | PK, AUTO_INCREMENT | Surrogate key |
| race_ref | VARCHAR(32) | NOT NULL, UNIQUE | Composite reference (e.g., "2024-01") |
| season | SMALLINT | NOT NULL | Season year |
| round | SMALLINT | NOT NULL | Round number in season |
| name | VARCHAR(128) | NOT NULL | Race name (e.g., "Italian Grand Prix") |
| date | DATE | NOT NULL | Race date |
| date_id | INT | NOT NULL, FK -> dim_date | Foreign key to date dimension |
| circuit_id | INT | NOT NULL, FK -> dim_circuit | Foreign key to circuit dimension |
| url | VARCHAR(255) | NULL | Wikipedia/API URL |

**Constraints:** fk_dim_race_date, fk_dim_race_circuit, uq_dim_race_season_round  
**Indexes:** ix_dim_race_date, ix_dim_race_circuit

---

## Fact Tables

### 1. fact_race_result (Central Fact Table)
One row per driver per race - the core performance fact.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| result_id | BIGINT | PK, AUTO_INCREMENT | Surrogate key |
| race_id | INT | NOT NULL, FK -> dim_race | Race |
| driver_id | INT | NOT NULL, FK -> dim_driver | Driver |
| constructor_id | INT | NOT NULL, FK -> dim_constructor | Constructor |
| circuit_id | INT | NOT NULL, FK -> dim_circuit | Circuit |
| date_id | INT | NOT NULL, FK -> dim_date | Date |
| season | SMALLINT | NOT NULL | Degenerate dimension (for fast filtering) |
| grid | INT | NOT NULL | Starting position (1-based) |
| position | INT | NULL | Final position (NULL = DNF/DSQ/unclassified) |
| position_text | VARCHAR(4) | NULL | Position as text |
| points | DECIMAL(6,2) | NOT NULL, DEFAULT 0 | Championship points earned |
| laps | INT | NOT NULL, DEFAULT 0 | Laps completed |
| time_milliseconds | BIGINT | NULL | Total race time in ms |
| fastest_lap_rank | INT | NULL | Fastest lap rank in race |
| fastest_lap_time | VARCHAR(16) | NULL | Fastest lap time string |
| fastest_lap_seconds | DECIMAL(9,3) | NULL | Fastest lap time in seconds |
| fastest_lap_speed | DECIMAL(9,3) | NULL | Fastest lap speed |
| pit_stop_count | INT | NOT NULL, DEFAULT 0 | Number of pit stops (derived) |
| status | VARCHAR(48) | NOT NULL | Finishing status |
| position_gain | INT | NULL | **Derived metric:** grid - position (positive = gained places) |

**Constraints:** fk_fact_rr_*, uq_fact_race_result (race_id, driver_id), chk_fact_rr_grid >= 0  
**Indexes:** ix_fact_rr_driver, ix_fact_rr_constructor, ix_fact_rr_circuit, ix_fact_rr_date, ix_fact_rr_season, ix_fact_rr_position, ix_fact_rr_points

---

### 2. fact_qualifying
Qualifying session results (Q1, Q2, Q3).

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| qualifying_id | BIGINT | PK, AUTO_INCREMENT | Surrogate key |
| race_id | INT | NOT NULL, FK -> dim_race | Race |
| driver_id | INT | NOT NULL, FK -> dim_driver | Driver |
| constructor_id | INT | NOT NULL, FK -> dim_constructor | Constructor |
| circuit_id | INT | NOT NULL, FK -> dim_circuit | Circuit |
| date_id | INT | NOT NULL, FK -> dim_date | Date |
| season | SMALLINT | NOT NULL | Degenerate dimension |
| position | INT | NOT NULL | Qualifying position |
| q1 | VARCHAR(16) | NULL | Q1 time string |
| q2 | VARCHAR(16) | NULL | Q2 time string |
| q3 | VARCHAR(16) | NULL | Q3 time string |
| q1_seconds | DECIMAL(9,3) | NULL | Q1 time in seconds |
| q2_seconds | DECIMAL(9,3) | NULL | Q2 time in seconds |
| q3_seconds | DECIMAL(9,3) | NULL | Q3 time in seconds |

**Constraints:** fk_fact_q_*, uq_fact_qualifying (race_id, driver_id)  
**Indexes:** ix_fact_q_driver, ix_fact_q_constructor, ix_fact_q_circuit, ix_fact_q_season, ix_fact_q_position

---

### 3. fact_lap
Lap-by-lap timing data (large fact table).

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| lap_id | BIGINT | PK, AUTO_INCREMENT | Surrogate key |
| race_id | INT | NOT NULL, FK -> dim_race | Race |
| driver_id | INT | NOT NULL, FK -> dim_driver | Driver |
| constructor_id | INT | NOT NULL, FK -> dim_constructor | Constructor |
| circuit_id | INT | NOT NULL, FK -> dim_circuit | Circuit |
| date_id | INT | NOT NULL, FK -> dim_date | Date |
| season | SMALLINT | NOT NULL | Degenerate dimension |
| lap | INT | NOT NULL | Lap number |
| position | INT | NULL | Position on lap |
| lap_time | VARCHAR(16) | NULL | Lap time string |
| lap_milliseconds | INT | NULL | Lap time in ms |

**Constraints:** fk_fact_lap_*, uq_fact_lap (race_id, driver_id, lap)  
**Indexes:** ix_fact_lap_driver, ix_fact_lap_race, ix_fact_lap_season

---

### 4. fact_pit_stop
Pit stop event data.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| pit_stop_id | BIGINT | PK, AUTO_INCREMENT | Surrogate key |
| race_id | INT | NOT NULL, FK -> dim_race | Race |
| driver_id | INT | NOT NULL, FK -> dim_driver | Driver |
| constructor_id | INT | NOT NULL, FK -> dim_constructor | Constructor |
| circuit_id | INT | NOT NULL, FK -> dim_circuit | Circuit |
| date_id | INT | NOT NULL, FK -> dim_date | Date |
| season | SMALLINT | NOT NULL | Degenerate dimension |
| stop_number | INT | NOT NULL | Stop number (1st, 2nd, etc.) |
| lap | INT | NOT NULL | Lap when pit stop occurred |
| duration | DECIMAL(8,3) | NULL | Duration in seconds |
| duration_ms | INT | NULL | Duration in ms |

**Constraints:** fk_fact_ps_*, uq_fact_pit_stop (race_id, driver_id, stop_number)  
**Indexes:** ix_fact_ps_driver, ix_fact_ps_race, ix_fact_ps_season, ix_fact_ps_duration

---

### 5. fact_driver_standing
Championship standings for drivers (by round/season).

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| standing_id | BIGINT | PK, AUTO_INCREMENT | Surrogate key |
| race_id | INT | NULL, FK -> dim_race | Race (optional, for per-round) |
| season | SMALLINT | NOT NULL | Season |
| round | SMALLINT | NOT NULL, DEFAULT 0 | Round number |
| driver_id | INT | NOT NULL, FK -> dim_driver | Driver |
| constructor_id | INT | NULL, FK -> dim_constructor | Constructor |
| points | DECIMAL(6,2) | NOT NULL, DEFAULT 0 | Total points |
| position | INT | NOT NULL | Championship position |
| wins | INT | NOT NULL, DEFAULT 0 | Number of wins |

**Constraints:** fk_fact_ds_*, uq_fact_ds (season, round, driver_id)  
**Indexes:** ix_fact_ds_driver, ix_fact_ds_season, ix_fact_ds_round, ix_fact_ds_position

---

### 6. fact_constructor_standing
Championship standings for constructors (by round/season).

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| standing_id | BIGINT | PK, AUTO_INCREMENT | Surrogate key |
| race_id | INT | NULL, FK -> dim_race | Race |
| season | SMALLINT | NOT NULL | Season |
| round | SMALLINT | NOT NULL, DEFAULT 0 | Round number |
| constructor_id | INT | NOT NULL, FK -> dim_constructor | Constructor |
| points | DECIMAL(6,2) | NOT NULL, DEFAULT 0 | Total points |
| position | INT | NOT NULL | Championship position |
| wins | INT | NOT NULL, DEFAULT 0 | Number of wins |

**Constraints:** fk_fact_cs_*, uq_fact_cs (season, round, constructor_id)  
**Indexes:** ix_fact_cs_constructor, ix_fact_cs_season, ix_fact_cs_round

---

## Audit Table

### etl_run_log
Tracks ETL pipeline execution history and data quality.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| run_id | BIGINT | PK, AUTO_INCREMENT | Run identifier |
| pipeline | VARCHAR(64) | NOT NULL | Pipeline stage name (reference, results, qualifying, pitstops, standings, laps) |
| scope | VARCHAR(128) | NOT NULL | Scope of run (e.g., "season=2024") |
| started_at | DATETIME | NOT NULL | Start timestamp (UTC) |
| finished_at | DATETIME | NULL | End timestamp (UTC) |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'RUNNING' | Status (RUNNING, SUCCESS, FAILED) |
| records_extracted | INT | NOT NULL, DEFAULT 0 | Records extracted from API |
| records_transformed | INT | NOT NULL, DEFAULT 0 | Records transformed |
| records_loaded | INT | NOT NULL, DEFAULT 0 | Records loaded to warehouse |
| duplicates_removed | INT | NOT NULL, DEFAULT 0 | Duplicates removed |
| missing_values_fixed | INT | NOT NULL, DEFAULT 0 | Missing values fixed |
| errors | INT | NOT NULL, DEFAULT 0 | Error count |
| message | TEXT | NULL | Summary message or error details |

---

## Design Rationale

### Star Schema Benefits
- **Simplicity**: Easy to understand and query
- **Performance**: Denormalized structure allows fast aggregations
- **OLAP-friendly**: Supports roll-up, drill-down, slice, dice, pivot efficiently
- **Flexibility**: Easy to extend with new dimensions/measures

### Key Design Decisions

1. **Surrogate Keys**: All dimensions use AUTO_INCREMENT surrogate keys for stability
2. **Natural Keys**: Stored as UNIQUE for idempotent ETL upserts
3. **Degenerate Dimensions**: `season` is denormalized in fact tables for faster filtering
4. **Derived Metrics**: `position_gain = grid - position` pre-calculated for analytics
5. **Referential Integrity**: Foreign keys ensure data consistency
6. **Comprehensive Indexing**: Indexes on common filter/join columns
7. **Audit Trail**: ETL logging for traceability and monitoring

### Star Schema Structure
- **Fact Table**: `fact_race_result` is the central fact (grain = driver-race)
- **Supporting Facts**: Qualifying, laps, pit stops, standings provide detailed analysis
- **Dimensions**: Conformed dimensions (driver, constructor, circuit, date) shared across facts
- **Time Dimension**: `dim_date` enables temporal analysis

---

## Database Setup

### Using Docker
```bash
docker compose up -d
```

The schema is automatically loaded from `database/schema.sql` on first initialization.

### Using Alembic Migrations
```bash
cd backend
alembic upgrade head
```

### Using MySQL Directly
```bash
mysql -u root -p < database/schema.sql
```

---

## Data Volumes (Expected)
- dim_driver: ~900+ records
- dim_constructor: ~200+ records  
- dim_circuit: ~75+ records
- dim_race: ~1,100+ records (since 1950)
- dim_date: ~30,000+ records (spans F1 history)
- fact_race_result: ~25,000+ records
- fact_qualifying: ~25,000+ records
- fact_pit_stop: ~60,000+ records
- fact_lap: ~500,000+ records (largest)
- fact_driver_standing: ~40,000+ records
- fact_constructor_standing: ~30,000+ records

**Total: >10,000 records as required**
