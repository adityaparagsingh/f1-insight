# Software Requirements Specification (SRS)

**Project Title:** F1 Insight: Formula 1 Performance Analytics & Data Mining System  
**Version:** 1.0.0  
**Date:** October 2026  
**Prepared For:** Academic Project  
**Prepared By:** Development Team

---

## 1. Introduction

### 1.1 Purpose
The purpose of this document is to outline the software requirements for the F1 Insight system. It provides a detailed description of the system's functionality, user interfaces, constraints, and design specifications.

### 1.2 Scope
F1 Insight is a full-stack web application that provides comprehensive analytics, data warehousing, OLAP operations, and data mining capabilities for Formula 1 racing data. It collects real historical F1 data from the Jolpica F1 API, transforms it through an ETL pipeline into a star-schema data warehouse, and presents interactive visualizations and insights.

### 1.3 Definitions, Acronyms, and Abbreviations
- **ETL**: Extract, Transform, Load
- **OLAP**: Online Analytical Processing (Roll-up, Drill-down, Slice, Dice, Pivot)
- **API**: Application Programming Interface
- **F1**: Formula 1
- **ML**: Machine Learning
- **SRS**: Software Requirements Specification
- **KDD**: Knowledge Discovery in Databases
- **CRUD**: Create, Read, Update, Delete

---

## 2. Overall Description

### 2.1 Product Perspective
F1 Insight is a standalone web application that operates as an analytical platform. It interfaces with the Jolpica F1 API (Ergast-compatible) to gather historical F1 data. The system consists of:
- A React + Vite frontend for data visualization and user interaction
- A FastAPI backend providing RESTful API services
- A MySQL data warehouse implementing a star schema
- ETL processes for data ingestion and transformation
- Machine learning modules for data mining

### 2.2 Product Functions
1. **Data Acquisition**: Collect real historical F1 data from Jolpica API
2. **ETL Pipeline**: Extract, clean, transform, and load data into data warehouse
3. **Data Warehousing**: Store data in optimized star schema with facts and dimensions
4. **Descriptive Analytics**: Driver, constructor, circuit, race, qualifying, and pit-stop analytics
5. **OLAP Operations**: Multi-dimensional analysis with roll-up, drill-down, slice, dice, pivot
6. **Predictive Analytics**: Race winner prediction using machine learning
7. **Descriptive Data Mining**: K-Means clustering and association rule mining (Apriori)
8. **Performance Classification**: Automated driver/race performance classification
9. **Interactive Dashboards**: Visualizations with filters and dynamic insights
10. **Documentation**: Comprehensive technical documentation

### 2.3 User Classes and Characteristics
- **Data Analysts**: Users who need to explore F1 statistics and trends
- **Motorsport Enthusiasts**: Fans interested in F1 performance analysis
- **Students/Researchers**: Academic users studying data warehousing and mining
- **General Users**: Anyone interested in F1 data visualization

### 2.4 Operating Environment
- **Frontend**: Modern web browsers (Chrome, Firefox, Safari, Edge) supporting ES6+
- **Backend**: Python 3.9+, FastAPI, runs on Linux/macOS/Windows
- **Database**: MySQL 8.0+
- **Hosting**: Local development environment or deployment server

### 2.5 Design and Implementation Constraints
- Must use specified tech stack (React, Vite, Python, FastAPI, MySQL, Pandas, NumPy, Scikit-learn, MLxtend, Recharts)
- Must implement proper star schema design
- Must process at least 10,000 records
- Must use real data from Jolpica API (no hard-coded statistics)
- Must implement all specified OLAP operations and data mining techniques
- Must follow F1-inspired UI design with specified color palette
- Must include all required documentation

---

## 3. Specific Requirements

### 3.1 Functional Requirements

#### FR-1: Data Collection
- FR-1.1: System shall fetch real historical F1 data from Jolpica F1 API
- FR-1.2: System shall handle API rate limiting and retries
- FR-1.3: System shall cache responses to minimize API calls
- FR-1.4: System shall handle missing/404 responses gracefully

#### FR-2: ETL Pipeline
- FR-2.1: System shall extract data for drivers, constructors, circuits, races, results, qualifying, pit stops, laps, and standings
- FR-2.2: System shall clean and validate extracted data
- FR-2.3: System shall transform data into warehouse format
- FR-2.4: System shall load data into MySQL data warehouse idempotently
- FR-2.5: System shall track ETL run statistics and data quality metrics
- FR-2.6: System shall support full load, incremental load, and season-specific load

#### FR-3: Data Warehouse Schema
- FR-3.1: System shall implement a star schema with dimension tables (dim_driver, dim_constructor, dim_circuit, dim_race, dim_date)
- FR-3.2: System shall implement fact tables (fact_race_result, fact_qualifying, fact_pit_stop, fact_lap, fact_driver_standing, fact_constructor_standing)
- FR-3.3: System shall maintain referential integrity with foreign keys
- FR-3.4: System shall include audit logging (etl_run_log)
- FR-3.5: System shall store at least 10,000 records

