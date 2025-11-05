// webapp/src/components/news/NewsFeed.tsx
import React, { Suspense } from "react";
import NewsCard from "./NewsCard";
import { useNews } from "@/hooks/useNews";
import FreshnessBadge from "@/components/ui/FreshnessBadge";
import { EmptyState } from "@/components/EmptyState";
import { safeArray, hasItems } from '@/lib/safe';
import type { NewsItem } from '@/types/news.types';
import {
  Box,
  Stack,
  Button,
  Alert,
  CircularProgress,
  Typography
} from '@mui/material';
const NewsFilters = React.lazy(() => import("./NewsFilters"));

export default function NewsFeed() {
  const { items, filters, setFilters, loading, error, hasMore, loadMore, freshness } = useNews();

  // Safely access articles with fallback to empty array using safe helpers
  const articles = safeArray<NewsItem>(items);

  return (
    <Box component="section">
      {/* Filtres et badge de fraîcheur */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2} flexWrap="wrap" gap={1}>
        <Suspense fallback={null}>
          <NewsFilters value={filters} onChange={setFilters} />
        </Suspense>
        <FreshnessBadge
          freshness={freshness ?? undefined}
          stale={freshness ? new Date().getTime() - new Date(freshness).getTime() > 3600000 : false}
        />
      </Stack>

      {/* États d'erreur */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Erreur: {error}
        </Alert>
      )}

      {/* État de chargement initial */}
      {loading && !hasItems(articles) && (
        <Box display="flex" justifyContent="center" alignItems="center" py={8}>
          <Stack spacing={2} alignItems="center">
            <CircularProgress />
            <Typography variant="body2" color="text.secondary">
              Chargement des actualités…
            </Typography>
          </Stack>
        </Box>
      )}

      {/* État vide */}
      {!hasItems(articles) && !loading && (
        <EmptyState
          title="Aucun article disponible"
          subtitle={
            freshness
              ? `Dernière mise à jour: ${new Date(freshness).toLocaleString()}`
              : "Ingestion en cours…"
          }
        />
      )}

      {/* Liste d'articles */}
      {hasItems(articles) && (
        <Stack spacing={0}>
          {articles.map((item: NewsItem, index: number) => (
            <NewsCard key={item.id || index.toString()} item={item} />
          ))}
        </Stack>
      )}

      {/* Pagination */}
      {hasMore && (
        <Box display="flex" justifyContent="center" mt={3}>
          <Button
            variant="outlined"
            disabled={loading}
            onClick={loadMore}
            size="large"
          >
            {loading ? "Chargement…" : "Charger plus"}
          </Button>
        </Box>
      )}
    </Box>
  );
}
