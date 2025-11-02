-- Hybrid BM25 + embedding search with time decay for RAG.
WITH base AS (
    SELECT *,
           row_number() OVER () AS row_id
    FROM read_parquet('data/news/gold/embeddings/version=v1/dt=*/final.parquet')
),
vector_scores AS (
    SELECT row_id,
           cosine_similarity(embedding, ?::FLOAT[]) AS vector_score
    FROM base
),
bm25 AS (
    SELECT row_id,
           fts5_score(matchinfo(fts_main, 'pcnalx')) AS text_score
    FROM fts_main('SELECT row_id FROM base WHERE text_chunk MATCH ?')
),
combined AS (
    SELECT b.news_id,
           b.text_chunk,
           b.published_at,
           coalesce(v.vector_score, 0) AS vector_score,
           coalesce(t.text_score, 0) AS bm25_score,
           exp(-date_diff('day', b.published_at, current_timestamp) / ?) AS time_decay
    FROM base b
    LEFT JOIN vector_scores v USING (row_id)
    LEFT JOIN bm25 t USING (row_id)
)
SELECT *,
       (0.6 * vector_score + 0.4 * bm25_score) * time_decay AS hybrid_score
FROM combined
ORDER BY hybrid_score DESC
LIMIT 20;
