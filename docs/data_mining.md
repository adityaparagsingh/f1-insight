# F1 INSIGHT — Data Mining Documentation

Four data-mining tasks are implemented, all against the MySQL star schema, all
computed from real warehouse data (nothing hard-coded):

| Task                | Technique         | Endpoint                      |
|---------------------|-------------------|-------------------------------|
| Clustering          | K-Means + PCA     | `GET /api/mining/clusters`    |
| Winner prediction   | RF / DT / LogReg  | `GET /api/mining/prediction`  |
| Association rules   | Apriori (MLxtend) | `GET /api/mining/association-rules` |
| Classification      | Composite scoring | `GET /api/mining/classification` |

Results are cached in-process (15–30 min TTL); pass `?force=true` to recompute.

---

## 1. Clustering — K-Means driver performance groups

### Pipeline
1. Build a per-driver feature matrix from warehouse aggregates (drivers with ≥
   `min_races` career races, default 15):

   | Feature               | Definition                              |
   |-----------------------|-----------------------------------------|
   | `avg_finish`          | mean finishing position                 |
   | `avg_quali`           | mean qualifying position                |
   | `win_rate`            | % of races won                          |
   | `podium_rate`         | % of races finishing top-3              |
   | `points_per_race`     | total points ÷ races                    |
   | `dnf_rate`            | % of races not classified               |
   | `avg_lap_seconds`     | mean lap time (from `fact_lap`)         |
   | `avg_position_gain`   | mean `grid − position`                  |

   Missing lap data (pre-2015 drivers) is median-imputed; totals are coerced
   from DECIMAL to float.
2. Standardise features (`StandardScaler`).
3. **Automatic K selection**: fit K-Means for k = 2..8, record inertia (elbow)
   and silhouette score; pick the k with the highest silhouette — **or** pass
   `?k=` to force a specific k (2–8).
4. Fit the final K-Means (`random_state=42`, `n_init=10` — reproducible).
5. Project features to 2-D with PCA for the scatter plot; report centroids back
   in original units, cluster profiles and per-driver memberships.

### Request
```
GET /api/mining/clusters                     # auto k
GET /api/mining/clusters?k=4&min_races=30    # force k
GET /api/mining/clusters?force=true          # bypass cache
```

### Response (key fields)
```json
{
  "algorithm": "K-Means",
  "k": 4,
  "k_selection": "automatic: max silhouette among k=2..8",
  "elbow_curve": [{"k": 2, "inertia": 12.3, "silhouette": 0.41}, "..."],
  "silhouette": 0.47,
  "features": ["avg_finish", "...", "avg_position_gain"],
  "sample_size": 148,
  "pca_explained_variance": [0.61, 0.18],
  "overall_means": {"avg_finish": 12.4, "...": "..."},
  "clusters": [
    {"cluster": 0, "size": 35,
     "centroid": {"avg_finish": 3.1, "win_rate": 18.2, "...": "..."},
     "avg_races": 140.2,
     "drivers": [{"driver_id": 1, "name": "Max Verstappen", "code": "VER",
                  "race": 190, "x": 2.1, "y": -0.4, "win_rate": 22.1, "...": "..."}]
    }
  ],
  "profile": [
    {"cluster": 0, "vs_overall": {"win_rate": 12.1, "...": "..."},
     "standout_features": ["win_rate", "podium_rate", "avg_finish"]}
  ],
  "scatter": [{"x": 2.1, "y": -0.4, "cluster": 0, "name": "Max Verstappen",
               "code": "VER", "driver_id": 1}],
  "seed": 42
}
```
The `profile` block characterises each cluster by which features deviate most
from the overall mean — letting the UI label them (e.g. "elite winners",
"midfield", "strugglers") from the data itself.

---

## 2. Prediction — race-winner classification (pre-race features only)

### Anti-leakage design
Models are trained to answer *"will this driver win this race?"* using only
information available **before lights out**:

