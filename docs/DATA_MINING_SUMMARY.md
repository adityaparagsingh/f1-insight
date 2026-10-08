# Data Mining Summary

## Implemented Techniques

### 1. K-Means Clustering
- **Purpose**: Group drivers based on performance characteristics
- **Features**: avg_finish, avg_quali, win_rate, podium_rate, points_per_race, dnf_rate, avg_lap_seconds, avg_position_gain
- **Preprocessing**: StandardScaler normalization
- **Optimal K**: Auto-selected using Elbow method + Silhouette analysis (k=2..8)
- **Algorithm**: sklearn.cluster.KMeans with random_state=42 for reproducibility
- **Output**: Cluster assignments, centroids, PCA scatter plot data, cluster profiles
- **Endpoint**: GET /api/mining/clusters

### 2. Race Winner Prediction
- **Purpose**: Predict race winners using pre-race information only
- **Type**: Binary classification (winner = 1, others = 0)
- **Models**: Random Forest, Decision Tree, Logistic Regression
- **Anti-leakage design**: 
  - Historical averages computed from PRIOR races only (expanding means shifted)
  - Championship points before race (cumulative - current)
  - Recent form from last 5 prior races
  - No current race results, lap times, pit stops used
- **Split**: Time-based (train on earlier seasons, test on recent seasons)
- **Metrics**: Accuracy, Precision, Recall, F1, F1-macro, ROC-AUC
- **Evaluation**: Per-race top-1 picks with hit rate
- **Endpoint**: GET /api/mining/prediction

### 3. Apriori Association Rule Mining
- **Purpose**: Discover hidden patterns between race factors
- **Transactions**: One per driver-race entry
- **Discretization**: Qualifying (Q_TOP3/Q_4_10/Q_11_20/Q_21P), Grid, Constructor Tier, Pit Stops, Outcome, Position Change, Reliability, Pace
- **Algorithm**: mlxtend.frequent_patterns.apriori + association_rules
- **Metrics**: Support, Confidence, Lift, Leverage, Conviction
- **Filters**: min_support (0.03), min_confidence (0.4), min_lift (1.05) by default
- **Endpoint**: GET /api/mining/association-rules

### 4. Performance Classification
- **Purpose**: Classify race performances and driver careers
- **Formula**: score = 0.60*(1 - (pos-1)/(field_size-1)) + 0.40*(points/winner_points)
- **DNF**: Always classified as POOR
- **Thresholds**:
  - EXCELLENT: ≥ 0.75
  - STRONG: 0.50 - 0.75
  - AVERAGE: 0.25 - 0.50
  - POOR: < 0.25
- **Application**: Individual race results + driver career averages (min 10 scored races)
- **Endpoint**: GET /api/mining/classification

## OLAP Operations Implemented

1. **Roll-up**: Aggregate up hierarchies (e.g., driver→constructor→season)
2. **Drill-down**: Navigate to detailed levels (season→race→driver→lap)
3. **Slice**: Filter on single dimension
4. **Dice**: Filter on multiple dimensions simultaneously
5. **Pivot**: Cross-tabulation of measures across two dimensions

All accessible via `/api/olap/*` endpoints.