#### FR-4: Driver Analytics
- FR-4.1: System shall display driver profiles with career statistics
- FR-4.2: System shall show driver championship history
- FR-4.3: System shall provide driver comparison functionality
- FR-4.4: System shall filter drivers by season, constructor, etc.
- FR-4.5: System shall show win rates, podium rates, points per race, DNFs

#### FR-5: Constructor Analytics
- FR-5.1: System shall display constructor profiles and statistics
- FR-5.2: System shall show constructor championship history
- FR-5.3: System shall compare constructor performance
- FR-5.4: System shall track constructor points by season

#### FR-6: Circuit & Race Analytics
- FR-6.1: System shall display circuit information and statistics
- FR-6.2: System shall show race results by season/circuit
- FR-6.3: System shall track fastest laps and lap records
- FR-6.4: System shall analyze position changes (gains/losses)

#### FR-7: Qualifying & Pit Stop Analytics
- FR-7.1: System shall analyze qualifying performance and correlation to race results
- FR-7.2: System shall track pit stop strategies and durations
- FR-7.3: System shall correlate pit stops with race outcomes

#### FR-8: OLAP Operations
- FR-8.1: **Roll-up**: System shall aggregate data to higher hierarchy levels
- FR-8.2: **Drill-down**: System shall navigate to detailed levels (season → race → driver → lap)
- FR-8.3: **Slice**: System shall filter on a single dimension value
- FR-8.4: **Dice**: System shall filter on multiple dimensions simultaneously
- FR-8.5: **Pivot**: System shall create cross-tabulations of measures across dimensions

#### FR-9: Data Mining
- FR-9.1: **K-Means Clustering**: System shall cluster drivers based on performance metrics. Shall use Elbow method and Silhouette analysis for optimal K selection
- FR-9.2: **Race Winner Prediction**: System shall predict race winners using machine learning models (Random Forest, Decision Tree, Logistic Regression). Must use only pre-race features to avoid leakage
- FR-9.3: **Apriori Association Rules**: System shall discover association rules between race factors with support, confidence, and lift metrics
- FR-9.4: **Performance Classification**: System shall classify race performances and driver careers using composite scoring

#### FR-10: Interactive Dashboards & UI
- FR-10.1: System shall provide overview dashboard with key metrics
- FR-10.2: System shall display interactive charts (line, bar, area, scatter, pie) using Recharts
- FR-10.3: System shall include F1-inspired design with black, racing-red, white, charcoal color palette
- FR-10.4: System shall include motorsport-style timing tables
- FR-10.5: System shall include driver cards and championship standings
- FR-10.6: System shall be responsive across devices
- FR-10.7: System shall provide filtering and search capabilities
- FR-10.8: System shall display dynamically generated insights

#### FR-11: API & Integration
- FR-11.1: System shall provide RESTful API endpoints for all features
- FR-11.2: System shall support CORS for frontend integration
- FR-11.3: System shall return structured JSON responses
- FR-11.4: System shall include comprehensive API documentation

#### FR-12: Documentation
- FR-12.1: System shall include SRS document
- FR-12.2: System shall include database schema documentation
- FR-12.3: System shall include data dictionary
- FR-12.4: System shall include API documentation
- FR-12.5: System shall include README with setup instructions

### 3.2 Non-Functional Requirements

#### NFR-1: Performance
- NFR-1.1: API response times shall be < 500ms for standard queries
- NFR-1.2: ETL pipeline shall handle large datasets efficiently
- NFR-1.3: Frontend shall render charts and tables smoothly
- NFR-1.4: Database queries shall be optimized with appropriate indexes

#### NFR-2: Scalability
- NFR-2.1: System shall support growth in data volume
- NFR-2.2: Database schema shall be extensible
- NFR-2.3: API design shall follow RESTful principles

#### NFR-3: Reliability
- NFR-3.1: System shall handle errors gracefully with user-friendly messages
- NFR-3.2: ETL process shall be idempotent (safe to re-run)
- NFR-3.3: Database transactions shall ensure data consistency
- NFR-3.4: System shall validate inputs

#### NFR-4: Usability
- NFR-4.1: UI shall be intuitive and easy to navigate
- NFR-4.2: Design shall follow F1 racing aesthetics
- NFR-4.3: Interface shall be responsive
- NFR-4.4: Visualizations shall be clear and informative

#### NFR-5: Security
- NFR-5.1: Sensitive credentials shall not be hard-coded
- NFR-5.2: Environment variables shall be used for configuration
- NFR-5.3: CORS shall be properly configured
- NFR-5.4: Database access shall use parameterized queries

#### NFR-6: Maintainability
- NFR-6.1: Code shall be modular and well-structured
- NFR-6.2: Code shall follow Python/JavaScript best practices
- NFR-6.3: System shall include proper error handling and logging
- NFR-6.4: Documentation shall be comprehensive

