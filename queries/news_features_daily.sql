-- Query daily news features for dashboard consumption.
SELECT
    date,
    ticker,
    news_count,
    novelty,
    sent_mean,
    sent_pos_share,
    tier1_share,
    impact_proxy_mean
FROM read_parquet('data/news/gold/features_daily_v2/dt=*/features.parquet')
WHERE ticker IN ('AAPL','NVDA')
  AND date BETWEEN DATE '2025-10-01' AND DATE '2025-10-30'
ORDER BY date, ticker;
