# Ingestion Service

This service handles live data ingestion from various financial data sources including Yahoo Finance, RSS feeds, and FRED (Federal Reserve Economic Data).

## Sources

- Yahoo Finance API
- RSS feeds (financial news)
- FRED API (economic indicators)

## Components

- Data fetchers
- Job scheduler
- Cache (Redis/SQLite)
- Data validation

## Commands

- `make ingest-demo` - Run a demo ingestion job