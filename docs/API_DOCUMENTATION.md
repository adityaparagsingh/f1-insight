# API Documentation

## Overview

The F1 Insight API is a RESTful web service built with FastAPI. It provides endpoints for analytics, OLAP operations, data mining, and reference data. All responses are in JSON format.

**Base URL:** `http://127.0.0.1:8000/api`  
**Interactive Docs (Swagger):** `http://127.0.0.1:8000/docs`  
**ReDoc:** `http://127.0.0.1:8000/redoc`

---

## API Endpoints

### 1. Health & Reference

#### GET /api/health
Check API health status.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "service": "F1 INSIGHT API"
}
```

#### GET /api/reference/seasons
Get list of all seasons available in the database.

**Response:**
```json
{
  "count": 75,
  "seasons": [1950, 1951, ..., 2024]
}
```

#### GET /api/reference/drivers
Get list of drivers with filtering.

**Query Parameters:**
- `search` (string, optional): Search by name/code
- `limit` (int, default=100): Max results (1-500)
- `offset` (int, default=0): Pagination offset

**Response:**
```json
{
  "count": 100,
  "total": 900,
  "drivers": [
    {
      "driver_id": 44,
      "driver_ref": "hamilton",
      "code": "HAM",
      "full_name": "Lewis Hamilton",
      "nationality": "British"
    }
  ]
}
```

#### GET /api/reference/constructors
Get list of constructors.

#### GET /api/reference/circuits
Get list of circuits.

#### GET /api/reference/races
Get list of races with filtering.
- `season` (int, optional): Filter by season
- `circuit_id` (int, optional): Filter by circuit

---

### 2. Analytics Endpoints

Base path: `/api/analytics`

#### GET /api/analytics/overview
Get dashboard overview with key metrics and chart data.

**Query Parameters:**
- `season` (int, optional): Filter by season

**Response:**
```json
{
  "counts": {
    "seasons": 75,
    "races": 1125,
    "drivers": 900,
    "constructors": 200,
    "circuits": 75,
    "race_records": 25000,
    "total_records": 600000
  },
  "races_by_season": [...],
  "champions": [...],
  "top_drivers": [...],
  "progression": {
    "season": 2024,
    "rounds": [1,2,...,24],
    "drivers": [...]
  }
}
```

#### GET /api/analytics/drivers
List drivers with aggregated statistics.

**Query Parameters:**
- `season` (int, optional)
- `constructor_id` (int, optional)
- `search` (string, optional)
- `sort` (string, default="points"): points, wins, podiums, avg_finish
- `order` (string, default="desc"): asc or desc
- `limit` (int, default=50, max=200)
- `offset` (int, default=0)

**Response:**
```json
{
  "count": 50,
  "total": 900,
  "rows": [
    {
      "driver_id": 44,
      "name": "Lewis Hamilton",
      "code": "HAM",
      "nationality": "British",
      "races": 340,
      "wins": 103,
      "podiums": 197,
      "points": 4639.5,
      "avg_finish": 5.2,
      "dnfs": 22,
      "fastest_laps": 62
    }
  ]
}
```

#### GET /api/analytics/drivers/compare
Compare multiple drivers side-by-side.

**Query Parameters:**
- `ids` (string, required): Comma-separated driver IDs (e.g., "1,44")

#### GET /api/analytics/constructors
Constructor analytics with filtering/sorting.

#### GET /api/analytics/circuits
Circuit analytics and statistics.

#### GET /api/analytics/races
Race results overview.

**Query Parameters:**
- `season` (int, optional)
- `circuit_id` (int, optional)
- `search` (string, optional)
- `limit` (int, default=30)

#### GET /api/analytics/races/position-changes
Biggest position gains/losses.

#### GET /api/analytics/qualifying
Qualifying analytics.
- Without `race_id`: Overall qualifying summary + top qualifiers
- With `race_id`: Detailed qualifying for specific race

#### GET /api/analytics/pit-stops
Pit stop analytics with filters (season, constructor_id, circuit_id)

---

### 3. OLAP Endpoints

Base path: `/api/olap`

All OLAP operations support multi-dimensional analysis on the fact_race_result cube.

#### GET /api/olap/rollup
Aggregate up dimension hierarchies (ROLL-UP operation).

**Query Parameters:**
- `dimensions` (string, required): Comma-separated dimensions. Valid: `driver`, `constructor`, `season`, `circuit`, `race`
- `season`, `season_from`, `season_to` (int, optional): Time filters
- `constructor_id`, `circuit_id` (int, optional)
- `constructor_ids`, `circuit_ids`, `driver_ids` (string, optional): Comma-separated IDs
- `limit` (int, default=200, max=1000)

**Example:** `?dimensions=constructor,season&limit=100`

**Response:**
```json
{
  "operation": "rollup",
  "dimensions": ["constructor", "season"],
  "rows": [
    {
      "constructor": "Mercedes",
      "season": 2024,
      "races": 24,
      "wins": 9,
      "podiums": 24,
      "points": 468.0,
      "avg_finish": 4.2
    }
  ],
  "total": 150
}
```

---

#### GET /api/olap/drilldown
Navigate to more detailed levels (DRILL-DOWN operation).

**Query Parameters:**
- `level` (string, required): One of `season`, `race`, `driver`, `lap`
- `season` (int, optional)
- `race_id` (int, optional)
- `driver_id` (int, optional)
- `limit` (int, default=200)

**Example:** `?level=race&season=2024`

---

#### GET /api/olap/slice
Filter cube on single dimension (SLICE operation).

**Query Parameters:**
- `dimension` (string, required): `driver`, `constructor`, `season`, `circuit`, `race`
- `value` (string, required): Dimension ID or label value
- `group_by` (string, optional): Dimension to group results by
- `limit` (int, default=200)

**Example:** `?dimension=season&value=2024&group_by=constructor`

---

#### GET /api/olap/dice
Filter on multiple dimensions (DICE operation).

**Query Parameters:**
- `season`, `season_from`, `season_to` (int, optional)
- `constructor_ids` (string, optional): e.g., "1,6"
- `circuit_ids` (string, optional)
- `driver_ids` (string, optional)
- `group_by` (string, default="season,constructor")
- `limit` (int, default=300)

**Example:** `?constructor_ids=1,6&season_from=2020&season_to=2024&group_by=season`

---

#### GET /api/olap/pivot
Cross-tabulate two dimensions (PIVOT operation).

**Query Parameters:**
- `rows` (string, default="constructor"): Dimension for rows
- `cols` (string, default="season"): Dimension for columns
- `measure` (string, default="points"): Measure to pivot. Valid: `points`, `wins`, `podiums`, `races`, `avg_finish`, `dnfs`, `avg_position_gain`
- `season_from`, `season_to` (int, optional)
- `constructor_ids`, `circuit_ids`, `driver_ids` (string, optional)
- `limit_rows` (int, default=25)
- `limit_cols` (int, default=25)

**Response:**
```json
{
  "operation": "pivot",
  "rows_dim": "constructor",
  "cols_dim": "season",
  "measure": "points",
  "row_labels": ["Mercedes", "Red Bull", "Ferrari"],
  "col_labels": [2022, 2023, 2024],
  "matrix": [
    [515.0, 409.0, 468.0],
    [460.0, 860.0, 589.0],
    [554.0, 406.0, 652.0]
  ]
}
```

---

### 4. Data Mining Endpoints

Base path: `/api/mining`

#### GET /api/mining/clusters
K-Means clustering of drivers by performance characteristics.

**Query Parameters:**
- `k` (int, optional, 2-8): Number of clusters. If omitted, auto-selected using Elbow + Silhouette
- `min_races` (int, default=15, 5-100): Minimum career races per driver
- `force` (bool, default=false): Recompute instead of cached result

**Features used:** avg_finish, avg_quali, win_rate, podium_rate, points_per_race, dnf_rate, avg_lap_seconds, avg_position_gain

**Response:**
```json
{
  "algorithm": "K-Means",
  "k": 4,
  "k_selection": "automatic: max silhouette among k=2..8",
  "silhouette": 0.5234,
  "elbow_curve": [...],
  "sample_size": 120,
  "clusters": [
    {
      "cluster": 0,
      "size": 25,
      "centroid": {...},
      "drivers": [
        {
          "driver_id": 44,
          "name": "Lewis Hamilton",
          "code": "HAM",
          "cluster": 0,
          "races": 340,
          "x": 1.234,
          "y": -0.567,
          "avg_finish": 4.8,
          "win_rate": 30.3,
          ...
        }
      ]
    }
  ],
  "scatter": [...],
  "profile": [...]
}
```

---

#### GET /api/mining/prediction
Race winner prediction using machine learning (pre-race features only).

**Query Parameters:**
- `train_until` (int, optional): Train on seasons ≤ this year (default: 2 seasons before latest)
- `force` (bool, default=false): Recompute

**Models:** Random Forest (primary), Decision Tree, Logistic Regression  
**Leakage Prevention:** Only pre-race features; historical averages computed from prior races only

**Response:**
```json
{
  "algorithm": "Random Forest (primary) + Decision Tree + Logistic Regression",
  "task": "Binary classification: will this driver win the race?",
  "split": "time-based split: seasons <= 2022 train, > 2022 test",
  "train_size": 8500,
  "test_size": 2100,
  "models": {
    "random_forest": {
      "accuracy": 0.984,
      "precision": 0.723,
      "recall": 0.651,
      "f1": 0.685,
      "roc_auc": 0.921,
      "confusion_matrix": {"tn": 2050, "fp": 15, "fn": 18, "tp": 17}
    }
  },
  "feature_importances": [...],
  "winner_picks": {
    "model": "random_forest",
    "races": 85,
    "correct": 42,
    "hit_rate": 0.494,
    "picks": [...]
  }
}
```

---

#### GET /api/mining/association-rules
Apriori association rule mining over discretized race characteristics.

**Query Parameters:**
- `min_support` (float, default=0.03, range 0.001-0.5)
- `min_confidence` (float, default=0.4, range 0.05-1.0)
- `min_lift` (float, default=1.05, range 0.0-10.0)
- `force` (bool, default=false)

**Transactions:** One per driver-race entry with discretized items (qualifying, grid, constructor tier, pit stops, outcome, position change, reliability, pace)

**Response:**
```json
{
  "algorithm": "Apriori (MLxtend)",
  "dataset_size": 25000,
  "frequent_itemsets": 45,
  "rules": [
    {
      "antecedents": ["GRID_POLE"],
      "consequents": ["OUT_WIN"],
      "support": 0.042,
      "confidence": 0.652,
      "lift": 4.285,
      "leverage": 0.032,
      "conviction": 2.354,
      "count": 1050
    }
  ],
  "item_definitions": {...},
  "item_frequencies": [...]
}
```

---

#### GET /api/mining/classification
Performance classification using composite scoring formula.

**Query Parameters:**
- `season` (int, optional): Filter to specific season
- `force` (bool, default=false)

**Formula:** `score = 0.60*(1 - (pos-1)/(field_size-1)) + 0.40*(points/race_winner_points)`  
**Thresholds:** EXCELLENT (≥0.75), STRONG (0.50-0.75), AVERAGE (0.25-0.50), POOR (<0.25), DNF → POOR

**Response:**
```json
{
  "method": "composite performance score",
  "formula": "...",
  "thresholds": [
    {"class": "EXCELLENT", "min": 0.75, "max": 1.01},
    {"class": "STRONG", "min": 0.5, "max": 0.75},
    ...
  ],
  "distribution": {
    "EXCELLENT": {"count": 3250, "pct": 13.0},
    "STRONG": {"count": 7500, "pct": 30.0},
    ...
  },
  "by_season": [...],
  "driver_classification": [
    {
      "driver_id": 1,
      "name": "Max Verstappen",
      "code": "VER",
      "races_scored": 180,
      "avg_performance_score": 0.842,
      "class": "EXCELLENT",
      "excellent_pct": 65.5
    }
  ],
  "sample_rows": [...]
}
```

---

### 5. Insights Endpoints

Base path: `/api/insights`

#### GET /api/insights/dynamic
Generate dynamic insights based on current data.

**Query Parameters:**
- `season` (int, optional)

**Response:** Array of insight objects with type, title, description, value, etc.

**Insight Types:** trends, records, performance, correlation

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Successful request
- `400 Bad Request`: Invalid query parameters
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

**Error Response Format:**
```json
{
  "detail": "Error message describing the issue"
}
```

---

## Rate Limiting & Caching

- **ETL API calls** (to Jolpica): Rate-limited (configurable RPS), with retries and exponential backoff
- **API responses**: ML endpoints use in-memory caching (15-30 min TTL) to avoid recomputation
- **Cache keys** include relevant parameters (k, min_races, min_support, etc.)

---

## Pagination

Endpoints returning lists support:
- `limit`: Number of results per page (default varies by endpoint, max typically 200-1000)
- `offset`: Number of results to skip

Response includes `count` (returned in this page) and `total` (total matching records) where applicable.

---

## Examples

### Get top 5 drivers in 2024
```bash
curl "http://127.0.0.1:8000/api/analytics/drivers?season=2024&sort=points&limit=5"
```

### Roll-up by constructor for last 5 seasons
```bash
curl "http://127.0.0.1:8000/api/olap/rollup?dimensions=constructor,season&season_from=2020&season_to=2024"
```

### Auto-cluster drivers with min 20 races
```bash
curl "http://127.0.0.1:8000/api/mining/clusters?min_races=20"
```

### Get race winner predictions
```bash
curl "http://127.0.0.1:8000/api/mining/prediction"
```

### Association rules with stricter thresholds
```bash
curl "http://127.0.0.1:8000/api/mining/association-rules?min_support=0.05&min_confidence=0.5"
```

---

## Notes

- All numeric values are returned as numbers (integers/floats) in JSON
- Dates are returned as ISO 8601 strings (YYYY-MM-DD)
- Decimal values from database are converted to floats/numbers in API responses
- CORS is enabled for `http://localhost:5173` and `http://127.0.0.1:5173` by default
