// webapp/src/components/news/NewsFeed.tsx
import React, { Suspense } from "react";
import NewsCard from "./NewsCard";
import { useNews } from "@/hooks/useNews";
import { FreshnessBadge } from "@/components/ui/FreshnessBadge";
import { EmptyState } from "@/components/ui/EmptyState";
const NewsFilters = React.lazy(() => import("./NewsFilters"));

export default function NewsFeed() {
  const { items, filters, setFilters, loading, error, hasMore, loadMore, freshness } = useNews();

  // Safely access articles with fallback to empty array
  const articles = items ?? [];

  return (
    <section>
      {/* Filtres et badge de fraîcheur */}
      <div className="flex items-center justify-between mb-4">
        <Suspense fallback={null}>
          <NewsFilters value={filters} onChange={setFilters} />
        </Suspense>
        <FreshnessBadge freshness={freshness} stale={freshness ? new Date().getTime() - new Date(freshness).getTime() > 3600000 : false} />
      </div>

      {/* États */}
      {error && <div role="alert" className="text-red-700">Erreur: {error}</div>}
      {loading && articles.length === 0 && <div className="text-center py-8">Chargement des actualités…</div>}
      {articles.length === 0 && !loading && (
        <EmptyState
          title="Aucun article disponible"
          hint={freshness ? `Dernière mise à jour: ${new Date(freshness).toLocaleString()}` : "Ingestion en cours…"}
        />
      )}

      {/* Liste sécurisée */}
      {articles.length > 0 && (
        <div>
          {articles.map(item => <NewsCard key={item.id} item={item} />)}
        </div>
      )}

      {/* Pagination */}
      <div className="mt-4">
        {hasMore && (
          <button disabled={loading} onClick={loadMore} className="px-4 py-2 rounded border">
            {loading ? "Chargement…" : "Charger plus"}
          </button>
        )}
      </div>
    </section>
  );
}
