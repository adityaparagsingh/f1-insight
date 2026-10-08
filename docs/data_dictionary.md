# Data Dictionary

## Overview

This data dictionary provides detailed definitions for all tables, columns, measures, and metrics used in the F1 Insight data warehouse.

---

## Dimension Tables

### dim_date
| Column | Type | Description | Example |
|---|---|---|---|
| date_id | INT | Surrogate primary key | 12345 |
| full_date | DATE | Calendar date in YYYY-MM-DD format | 2024-03-02 |
| year | SMALLINT | Four-digit year | 2024 |
| quarter | TINYINT | Quarter of year (1-4) | 1 |
| month | TINYINT | Month number (1-12) | 3 |
| month_name | VARCHAR(12) | Full month name | March |
| day | TINYINT | Day of month (1-31) | 2 |
| day_of_week | TINYINT | Day of week: 0=Monday, 1=Tuesday, ..., 6=Sunday | 6 |
| day_name | VARCHAR(12) | Full day name | Saturday |
| week_of_year | SMALLINT | ISO 8601 week number (1-53) | 9 |
| is_weekend | TINYINT(1) | Flag: 1 if Saturday/Sunday, 0 otherwise | 1 |

---

### dim_driver
| Column | Type | Description | Example |
|---|---|---|---|
| driver_id | INT | Surrogate primary key | 44 |
| driver_ref | VARCHAR(64) | Unique natural identifier from API | "hamilton" |
| code | VARCHAR(8) | Three-letter driver code | "HAM" |
| forename | VARCHAR(64) | Driver's first/given name | "Lewis" |
| surname | VARCHAR(64) | Driver's last/family name | "Hamilton" |
| full_name | VARCHAR(128) | Concatenated full name | "Lewis Hamilton" |
| number | INT | Permanent racing number | 44 |
| date_of_birth | DATE | Driver's birth date | 1985-01-07 |
| nationality | VARCHAR(64) | Driver's nationality | "British" |
| url | VARCHAR(255) | Reference URL (Wikipedia/Ergast) | "http://en.wikipedia.org/wiki/Lewis_Hamilton" |

---

### dim_constructor
| Column | Type | Description | Example |
|---|---|---|---|
| constructor_id | INT | Surrogate primary key | 6 |
| constructor_ref | VARCHAR(64) | Unique natural identifier | "ferrari" |
| name | VARCHAR(128) | Constructor/team name | "Ferrari" |
| nationality | VARCHAR(64) | Team's nationality | "Italian" |
| url | VARCHAR(255) | Reference URL | "http://en.wikipedia.org/wiki/Scuderia_Ferrari" |

---

### dim_circuit
| Column | Type | Description | Example |
|---|---|---|---|
| circuit_id | INT | Surrogate primary key | 14 |
| circuit_ref | VARCHAR(64) | Unique natural identifier | "monza" |
| name | VARCHAR(128) | Full circuit name | "Autodromo Nazionale di Monza" |
| location | VARCHAR(64) | City or locality | "Monza" |
| country | VARCHAR(64) | Country name | "Italy" |
| latitude | DECIMAL(9,6) | Latitude in decimal degrees | 45.615600 |
| longitude | DECIMAL(9,6) | Longitude in decimal degrees | 9.281110 |
| altitude | DECIMAL(8,2) | Altitude in meters | 162.00 |
| url | VARCHAR(255) | Reference URL | "http://en.wikipedia.org/wiki/Autodromo_Nazionale_Monza" |

---

### dim_race
| Column | Type | Description | Example |
|---|---|---|---|
| race_id | INT | Surrogate primary key | 1096 |
| race_ref | VARCHAR(32) | Composite reference: season-round | "2024-16" |
| season | SMALLINT | Season year | 2024 |
| round | SMALLINT | Round number in championship | 16 |
| name | VARCHAR(128) | Grand Prix name | "Italian Grand Prix" |
| date | DATE | Race start date | 2024-09-01 |
| date_id | INT | FK to dim_date | 45678 |
| circuit_id | INT | FK to dim_circuit | 14 |
| url | VARCHAR(255) | Reference URL | "http://en.wikipedia.org/wiki/2024_Italian_Grand_Prix" |

---

## Fact Tables

### fact_race_result (Core Fact)
**Grain:** One row per driver per race

