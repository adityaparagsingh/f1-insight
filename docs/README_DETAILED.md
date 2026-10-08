# F1 Insight - Detailed Documentation

This directory contains comprehensive documentation for the F1 Insight project.

## Documentation Files

| File | Description |
|---|---|
| [SRS.md](SRS.md) | Software Requirements Specification - Detailed requirements, architecture, design specs |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Complete database schema with ERD description, table definitions, constraints, and indexes |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Data dictionary defining all tables, columns, measures, KPIs, ML features, and business terms |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | Complete REST API documentation with endpoints, parameters, examples, and response formats |

## Quick Links (from running application)

- **Frontend**: http://localhost:5173
- **Backend API**: http://127.0.0.1:8000
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **Health Check**: http://127.0.0.1:8000/api/health

## Getting Started

See the main [README.md](../README.md) in the project root for installation and setup instructions.

## Project Summary

F1 Insight is a complete full-stack Formula 1 performance analytics and data mining system featuring:
- Real data ingestion from Jolpica F1 API
- ETL pipeline processing >10,000 records
- Star schema data warehouse (MySQL)
- 5 OLAP operations (Roll-up, Drill-down, Slice, Dice, Pivot)
- 4 data mining techniques (K-Means clustering, Race winner prediction, Apriori association rules, Performance classification)
- Interactive F1-inspired React frontend with Recharts visualizations
- Comprehensive REST API with FastAPI