#### NFR-7: Portability
- NFR-7.1: System shall run on major operating systems
- NFR-7.2: Dependencies shall be managed via requirements.txt and package.json
- NFR-7.3: Database setup shall be documented

---

## 4. System Architecture

### 4.1 High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React + Vite  │    │   FastAPI       │    │   MySQL         │
│   Frontend      │◄──►│   Backend       │◄──►│   Data Warehouse│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │   Jolpica F1    │
                        │   API           │
                        └─────────────────┘
```

### 4.2 Data Flow
1. ETL pipeline extracts data from Jolpica API
2. Data is cleaned, transformed, and validated
3. Transformed data is loaded into MySQL star schema
4. Backend queries data warehouse for analytics
5. Frontend consumes REST APIs and renders visualizations
6. Users interact with dashboards and explore insights

---

## 5. UI Design Specifications

### 5.1 Color Palette
- **Primary Background**: `#0a0a0c` (Black)
- **Secondary Background**: `#101013`, `#141418` (Charcoal variations)
- **Accent**: `#e10600` (Racing Red)
- **Accent Hover**: `#ff2a1f` (Bright Red)
- **Text Primary**: `#f4f4f6` (White)
- **Text Secondary**: `#b6b6c0`, `#85858f` (Gray)
- **Borders**: `#2a2a33`, `#3a3a45`

### 5.2 UI Components
- **Timing Tables**: Monospace font, red accents for leaders, zebra striping
- **Driver Cards**: Card-based layout with driver info and key stats
- **Championship Standings**: Ranked tables with position indicators
- **Telemetry Graphics**: Line/area charts styled with racing theme
- **Technical Analytics Dashboards**: Panel-based layouts with metrics cards
- **Navigation Bar**: Sticky header with F1 branding

### 5.3 Responsive Design
- Desktop: Full multi-column layouts
- Tablet: Adjusted grid, stacked panels
- Mobile: Single column, simplified navigation

---

## 6. Data Mining Methodology

### 6.1 K-Means Clustering
- **Features**: avg_finish, avg_quali, win_rate, podium_rate, points_per_race, dnf_rate, avg_lap_seconds, avg_position_gain
- **Preprocessing**: StandardScaler normalization
- **K Selection**: Elbow method (inertia) and Silhouette analysis
- **Algorithm**: K-Means with fixed random_state for reproducibility
- **Evaluation**: Silhouette score

### 6.2 Race Winner Prediction
- **Approach**: Binary classification (winner/non-winner)
- **Models**: Random Forest, Decision Tree, Logistic Regression
- **Features** (pre-race only): grid, quali_pos, drv_avg_finish_prior, drv_win_rate_prior, con_avg_finish_prior, circuit_avg_finish_prior, pts_before, form5_prior
- **Prevention of Leakage**: Historical averages computed from prior races only (shifted/expanding means); current race data excluded
- **Split**: Time-based (train on earlier seasons, test on recent seasons)
- **Metrics**: Accuracy, Precision, Recall, F1, ROC-AUC

### 6.3 Apriori Association Rule Mining
- **Transactions**: One per driver-race entry
- **Discretization**: Qualifying buckets, grid buckets, constructor tiers, pit stops, outcome, position change, reliability, pace
- **Metrics**: Support, Confidence, Lift, Leverage, Conviction
- **Library**: MLxtend

### 6.4 Performance Classification
- **Formula**: `score = 0.60*(1 - (pos-1)/(field_size-1)) + 0.40*(points/max_points)`
- **DNF Handling**: Classified as POOR
- **Thresholds**: EXCELLENT (≥0.75), STRONG (0.50-0.75), AVERAGE (0.25-0.50), POOR (<0.25)
- **Application**: Per-race results and driver career averages (min 10 races)

---

## 7. Project Deliverables

1. Complete, functional full-stack application
2. ETL pipeline with data from Jolpica API (>10,000 records)
3. Star schema data warehouse in MySQL
4. All specified analytics, OLAP, and data mining features
5. Interactive F1-inspired frontend
6. Comprehensive backend API
7. All documentation files in `/docs/`
8. README.md with setup instructions
9. Database schema and migrations
10. Test suite for backend

---

## 8. Acceptance Criteria

- [ ] System successfully extracts data from Jolpica F1 API
- [ ] ETL loads >10,000 records into data warehouse
- [ ] All dimension and fact tables properly implemented
- [ ] All 5 OLAP operations functional
- [ ] All 3 data mining techniques implemented and producing results
- [ ] Frontend connects to backend successfully
- [ ] UI matches F1-inspired design specifications
- [ ] All documentation files created and complete
- [ ] Application runs without critical errors
- [ ] Real data used (no hard-coded statistics)

---

## 9. References

- [Jolpica F1 API](https://github.com/jolpica/jolpica-f1) - Formula 1 data API
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Recharts Documentation](https://recharts.org/)
- [Scikit-learn Documentation](https://scikit-learn.org/)
- [MLxtend Documentation](http://rasbt.github.io/mlxtend/)
- [Pandas Documentation](https://pandas.pydata.org/)