| Column | Type | Description | Example |
|---|---|---|---|
| result_id | BIGINT | Surrogate primary key | 25001 |
| race_id | INT | FK to dim_race | 1096 |
| driver_id | INT | FK to dim_driver | 44 |
| constructor_id | INT | FK to dim_constructor | 6 |
| circuit_id | INT | FK to dim_circuit | 14 |
| date_id | INT | FK to dim_date | 45678 |
| season | SMALLINT | Degenerate dimension - season year | 2024 |
| grid | INT | Starting grid position (1 = pole position) | 1 |
| position | INT | Final finishing position. NULL if DNF/DSQ | 1 |
| position_text | VARCHAR(4) | Position as text (e.g., "1", "R", "D") | "1" |
| points | DECIMAL(6,2) | Championship points awarded | 25.00 |
| laps | INT | Number of laps completed | 53 |
| time_milliseconds | BIGINT | Total race time in milliseconds | 5242411 |
| fastest_lap_rank | INT | Rank of driver's fastest lap in race | 2 |
| fastest_lap_time | VARCHAR(16) | Fastest lap time formatted | "1:21.358" |
| fastest_lap_seconds | DECIMAL(9,3) | Fastest lap time in seconds | 81.358 |
| fastest_lap_speed | DECIMAL(9,3) | Fastest lap speed (km/h) | 264.362 |
| pit_stop_count | INT | Number of pit stops (computed/loaded) | 1 |
| status | VARCHAR(48) | Finishing status (e.g., "Finished", "Retired") | "Finished" |
| position_gain | INT | Derived: grid - position. Positive = gained places | 0 |

**Business Measures:**
- Points, grid position, final position, laps, fastest lap metrics, pit stop count, position gain

---

### fact_qualifying
**Grain:** One row per driver per race's qualifying session

| Column | Type | Description | Example |
|---|---|---|---|
| qualifying_id | BIGINT | Surrogate primary key | 18001 |
| race_id | INT | FK to dim_race | 1096 |
| driver_id | INT | FK to dim_driver | 44 |
| constructor_id | INT | FK to dim_constructor | 6 |
| circuit_id | INT | FK to dim_circuit | 14 |
| date_id | INT | FK to dim_date | 45678 |
| season | SMALLINT | Degenerate dimension | 2024 |
| position | INT | Qualifying final position (1 = pole) | 1 |
| q1 | VARCHAR(16) | Q1 lap time | "1:20.123" |
| q2 | VARCHAR(16) | Q2 lap time (if reached) | "1:19.456" |
| q3 | VARCHAR(16) | Q3 lap time (if reached) | "1:18.792" |
| q1_seconds | DECIMAL(9,3) | Q1 in seconds | 80.123 |
| q2_seconds | DECIMAL(9,3) | Q2 in seconds | 79.456 |
| q3_seconds | DECIMAL(9,3) | Q3 in seconds | 78.792 |

---

### fact_lap
**Grain:** One row per driver per lap  
**Note:** Largest fact table (>500K rows)

| Column | Type | Description | Example |
|---|---|---|---|
| lap_id | BIGINT | Surrogate primary key | 1500001 |
| race_id | INT | FK to dim_race | 1096 |
| driver_id | INT | FK to dim_driver | 44 |
| constructor_id | INT | FK to dim_constructor | 6 |
| circuit_id | INT | FK to dim_circuit | 14 |
| date_id | INT | FK to dim_date | 45678 |
| season | SMALLINT | Degenerate dimension | 2024 |
| lap | INT | Lap number | 5 |
| position | INT | Position on this lap | 1 |
| lap_time | VARCHAR(16) | Lap time formatted | "1:21.500" |
| lap_milliseconds | INT | Lap time in milliseconds | 81500 |

---

### fact_pit_stop
**Grain:** One row per pit stop event

| Column | Type | Description | Example |
|---|---|---|---|
| pit_stop_id | BIGINT | Surrogate primary key | 45001 |
| race_id | INT | FK to dim_race | 1096 |
| driver_id | INT | FK to dim_driver | 44 |
| constructor_id | INT | FK to dim_constructor | 6 |
| circuit_id | INT | FK to dim_circuit | 14 |
| date_id | INT | FK to dim_date | 45678 |
| season | SMALLINT | Degenerate dimension | 2024 |
| stop_number | INT | Stop sequence number (1st, 2nd, ...) | 1 |
| lap | INT | Lap number when pit stop occurred | 24 |
| duration | DECIMAL(8,3) | Pit stop duration in seconds | 2.345 |
| duration_ms | INT | Pit stop duration in milliseconds | 2345 |