| Feature                    | Source / computation                                   |
|----------------------------|--------------------------------------------------------|
| `grid`                     | starting position                                     |
| `quali_pos`                | qualifying position (NULL falls back to grid)          |
| `drv_avg_finish_prior`     | driver expanding mean of prior finishes (current race excluded) |
| `drv_win_rate_prior`       | prior win rate %                                       |
| `drv_podium_rate_prior`    | prior podium rate %                                    |
| `con_avg_finish_prior`     | constructor expanding mean of prior finishes           |
| `circuit_avg_finish_prior` | driver expanding mean at the same circuit              |
| `pts_before`               | championship points accumulated before the race        |
| `form5_prior`              | mean finish over the previous ≤ 5 races                |

Explicitly **never used**: the race's final position/points, pit stops, lap
times, fastest lap, or anything produced during/after the race. DNFs count as
"last place" when building historical averages (a documented modelling choice).

### Evaluation
- Time-based split: train on seasons `≤ train_until` (default: two seasons
  before the latest), test on the remaining seasons. If the test split is too
  small it falls back to a chronological 80/20 split.
- Three classifiers: Random Forest (primary), Decision Tree, and Logistic
  Regression (standardised, balanced class weights).
- Metrics per model: accuracy, precision, recall, F1 (binary + macro),
  ROC-AUC, confusion matrix.
- Random-Forest feature importances and logistic-regression coefficients are
  reported to explain what drives wins.

### Request
```
GET /api/mining/prediction
GET /api/mining/prediction?train_until=2021
GET /api/mining/prediction?force=true
```

### Response (key fields)
```json
{
  "algorithm": "Random Forest (primary) + Decision Tree + Logistic Regression",
  "task": "Binary classification: will this driver win the race?",
  "target": "winner (position == 1)",
  "features": ["grid", "quali_pos", "..."],
  "leakage_policy": "Only pre-race features: ...",
  "split": "time-based split: seasons <= 2024 train, > 2024 test",
  "train_until": 2024,
  "sample_size": 50000, "train_size": 46000, "test_size": 4000,
  "base_rate": 0.05,
  "models": {
    "random_forest": {"accuracy": 0.91, "precision": 0.44, "recall": 0.52,
                      "f1": 0.48, "f1_macro": 0.73, "roc_auc": 0.94,
                      "confusion_matrix": {"tn": 3800, "fp": 190,
                                           "fn": 12, "tp": 30}}
  },
  "feature_importances": [{"feature": "grid", "label": "Grid position (start)",
                           "importance": 0.31}],
  "logistic_coefficients": [{"feature": "pts_before", "coefficient": -0.9}],
  "winner_picks": {
    "model": "random_forest",
    "races": 42, "correct": 22, "hit_rate": 0.52,
    "picks": [{"race_id": 321, "season": 2025, "round": 4,
               "race_name": "Japanese Grand Prix",
               "predicted_winner": "Max Verstappen", "predicted_code": "VER",
               "probability": 0.61, "actual_winner": "Max Verstappen",
               "correct": true}]
  }
}
```

---

## 3. Association rules — Apriori

Every **transaction** is one driver-race entry (`fact_race_result` joined with
`fact_qualifying`). Items are symbolic bins derived from the data:

| Group            | Items                                                       |
|------------------|-------------------------------------------------------------|
| qualifying       | `Q_TOP3`, `Q_4_10`, `Q_11_20`, `Q_21P`                      |
| grid             | `GRID_POLE`, `GRID_TOP3`, `GRID_4_10`, `GRID_11_20`, `GRID_21P` |
| constructor tier | `CTOR_TIER1/2/3` (end-of-season points rank 1–3 / 4–10 / 11+) |
| pit stops        | `PIT_NONE`, `PIT_ONE`, `PIT_TWO_PLUS`                       |
| outcome          | `OUT_WIN`, `OUT_PODIUM`, `OUT_POINTS`, `OUT_NO_SCORE`       |
| position change  | `GAINED`, `LOST`, `NO_CHANGE` (`position_gain` sign)        |
| reliability      | `CLASSIFIED`, `DNF`                                         |
| pace             | `FL_FAST` (fastest-lap rank ≤ 5), `FL_SLOW`                 |

Rules are discovered by MLxtend's `apriori` + `association_rules`
(confidence metric) and filtered by **support / confidence / lift** query
parameters. Self-referencing rules (overlapping antecedent/consequent) are
dropped; results are sorted by lift/confidence and capped at 60 rules.

