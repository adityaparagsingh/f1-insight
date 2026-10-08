# F1 Insight: Formula 1 Performance Analytics & Data Mining System

A comprehensive full-stack application for Formula 1 performance analytics, data warehousing, OLAP operations, and data mining. Built with modern technologies and inspired by Formula 1 racing aesthetics.

## 🚀 Tech Stack

### Frontend
- **React + Vite** - Modern UI framework with fast build tooling
- **JavaScript** - Core language
- **Plain CSS** - Custom F1-inspired racing theme with black, racing-red, white, and charcoal palette
- **Recharts** - Interactive data visualization and charts

### Backend
- **Python + FastAPI** - High-performance async API framework with Pydantic validation
- **SQLAlchemy + Alembic** - ORM and database migrations
- **Pandas** - Data manipulation and transformation
- **NumPy** - Numerical computing

### Database
- **MySQL** - Relational database for data warehouse

### Machine Learning
- **Scikit-learn** - K-Means clustering, classification, and predictive modeling
- **MLxtend** - Apriori association rule mining

## ✨ Core Features

1. **Data Collection** - Real historical F1 data from the Jolpica F1 API (Ergast-compatible)
2. **ETL Pipeline** - Extract, transform, clean, and load at least 10,000 records into MySQL data warehouse
3. **Star Schema** - Optimized dimensional model with fact and dimension tables
4. **Comprehensive Analytics** - Driver, constructor, circuit, race, qualifying, and pit-stop analytics
5. **OLAP Operations** - Roll-up, drill-down, slice, dice, and pivot functionality
6. **Data Mining** - K-Means clustering, race-winner prediction, and Apriori association rule mining
7. **Interactive Dashboards** - Charts, filters, and dynamically generated insights
8. **Modern UI** - F1-inspired interface with motorsport-style timing tables, telemetry graphics, and driver cards
9. **Responsive Design** - Optimized for desktop, tablet, and mobile devices

## 📁 Project Structure

```
f1-insight/
├── backend/              # FastAPI backend
│   ├── app/             # Application code
│   │   ├── analytics/   # Analytics service layer
│   │   ├── api/         # API route handlers
│   │   ├── mining/      # ML/data mining modules
│   │   ├── models/      # SQLAlchemy ORM models
│   │   ├── schemas/     # Pydantic schemas
│   │   └── services/    # Utility services
│   ├── etl/             # ETL pipeline
│   ├── tests/           # Backend tests
│   └── alembic/         # Database migrations
├── frontend/            # React + Vite frontend
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Page components
│   │   ├── services/    # API client services
│   │   ├── styles/      # Global styles and theme
│   │   └── utils/       # Utility functions
├── database/            # Database schema and scripts
├── docs/                # Documentation (SRS, API docs, data dictionary, etc.)
├── notebooks/           # Jupyter notebooks for exploratory analysis
└── docker-compose.yml   # MySQL setup via Docker
```

## 🛠️ Prerequisites

- Python 3.9+ 
- Node.js 18+ and npm
- MySQL 8.0+ (or Docker)
- Git

## ⚡ Quick Start

### 1. Clone and Setup

```bash
cd f1-insight
```

### 2. Set up Environment Variables

```bash
# Copy environment examples
cp .env.example .env
cp frontend/.env.example frontend/.env 2>/dev/null || echo "frontend/.env already exists"
```

Update `.env` with your database credentials if needed.

### 3. Start MySQL Database

**Option A: Using Docker (Recommended)**
```bash
docker compose up -d
```

**Option B: Local MySQL**
Create a database named `f1_insight` with user `f1user` and password `f1pass` (or update .env).

### 4. Set up Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head
```

### 5. Run ETL Pipeline (Load Data)

The ETL pipeline extracts real historical F1 data from Jolpica API. This will load 10,000+ records into the warehouse.

```bash
# From backend directory with venv activated
python -m etl.run --all  # Load all historical data (may take 10-30 minutes)

# Or for faster testing
python -m etl.run --season 2023  # Load just one season
python -m etl.run --update       # Incremental update for latest season
```

### 6. Start Backend API

```bash
# From backend directory
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API documentation available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 7. Set up Frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend available at: [http://localhost:5173](http://localhost:5173)

## 📚 Documentation

Detailed documentation is available in the `/docs` directory:

- [Software Requirements Specification (SRS)](docs/SRS.md) — 9-section SRS with
  functional/non-functional requirements and acceptance criteria
- [System Architecture](docs/architecture.md) — end-to-end architecture &
  data flow
- [Data Dictionary](docs/data_dictionary.md) — every table, column, key and
  derived metric
- [OLAP Guide](docs/olap.md) — rollup / drilldown / slice / dice / pivot
- [Data Mining Guide](docs/data_mining.md) — clustering, prediction,
  association rules, classification (E/S/A/P)
- [API Reference](docs/api.md) — full endpoint list and contracts
- [Setup Guide](docs/setup.md) — install, MySQL, ETL, run, test, verify

## 🎯 Key Features Explained

### ETL Pipeline
- **Extract**: Fetches data from Jolpica F1 API with rate limiting, retries, and disk caching
- **Transform**: Cleans, normalizes, and enriches data with quality tracking
- **Load**: Idempotent upserts into star schema with foreign key resolution

### OLAP Operations
- **Roll-up**: Aggregate data by climbing hierarchy (e.g., driver → constructor → season)
- **Drill-down**: Navigate to more detailed levels (e.g., season → race → driver)
- **Slice**: Filter cube on a single dimension
- **Dice**: Filter on multiple dimensions
- **Pivot**: Create cross-tabulations of measures across dimensions

### Data Mining
- **K-Means Clustering**: Groups drivers by performance characteristics with automatic K selection (Elbow + Silhouette)
- **Race Winner Prediction**: Binary classification using pre-race features only (anti-leakage design)
- **Apriori Association Rules**: Discovers patterns in race outcomes and strategies
- **Performance Classification**: Composite scoring system for drivers and race results

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v
```

## 🏗️ Building for Production

### Frontend
```bash
cd frontend
npm run build
npm run preview
```

### Backend
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📝 License

This project is for educational purposes.

## 🤝 Acknowledgments

- Data provided by [Jolpica F1 API](https://github.com/jolpica/jolpica-f1)
- Formula 1 for the inspiration and rich historical data