---

### fact_driver_standing
**Grain:** One row per driver per season per round (championship standings snapshot)

| Column | Type | Description | Example |
|---|---|---|---|
| standing_id | BIGINT | Surrogate primary key | 30001 |
| race_id | INT | FK to dim_race (race that updated standings) | 1096 |
| season | SMALLINT | Championship season | 2024 |
| round | SMALLINT | Round number (after which standings apply) | 16 |
| driver_id | INT | FK to dim_driver | 44 |
| constructor_id | INT | FK to dim_constructor | 6 |
| points | DECIMAL(6,2) | Cumulative championship points | 234.00 |
| position | INT | Championship position (1 = leader) | 1 |
| wins | INT | Cumulative number of wins | 8 |

---

### fact_constructor_standing
**Grain:** One row per constructor per season per round

| Column | Type | Description | Example |
|---|---|---|---|
| standing_id | BIGINT | Surrogate primary key | 28001 |
| race_id | INT | FK to dim_race | 1096 |
| season | SMALLINT | Championship season | 2024 |
| round | SMALLINT | Round number | 16 |
| constructor_id | INT | FK to dim_constructor | 6 |
| points | DECIMAL(6,2) | Cumulative constructor points | 441.00 |
| position | INT | Championship position | 1 |
| wins | INT | Cumulative number of wins | 8 |

---

### etl_run_log
| Column | Type | Description | Example |
|---|---|---|---|
| run_id | BIGINT | Surrogate primary key | 15 |
| pipeline | VARCHAR(64) | ETL stage: reference, results, qualifying, pitstops, standings, laps | "results" |
| scope | VARCHAR(128) | Run scope description | "season=2024" |
| started_at | DATETIME | Start timestamp (UTC) | 2026-10-09 10:30:00 |
| finished_at | DATETIME | End timestamp (UTC) | 2026-10-09 10:45:15 |
| status | VARCHAR(16) | Execution status: RUNNING, SUCCESS, FAILED | "SUCCESS" |
| records_extracted | INT | Count of raw records extracted | 2500 |
| records_transformed | INT | Count after transformation/cleaning | 2485 |
| records_loaded | INT | Count loaded to warehouse | 2485 |
| duplicates_removed | INT | Duplicates identified/removed | 15 |
| missing_values_fixed | INT | Missing values handled | 12 |
| errors | INT | Error count encountered | 0 |
| message | TEXT | Summary message or error details | "Loaded 2485 race results" |

---

## Computed Metrics & KPIs

### Driver Performance Metrics
| Metric | Formula | Description |
|---|---|---|
| Win Rate | (Wins / Races) × 100 | Percentage of races won |
| Podium Rate | (Podiums / Races) × 100 | Percentage of top-3 finishes |
| Points Per Race | Total Points / Races | Average points per race |
| DNF Rate | (DNFs / Races) × 100 | Percentage of non-finishes |
| Average Finish | Mean of final positions (classified only) | Lower is better |
| Average Grid | Mean of starting positions | Lower is better |
| Position Gain (Avg) | Mean of (grid - position) | Positive = overtaking ability |
| Pole Percentage | (Poles / Races) × 100 | Percentage starting from pole |

### Constructor Metrics
| Metric | Formula | Description |
|---|---|---|
| Total Wins | Sum of driver wins | Team victories |
| Total Podiums | Sum of podium finishes | Top-3 results |
| Total Points | Sum of driver points | Constructor championship points |
| Win Ratio | Team wins / Total races | Success rate |
| Reliability | (Classified / Entries) × 100 | Car reliability |

### Race Analysis Metrics
| Metric | Description |
|---|---|
| Field Size | Number of drivers classified/entered |
| Overtaking | Position changes throughout race (from lap data) |
| Pit Stop Strategy | Average stops, stop timing, durations |
| Qualifying-to-Race Correlation | Relationship between grid and final position |

---

## Data Quality Metrics