### Request
```
GET /api/mining/association-rules
GET /api/mining/association-rules?min_support=0.05&min_confidence=0.5&min_lift=1.2
```

### Response (key fields)
```json
{
  "algorithm": "Apriori (MLxtend)",
  "dataset_size": 50000,
  "transaction_definition": "one transaction per driver-race entry",
  "item_definitions": {"qualifying": "...", "...": "..."},
  "item_count": 24,
  "frequent_itemsets": 310,
  "parameters": {"min_support": 0.03, "min_confidence": 0.4, "min_lift": 1.05},
  "rule_count": 22,
  "rules": [
    {"antecedents": ["GRID_POLE", "CTOR_TIER1"],
     "consequents": ["OUT_PODIUM"],
     "support": 0.045, "confidence": 0.82, "lift": 2.4,
     "leverage": 0.002, "conviction": 3.1, "count": 2250}
  ],
  "item_frequencies": [{"item": "CLASSIFIED", "count": 47000, "frequency": 0.94}]
}
```

---

## 4. Classification — E/S/A/P performance scoring

### Formula (documented, data-driven)
For every **classified** result:

```
field_size   = number of classified finishers in the race
max_points   = points scored by the race winner

performance_score =
    0.60 * (1 − (position − 1) / (field_size − 1))   # track position component
  + 0.40 * (points / max_points)                     # championship value component
```

**Classification thresholds** (E/S/A/P):

| Class      | Score range        |
|------------|--------------------|
| EXCELLENT  | score ≥ 0.75       |
| STRONG     | 0.50 ≤ score < 0.75|
| AVERAGE    | 0.25 ≤ score < 0.50|
| POOR       | score < 0.25       |

A **Did-Not-Finish** (`position IS NULL`) is always classed **POOR**.

Driver career classification uses the driver's **mean** performance score over
≥ 10 scored races with the same thresholds.

### Request
```
GET /api/mining/classification
GET /api/mining/classification?season=2024
```

### Response (key fields)
```json
{
  "method": "composite performance score",
  "formula": "score = 0.60 * (1 - (finish-1)/(field_size-1)) + 0.40 * (points / race_winner_points); DNF -> POOR",
  "thresholds": [
    {"class": "EXCELLENT", "min": 0.75, "max": 1.01},
    {"class": "STRONG", "min": 0.5, "max": 0.75},
    {"class": "AVERAGE", "min": 0.25, "max": 0.5},
    {"class": "POOR", "min": -0.01, "max": 0.25}
  ],
  "samples_scanned": 26000,
  "distribution": {
    "EXCELLENT": {"count": 1200, "pct": 4.6},
    "STRONG": {"count": 3200, "pct": 12.3},
    "AVERAGE": {"count": 6000, "pct": 23.1},
    "POOR": {"count": 15600, "pct": 60.0}
  },
  "by_season": [
    {"season": 2010, "EXCELLENT": 41, "STRONG": 96, "AVERAGE": 180,
     "POOR": 320, "total": 637}
  ],
  "driver_classification": [
    {"driver_id": 1, "name": "Lewis Hamilton", "code": "HAM",
     "races_scored": 340, "avg_performance_score": 0.71,
     "class": "STRONG", "excellent_pct": 52.1}
  ],
  "sample_rows": [
    {"season": 2024, "race_name": "Bahrain Grand Prix", "driver": "Max Verstappen",
     "code": "VER", "constructor": "Red Bull", "grid": 1, "position": 1,
     "points": 25, "status": "Finished", "performance_score": 1.0,
     "class": "EXCELLENT"}
  ]
}
```

---

## 5. Caching, reproducibility & ethics notes

- **Reproducibility**: all scikit-learn models use `random_state=42`;
  results are computed from the warehouse at request time.
- **Caches**: clustering 15 min, prediction/association/classification 30 min.
  `?force=true` recomputes immediately (used after a fresh ETL load).
- **E/S/A/P**: labels are surfaced for transparency — the four classes,
  their score ranges and the formula are returned in every response so users
  can audit the classification.
- **Ethical / statistical caveats** (mirrored in `docs/SRS.md` §17–19):
  prediction accuracy is a modelling artefact (F1 is dominated by grid and car
  performance); association rules show correlation, not causation.