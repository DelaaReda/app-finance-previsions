// webapp/src/components/news/NewsFeed.tsx
import React, { Suspense } from "react";
import NewsCard from "./NewsCard";
import { useNews } from "@/hooks/useNews";
import { FreshnessBadge } from "@/components/ui/FreshnessBadge";
const NewsFilters = React.lazy(() => import("./NewsFilters"));

export default function NewsFeed() {
  const { items, filters, setFilters, loading, error, hasMore, loadMore, freshness } = useNews();

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
      {loading && items.length === 0 && <div className="text-center py-8">Chargement des actualités…</div>}
      {items.length === 0 && !loading && (
        <div className="text-center py-8 bg-gray-50 rounded-lg border">
          <h3 className="font-medium text-gray-900 mb-2">Aucune actualité trouvée</h3>
          <p className="text-sm text-gray-600 mb-3">
            Aucun article ne correspond aux filtres actuels.
          </p>
          <p className="text-xs text-gray-500">
            Essayez de modifier les filtres (période, région, score minimum) pour voir plus d'articles.
          </p>
        </div>
      )}

      {/* Liste */}
      {items.map(item => <NewsCard key={item.id} item={item} />)}

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