| Metric | Source | Description |
|---|---|---|
| Completeness | ETL stats | % of required fields populated |
| Uniqueness | UNIQUE constraints | No duplicate natural keys |
| Referential Integrity | FK constraints | All FKs resolve to valid parent |
| Consistency | ETL validation | Data conforms to expected ranges/formats |
| Timeliness | ETL run logs | Data freshness tracked |

---

## OLAP Dimensions & Hierarchies

### Driver Hierarchy
`Driver → Constructor` (contextual)  
`Driver → Season → Race`

### Race Hierarchy
`Season → Race → Circuit`  
`Race → Date`

### Time Hierarchy (dim_date)
`Year → Quarter → Month → Day`  
`Year → Week → Day`

### Geographic Hierarchy (dim_circuit)
`Country → Location → Circuit`

---

## Machine Learning Feature Definitions

### Clustering Features (per-driver, career aggregates)
| Feature | Source | Description |
|---|---|---|
| avg_finish | fact_race_result | Average finishing position (classified races) |
| avg_quali | fact_qualifying | Average qualifying position |
| win_rate | fact_race_result | Win percentage |
| podium_rate | fact_race_result | Podium percentage |
| points_per_race | fact_race_result | Average points per race |
| dnf_rate | fact_race_result | DNF percentage |
| avg_lap_seconds | fact_lap | Average lap time in seconds |
| avg_position_gain | fact_race_result | Average positions gained vs grid |

### Prediction Features (pre-race, anti-leakage)
| Feature | Computation | Description |
|---|---|---|
| grid | Current race | Starting position |
| quali_pos | fact_qualifying | Qualifying position |
| drv_avg_finish_prior | Expanding mean (prior races only) | Driver's historical average finish |
| drv_win_rate_prior | Expanding mean (prior races only) | Driver's historical win rate |
| drv_podium_rate_prior | Expanding mean (prior races only) | Driver's historical podium rate |
| con_avg_finish_prior | Expanding mean (prior races only) | Constructor's historical avg finish |
| circuit_avg_finish_prior | Expanding mean (prior races only) | Driver's avg finish at this circuit |
| pts_before | Cumulative - current race points | Championship points before race |
| form5_prior | Rolling mean last 5 (prior) | Recent form (avg finish last 5 races) |

**Note:** All "prior" features exclude current race data to prevent data leakage.

---

## Classification Scoring

**Performance Score Formula:**
```
score = 0.60 × (1 - (finish_position - 1)/(field_size - 1)) + 0.40 × (points / race_winner_points)
```

- `finish_position`: Final position (classified only)
- `field_size`: Number of classified finishers in race
- `points`: Points earned by driver
- `race_winner_points`: Points scored by race winner

**Thresholds:**
- EXCELLENT: score ≥ 0.75
- STRONG: 0.50 ≤ score < 0.75
- AVERAGE: 0.25 ≤ score < 0.50
- POOR: score < 0.25 (or DNF)

---

## Association Rule Discretization

| Item | Bins | Description |
|---|---|---|
| Qualifying | Q_TOP3, Q_4_10, Q_11_20, Q_21P | Qualifying position buckets |
| Grid | GRID_POLE, GRID_TOP3, GRID_4_10, GRID_11_20, GRID_21P | Starting grid buckets |
| Constructor Tier | CTOR_TIER1, CTOR_TIER2, CTOR_TIER3 | Based on end-of-season points rank (1-3, 4-10, 11+) |
| Pit Stops | PIT_NONE, PIT_ONE, PIT_TWO_PLUS | Number of pit stops |
| Outcome | OUT_WIN, OUT_PODIUM, OUT_POINTS, OUT_NO_SCORE | Race result outcome |
| Position Change | GAINED, LOST, NO_CHANGE | vs grid position |
| Reliability | CLASSIFIED, DNF | Race completion |
| Pace | FL_FAST, FL_SLOW | Fastest lap rank (≤5 or >5) |

---

## Notes

- All timestamps in ETL logs are in UTC
- DECIMAL types preserve precision for times, speeds, and points
- BIGINT used for large fact table primary keys and millisecond values
- Degenerate dimensions (season) included for query performance
- Derived metrics pre-calculated to avoid runtime computation
- Natural keys preserve traceability to source API
