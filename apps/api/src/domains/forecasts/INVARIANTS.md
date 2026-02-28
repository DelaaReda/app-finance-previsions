# Invariants - Forecasts Domain

- Input validation: endpoints accept normalized tickers from shared input contracts.
- Forecast payload includes: `action`, `direction`, `confidence`, `horizon`, `generated_at`, `freshness_status`.
- Service layer is pure business logic; API layer only maps HTTP contracts.
- No direct UI/rendering decisions in this domain.
